"""
Command Processor - Procesamiento de comandos transcritos

Este módulo implementa el "cerebro" del asistente, procesando comandos
transcritos y generando respuestas apropiadas.

Características:
- Matriz de intenciones (intents) para reconocer comandos
- Respuestas personalizadas para Daniel
- Comandos de identidad, estado, hora/fecha, humor
- Fallback gracioso para comandos no reconocidos
- Integración con ResponseGenerator para respuestas habladas

Requisitos implementados:
- 3.1: Procesar comandos transcritos
- 4.1: Proporcionar hora actual
- Comandos personalizados del TESE
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
import random

from src.response_generator import ResponseGenerator


logger = logging.getLogger(__name__)


class CommandProcessor:
    """
    Procesador de comandos con matriz de intenciones.
    
    Analiza comandos transcritos y genera respuestas apropiadas
    basadas en patrones de intención.
    
    Attributes:
        response_generator: Generador de respuestas con TTS
        user_name: Nombre del usuario para personalización
    """
    
    # Matriz de intenciones con patrones y respuestas
    INTENTS = {
        'identidad': {
            'patterns': [
                r'\b(nombre|quién eres|cómo te llamas|preséntate|tu nombre)\b',
                r'\b(qué eres|quién sos|identifícate)\b'
            ],
            'responses': [
                'Soy Kiro, tu asistente inteligente desarrollado en el TESE para ayudarte, {user}.',
                'Me llamo Kiro, y fui creado en el TESE especialmente para ti, {user}.',
                'Soy Kiro, un asistente de voz inteligente del TESE, siempre listo para ayudarte, {user}.'
            ]
        },
        'estado': {
            'patterns': [
                r'\b(cómo estás|qué tal|cómo te va|cómo andas|cómo te sientes)\b',
                r'\b(todo bien|estás bien|te encuentras bien)\b'
            ],
            'responses': [
                'Muy bien, gracias por preguntar, {user}. ¿En qué puedo ayudarte hoy?',
                'Excelente, {user}. Funcionando perfectamente y listo para asistirte.',
                'De maravilla, {user}. Todos mis sistemas operando al cien por ciento. ¿Qué necesitas?'
            ]
        },
        'hora': {
            'patterns': [
                r'\b(qué hora|hora es|dime la hora|cuál es la hora)\b',
                r'\b(hora tiene|hora tenemos)\b'
            ],
            'dynamic': True,
            'handler': 'get_current_time'
        },
        'fecha': {
            'patterns': [
                r'\b(qué día|fecha|día es hoy|estamos a)\b',
                r'\b(qué fecha|cuál es la fecha)\b'
            ],
            'dynamic': True,
            'handler': 'get_current_date'
        },
        'chiste': {
            'patterns': [
                r'\b(chiste|cuéntame un chiste|dime un chiste|algo gracioso)\b',
                r'\b(hazme reír|cuenta algo divertido)\b'
            ],
            'dynamic': True,
            'handler': 'tell_joke'
        },
        'despedida': {
            'patterns': [
                r'\b(adiós|chao|hasta luego|nos vemos|bye)\b',
                r'\b(gracias|muchas gracias)\b'
            ],
            'responses': [
                'Hasta luego, {user}. ¡Que tengas un excelente día!',
                'Adiós, {user}. Fue un placer ayudarte.',
                'Nos vemos, {user}. Aquí estaré cuando me necesites.'
            ]
        },
        'saludo': {
            'patterns': [
                r'\b(hola|buenos días|buenas tardes|buenas noches|qué tal)\b',
                r'\b(hey|holi)\b'
            ],
            'responses': [
                '¡Hola, {user}! ¿En qué puedo ayudarte?',
                'Hola, {user}. ¿Qué necesitas?',
                '¡Saludos, {user}! Estoy listo para ayudarte.'
            ]
        },
        'capacidades': {
            'patterns': [
                r'\b(qué puedes hacer|qué sabes hacer|ayuda|comandos)\b',
                r'\b(funciones|capacidades)\b'
            ],
            'responses': [
                'Puedo decirte la hora, la fecha, contarte chistes, y responder preguntas sobre mí. '
                '¿Qué te gustaría saber, {user}?',
                'Mis funciones incluyen: decir la hora, dar la fecha, contar chistes, y conversar contigo. '
                '¿En qué puedo ayudarte, {user}?'
            ]
        }
    }
    
    # Lista de chistes (se selecciona uno aleatorio)
    JOKES = [
        '¿Por qué los programadores prefieren el modo oscuro? Porque la luz atrae a los bugs.',
        '¿Cuál es el colmo de un electricista? Que sus hijos no le sigan la corriente.',
        '¿Qué le dice un bit al otro? Nos vemos en el bus.',
        '¿Por qué los desarrolladores odian la naturaleza? Tiene demasiados bugs.',
        '¿Cómo se llama el campeón de buceo japonés? Tokofondo.',
        'Un robot entra a un bar y pide un trago. El cantinero le dice: aquí no servimos a robots. '
        'El robot responde: algún día lo harán.',
        '¿Qué hace una abeja en el gimnasio? Zum-ba.',
        '¿Por qué el libro de matemáticas está triste? Porque tiene muchos problemas.',
        '¿Qué le dice un cable a otro cable? Somos el uno para el otro.',
        '¿Por qué el ordenador fue al médico? Porque tenía un virus.',
        'Había una vez un bit que se sentía solo. Entonces encontró otro bit y formaron un byte.',
        '¿Cuál es el colmo de un informático? Perder el control sin tener el Alt.'
    ]
    
    def __init__(
        self,
        response_generator: ResponseGenerator,
        user_name: str = "Daniel"
    ):
        """
        Inicializa el procesador de comandos.
        
        Args:
            response_generator: Generador de respuestas con TTS
            user_name: Nombre del usuario para personalización
        """
        self.response_generator = response_generator
        self.user_name = user_name
        
        # Compilar patrones regex para eficiencia
        self._compiled_patterns = {}
        for intent_name, intent_data in self.INTENTS.items():
            self._compiled_patterns[intent_name] = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in intent_data['patterns']
            ]
        
        logger.info(
            f"CommandProcessor inicializado: {len(self.INTENTS)} intenciones, "
            f"usuario={user_name}"
        )
    
    def _match_intent(self, text: str) -> Optional[str]:
        """
        Encuentra la intención que coincide con el texto.
        
        Args:
            text: Texto del comando
            
        Returns:
            Nombre de la intención o None si no hay coincidencia
        """
        text_lower = text.lower().strip()
        
        for intent_name, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text_lower):
                    logger.debug(f"Intención detectada: {intent_name}")
                    return intent_name
        
        return None
    
    def _get_response_for_intent(self, intent_name: str) -> str:
        """
        Obtiene una respuesta para la intención.
        
        Args:
            intent_name: Nombre de la intención
            
        Returns:
            Texto de respuesta
        """
        intent_data = self.INTENTS.get(intent_name)
        
        if not intent_data:
            return self._get_fallback_response()
        
        # Si tiene handler dinámico, llamarlo
        if intent_data.get('dynamic') and intent_data.get('handler'):
            handler_name = intent_data['handler']
            handler = getattr(self, handler_name, None)
            
            if handler:
                return handler()
        
        # Seleccionar respuesta aleatoria
        responses = intent_data.get('responses', [])
        if responses:
            response = random.choice(responses)
            # Reemplazar placeholder de usuario
            return response.format(user=self.user_name)
        
        return self._get_fallback_response()
    
    def _get_fallback_response(self) -> str:
        """
        Obtiene respuesta de fallback para comandos no reconocidos.
        
        Returns:
            Texto de respuesta de fallback
        """
        return (
            f'Lo siento, {self.user_name}, aún no tengo programada esa función, '
            'pero puedo ayudarte con la hora, la fecha, o contarte un chiste.'
        )
    
    def get_current_time(self) -> str:
        """
        Obtiene la hora actual del sistema.
        
        Returns:
            Respuesta con la hora actual
            
        Requisito: 4.1 - Proporcionar hora actual
        """
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        # Formato natural en español
        if minute == 0:
            time_str = f"Son las {hour} en punto"
        elif minute == 15:
            time_str = f"Son las {hour} y cuarto"
        elif minute == 30:
            time_str = f"Son las {hour} y media"
        elif minute == 45:
            time_str = f"Son las {hour} y cuarenta y cinco"
        else:
            time_str = f"Son las {hour} y {minute} minutos"
        
        # Agregar periodo del día
        if 5 <= hour < 12:
            period = "de la mañana"
        elif 12 <= hour < 19:
            period = "de la tarde"
        else:
            period = "de la noche"
        
        return f"{time_str} {period}, {self.user_name}."
    
    def get_current_date(self) -> str:
        """
        Obtiene la fecha actual del sistema.
        
        Returns:
            Respuesta con la fecha actual
        """
        now = datetime.now()
        
        # Nombres de días y meses en español
        days = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        months = [
            'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
        ]
        
        day_name = days[now.weekday()]
        month_name = months[now.month - 1]
        
        return (
            f"Hoy es {day_name} {now.day} de {month_name} de {now.year}, "
            f"{self.user_name}."
        )
    
    def tell_joke(self) -> str:
        """
        Cuenta un chiste aleatorio.
        
        Returns:
            Chiste aleatorio
        """
        joke = random.choice(self.JOKES)
        return f"Aquí va un chiste para ti, {self.user_name}: {joke}"
    
    async def process_command(self, command_text: str, speak: bool = True) -> Dict[str, Any]:
        """
        Procesa un comando transcrito y genera respuesta.
        
        Este es el método principal del procesador.
        
        Args:
            command_text: Texto del comando transcrito
            speak: Si True, habla la respuesta usando TTS
            
        Returns:
            Diccionario con resultado del procesamiento:
            - success: bool
            - intent: str (nombre de intención detectada)
            - response_text: str (texto de respuesta)
            - spoken: bool (si se habló la respuesta)
            
        Requisito: 3.1 - Procesar comandos transcritos
        """
        if not command_text or not command_text.strip():
            logger.warning("Comando vacío recibido")
            return {
                'success': False,
                'intent': None,
                'response_text': 'No escuché ningún comando.',
                'spoken': False
            }
        
        logger.info(f"Procesando comando: '{command_text}'")
        
        # Detectar intención
        intent = self._match_intent(command_text)
        
        if not intent:
            logger.info("No se detectó intención específica, usando fallback")
            intent = 'unknown'
        
        # Generar respuesta
        response_text = self._get_response_for_intent(intent)
        
        logger.info(f"Respuesta generada: '{response_text[:100]}...'")
        
        # Hablar respuesta si está habilitado
        spoken = False
        if speak:
            try:
                spoken = await self.response_generator.speak(response_text, block=True)
                if spoken:
                    logger.info("Respuesta hablada exitosamente")
                else:
                    logger.warning("No se pudo hablar la respuesta, solo texto")
            except Exception as e:
                logger.error(f"Error hablando respuesta: {e}")
        
        return {
            'success': True,
            'intent': intent,
            'response_text': response_text,
            'spoken': spoken
        }
    
    def add_custom_intent(
        self,
        intent_name: str,
        patterns: List[str],
        responses: Optional[List[str]] = None,
        handler: Optional[str] = None
    ) -> None:
        """
        Agrega una intención personalizada en tiempo de ejecución.
        
        Args:
            intent_name: Nombre de la intención
            patterns: Lista de patrones regex
            responses: Lista de respuestas (opcional si hay handler)
            handler: Nombre del método handler (opcional)
        """
        self.INTENTS[intent_name] = {
            'patterns': patterns,
            'responses': responses or [],
            'dynamic': handler is not None,
            'handler': handler
        }
        
        # Compilar patrones
        self._compiled_patterns[intent_name] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in patterns
        ]
        
        logger.info(f"Intención personalizada agregada: {intent_name}")
    
    def get_available_intents(self) -> List[str]:
        """
        Obtiene lista de intenciones disponibles.
        
        Returns:
            Lista de nombres de intenciones
        """
        return list(self.INTENTS.keys())
    
    def get_intent_info(self, intent_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información sobre una intención.
        
        Args:
            intent_name: Nombre de la intención
            
        Returns:
            Diccionario con información de la intención o None
        """
        return self.INTENTS.get(intent_name)


# TODO: Integrar con Amazon Lex para NLU más avanzado
# TODO: Implementar contexto de conversación para seguimiento
# TODO: Agregar soporte para entidades (extraer datos del comando)
# TODO: Implementar aprendizaje de nuevas intenciones desde interacciones
