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
import os
import re
import threading
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional, Dict, Any, List, Tuple
import random

from openai import OpenAI

from src.response_generator import ResponseGenerator
from src.query_router import QueryRouter
from src.web_search import WebSearchModule
from src.threading_manager import ThreadingManager
from src.rich_ui_manager import RichUIManager
from src.models import SystemState
from src.intent_classifier import IntentClassifier, IntentType, ActionType
from src.action_router import ActionRouter


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
                'Me llamo Kiro, y fui creado en el TESE especialmente para ti, Daniel Vazquez Salazar.',
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
                'Puedo decirte la hora, la fecha, contarte chistes, y responder cualquier pregunta general gracias a mi conexión con inteligencia artificial. '
                '¡Pregúntame lo que quieras, {user}!',
                'Mis funciones incluyen: decir la hora, dar la fecha, contar chistes, y responder preguntas de cualquier tema. '
                '¿En qué puedo ayudarte, {user}?'
            ]
        }
    }

    # Frases clave para coincidencia difusa (toleran errores de transcripción tipo "ora"/"hora")
    FUZZY_PHRASES: Dict[str, List[str]] = {
        'hora': ['qué hora es', 'dime la hora', 'que hora es', 'cuál es la hora', 'que ora es', 'ora es'],
        'fecha': ['qué día es', 'qué fecha es', 'fecha', 'día es hoy', 'que dia es', 'que fecha'],
        'chiste': ['chiste', 'cuéntame un chiste', 'dime un chiste', 'algo gracioso', 'un chiste'],
        'identidad': ['cómo te llamas', 'quién eres', 'tu nombre', 'preséntate', 'como te llamas'],
        'estado': ['cómo estás', 'qué tal', 'cómo te va', 'estás bien', 'como estas'],
        'saludo': ['hola', 'buenos días', 'buenas tardes', 'buenas noches', 'hey', 'ola'],
        'despedida': ['adiós', 'chao', 'hasta luego', 'gracias', 'bye', 'adios'],
        'capacidades': ['qué puedes hacer', 'ayuda', 'comandos', 'qué sabes hacer', 'que puedes hacer'],
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
        user_name: str = "Daniel",
        web_search_enabled: bool = True,
        data_dir: str = "data",
        smart_router_enabled: bool = True,
        local_rag_enabled: bool = True,
        vector_cache_enabled: bool = True,
        vector_cache_backend: str = "chroma",
    ):
        """
        Inicializa el procesador de comandos.
        
        Args:
            response_generator: Generador de respuestas con TTS
            user_name: Nombre del usuario para personalización
            web_search_enabled: Si True, habilita búsqueda web
            data_dir: Directorio para guardar notas (Phase 3)
            smart_router_enabled: Si True, usa SmartLLMRouter en lugar de IntentClassifier
            local_rag_enabled: Si True, habilita búsqueda de notas locales
            vector_cache_enabled: Si True, usa base vectorial para cache de respuestas (ahorro DeepSeek)
            vector_cache_backend: "chroma" (local) o "supabase" (nube). Supabase requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env
        """
        self.response_generator = response_generator
        self.user_name = user_name
        self.data_dir = data_dir
        self._vector_cache_enabled = vector_cache_enabled
        self._vector_cache_backend = (vector_cache_backend or "chroma").lower()
        self._vector_store = None  # Inicialización perezosa (carga modelo de embeddings)
        
        # Compilar patrones regex para eficiencia
        self._compiled_patterns = {}
        for intent_name, intent_data in self.INTENTS.items():
            self._compiled_patterns[intent_name] = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in intent_data['patterns']
            ]
        
        # Cliente de DeepSeek para preguntas generales
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_key:
            self._llm_client = OpenAI(
                api_key=deepseek_key,
                base_url="https://api.deepseek.com"
            )
            logger.info("DeepSeek configurado como fallback para preguntas generales")
        else:
            self._llm_client = None
            logger.warning("DEEPSEEK_API_KEY no encontrada; preguntas generales deshabilitadas")
        
        # Phase 2: Componentes de web search y threading
        self.query_router = QueryRouter()
        self.web_search = WebSearchModule() if web_search_enabled else None
        self.threading_manager = ThreadingManager(max_workers=3)
        self.ui_manager = RichUIManager()
        self.current_state = SystemState.ESCUCHANDO
        self._state_lock = threading.Lock()
        
        # Phase 3: Componentes de acciones del sistema
        self.intent_classifier = IntentClassifier()
        self.action_router = ActionRouter(data_dir=data_dir)
        
        # Phase 4: Smart LLM Router (reemplaza IntentClassifier si está habilitado)
        self.smart_router_enabled = smart_router_enabled
        if smart_router_enabled and self._llm_client:
            from src.smart_llm_router import SmartLLMRouter
            self.smart_router = SmartLLMRouter(
                deepseek_client=self._llm_client,
                timeout=3,
                confidence_threshold=0.7,
                temperature=0.1,
                max_tokens=200
            )
            logger.info("SmartLLMRouter habilitado (reemplaza IntentClassifier)")
        else:
            self.smart_router = None
            if smart_router_enabled:
                logger.warning("SmartLLMRouter deshabilitado: DEEPSEEK_API_KEY no encontrada")
        
        # Phase 4: Local RAG (búsqueda de notas locales)
        self.local_rag_enabled = local_rag_enabled
        if local_rag_enabled:
            from src.local_knowledge_reader import LocalKnowledgeReader
            self.local_knowledge = LocalKnowledgeReader(
                data_dir=data_dir,
                max_context_tokens=2000,
                max_results=3,
                threading_manager=self.threading_manager
            )
            # Inicializar en thread separado para no bloquear
            try:
                future = self.threading_manager.execute_async(
                    self.local_knowledge.initialize,
                    timeout=5
                )
                future.result(timeout=5)
                logger.info("LocalKnowledgeReader inicializado correctamente")
            except Exception as e:
                logger.error(f"Error inicializando LocalKnowledgeReader: {e}")
        else:
            self.local_knowledge = None
        
        logger.info(
            f"CommandProcessor inicializado: {len(self.INTENTS)} intenciones, "
            f"usuario={user_name}, web_search={'enabled' if web_search_enabled else 'disabled'}, "
            f"actions={'enabled'}, smart_router={'enabled' if self.smart_router else 'disabled'}, "
            f"local_rag={'enabled' if self.local_knowledge else 'disabled'}, "
            f"vector_cache={'enabled' if vector_cache_enabled else 'disabled'} (backend={self._vector_cache_backend})"
        )
    
    def _match_intent(self, text: str) -> Optional[str]:
        """
        Encuentra la intención que coincide con el texto.
        Primero intenta regex; si no hay match, usa coincidencia difusa para tolerar errores de transcripción.
        
        Args:
            text: Texto del comando
            
        Returns:
            Nombre de la intención o None si no hay coincidencia
        """
        text_lower = text.lower().strip()
        
        # 1) Coincidencia exacta con patrones regex
        for intent_name, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text_lower):
                    logger.debug(f"Intención detectada: {intent_name}")
                    return intent_name
        
        # 2) Coincidencia difusa (transcripción con pequeños errores: "que ora es" -> hora)
        best_intent, best_ratio = self._fuzzy_match_intent(text_lower)
        if best_intent and best_ratio >= 0.72:
            logger.debug(f"Intención detectada por similitud: {best_intent} ({best_ratio:.2f})")
            return best_intent
        
        return None

    def _fuzzy_match_intent(self, text: str) -> Tuple[Optional[str], float]:
        """Devuelve (intent, ratio) con la mejor coincidencia por similitud. Tolera errores de transcripción."""
        best_intent: Optional[str] = None
        best_ratio: float = 0.0
        for intent_name, phrases in self.FUZZY_PHRASES.items():
            for phrase in phrases:
                r = SequenceMatcher(None, text, phrase).ratio()
                if r > best_ratio:
                    best_ratio = r
                    best_intent = intent_name
        return best_intent, best_ratio
    
    def _update_state(self, new_state: SystemState):
        """
        Actualiza estado del sistema de forma thread-safe.
        
        Args:
            new_state: Nuevo estado del sistema
        """
        with self._state_lock:
            old_state = self.current_state
            self.current_state = new_state
            self.ui_manager.update_state(new_state)
            logger.info(f"Estado cambiado: {old_state.value} -> {new_state.value}")
    
    def _build_system_prompt(self, web_context: str = "", notes_context: str = "") -> str:
        """
        Construye system prompt con contexto web y/o notas si aplica.
        
        Args:
            web_context: Contexto de búsqueda web (vacío si no hay)
            notes_context: Contexto de notas del usuario (vacío si no hay)
            
        Returns:
            System prompt completo
        """
        base_prompt = (
            f"Eres Kiro, un asistente de voz inteligente. "
            f"El usuario es Daniel Vazquez Salazar, estudiante del TESE "
            f"(Tecnológico de Estudios Superiores de Ecatepec). "
            f"Proporciona respuestas técnicas apropiadas para nivel universitario. "
            f"Responde de forma directa y concisa, sin introducciones largas. "
            f"Máximo 2-3 oraciones, optimizado para síntesis de voz. "
            f"No uses markdown, emojis, ni formato especial. Solo texto plano."
        )
        
        # Agregar contexto de notas si existe
        if notes_context:
            base_prompt += f"\n\n{notes_context}\n\nBasa tu respuesta en las notas del usuario proporcionadas."
        
        # Agregar contexto web si existe
        if web_context:
            base_prompt += f"\n\nInformación de internet: {web_context}\n\nBasa tu respuesta en la información proporcionada."
        
        return base_prompt
    
    def _call_deepseek(self, command_text: str, system_prompt: str) -> str:
        """
        Llama a DeepSeek con manejo de errores.
        
        Args:
            command_text: Texto del comando
            system_prompt: System prompt (con o sin web context)
            
        Returns:
            Respuesta de DeepSeek o mensaje de error
        """
        if not self._llm_client:
            return "Lo siento, no tengo acceso a información externa en este momento."
        
        try:
            import time
            start_time = time.time()
            
            response = self._llm_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": command_text}
                ],
                max_tokens=150,
                temperature=0.3,
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"DeepSeek response time: {elapsed_ms:.0f}ms")
            
            text = response.choices[0].message.content.strip() if response.choices else None
            if text:
                logger.info("DeepSeek respondió correctamente")
                return text
            else:
                return "Lo siento, no pude generar una respuesta."
                
        except TimeoutError:
            logger.error("Timeout en DeepSeek")
            return "Lo siento, la respuesta está tardando demasiado."
        except Exception as e:
            logger.error(f"Error consultando DeepSeek: {e}")
            return "Lo siento, no pude procesar tu solicitud en este momento."
    
    def _validate_command(self, command: str) -> bool:
        """
        Valida comando antes de procesar.
        
        Args:
            command: Comando a validar
            
        Returns:
            True si es válido, False en caso contrario
        """
        if not command or len(command) > 500:
            return False
        
        # Verificar que sea texto válido
        if not command.isprintable():
            return False
        
        return True
    
    def _get_response_for_intent(self, intent_name: str, original_text: str = "") -> str:
        """
        Obtiene una respuesta para la intención.
        
        Args:
            intent_name: Nombre de la intención
            original_text: Texto original del comando (para fallback con Gemini)
            
        Returns:
            Texto de respuesta
        """
        intent_data = self.INTENTS.get(intent_name)
        
        if not intent_data:
            return self._get_fallback_response(original_text)
        
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
            return response.format(user=self.user_name)
        
        return self._get_fallback_response(original_text)
    
    def _ask_llm(self, question: str) -> Optional[str]:
        """Consulta a DeepSeek para responder preguntas de conocimiento general."""
        if not self._llm_client:
            return None
        try:
            import time
            start_time = time.time()
            
            response = self._llm_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"Eres Kiro, un asistente de voz inteligente. "
                            f"El usuario es Daniel Vazquez Salazar, estudiante del TESE "
                            f"(Tecnológico de Estudios Superiores de Ecatepec). "
                            f"Proporciona respuestas técnicas apropiadas para nivel universitario. "
                            f"Responde de forma directa y concisa, sin introducciones largas. "
                            f"Máximo 2-3 oraciones, optimizado para síntesis de voz. "
                            f"No uses markdown, emojis, ni formato especial. Solo texto plano."
                        )
                    },
                    {"role": "user", "content": question}
                ],
                max_tokens=150,
                temperature=0.3,
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"DeepSeek response time: {elapsed_ms:.0f}ms")
            
            text = response.choices[0].message.content.strip() if response.choices else None
            if text:
                logger.info("DeepSeek respondió correctamente")
            return text
        except Exception as e:
            logger.error("Error consultando DeepSeek: %s", e)
            return None

    def _get_fallback_response(self, original_text: str = "") -> str:
        """
        Intenta responder con DeepSeek; si falla, usa respuesta genérica.
        """
        if original_text:
            llm_answer = self._ask_llm(original_text)
            if llm_answer:
                return llm_answer

        return (
            f'Lo siento, {self.user_name}, no pude encontrar una respuesta. '
            'Puedo ayudarte con la hora, la fecha, contarte un chiste, o hacerme preguntas generales.'
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
        Procesa un comando transcrito con clasificación de intents y acciones del sistema.

        Flujo Phase 3:
        1. Validar comando
        2. Actualizar estado a PROCESANDO
        3. Clasificar intent (conversational vs action)
        4. Si es ACTION: ejecutar acción del sistema
        5. Si es CONVERSATIONAL: procesar con web search + DeepSeek
        6. Sintetizar y hablar respuesta con auto-mute
        7. Volver a estado ESCUCHANDO

        Args:
            command_text: Texto del comando transcrito
            speak: Si True, habla la respuesta usando TTS

        Returns:
            Diccionario con resultado del procesamiento:
            - success: bool
            - intent: str (nombre de intención detectada)
            - response_text: str (texto de respuesta)
            - spoken: bool (si se habló la respuesta)
            - used_web_search: bool (si se usó búsqueda web)
            - action_executed: bool (si se ejecutó una acción)

        Requisito: 3.1 - Procesar comandos transcritos
        Requisito: 2.5 - Clasificar y enrutar intents
        """
        # 1. Validar comando
        if not self._validate_command(command_text):
            logger.warning("Comando inválido recibido")
            return {
                'success': False,
                'intent': None,
                'response_text': 'Comando inválido.',
                'spoken': False,
                'used_web_search': False,
                'action_executed': False
            }

        logger.info(f"Procesando comando: '{command_text}'")

        # 2. Primero mensaje del usuario, después Pensando
        self.ui_manager.show_user_message(command_text)
        self._update_state(SystemState.PROCESANDO)

        # 3. Clasificar intent (Phase 4: Smart LLM Router o Phase 3: IntentClassifier)
        if self.smart_router:
            # Usar SmartLLMRouter con threading
            try:
                future = self.threading_manager.execute_async(
                    self.smart_router.classify,
                    command_text,
                    timeout=3
                )
                classified_intent = future.result(timeout=3)
                logger.info(
                    f"Intent clasificado (SmartLLMRouter): {classified_intent.intent_type.value} "
                    f"(action: {classified_intent.action_type.value if classified_intent.action_type else 'N/A'}, "
                    f"confidence: {classified_intent.confidence:.2f})"
                )
            except Exception as e:
                logger.error(f"SmartLLMRouter falló, usando fallback: {e}")
                # Fallback a IntentClassifier
                classified_intent = self.intent_classifier.classify(command_text)
                logger.info(
                    f"Intent clasificado (fallback): {classified_intent.intent_type.value} "
                    f"(action: {classified_intent.action_type.value if classified_intent.action_type else 'N/A'})"
                )
        else:
            # Usar IntentClassifier (Phase 3)
            classified_intent = self.intent_classifier.classify(command_text)
            logger.info(
                f"Intent clasificado: {classified_intent.intent_type.value} "
                f"(action: {classified_intent.action_type.value if classified_intent.action_type else 'N/A'})"
            )

        # 4. Procesar según tipo de intent
        if classified_intent.intent_type == IntentType.ACTION:
            # Verificar si es lectura de notas (FILE con action="read")
            if (classified_intent.action_type == ActionType.FILE and 
                classified_intent.parameters.get('action') == 'read'):
                # Procesar como conversational con contexto de notas
                response_text, used_web_search = await self._process_conversational_with_notes(
                    command_text, 
                    classified_intent.parameters.get('query', '')
                )
                action_executed = False
                intent_name = 'note_read'
            else:
                # Ejecutar acción del sistema (crear nota, YouTube, App, Web)
                response_text = await self._process_action(classified_intent)
                used_web_search = False
                action_executed = True
                intent_name = classified_intent.action_type.value if classified_intent.action_type else 'action'
                
                # Re-indexar notas si se creó una nota
                if classified_intent.action_type == ActionType.FILE and self.local_knowledge:
                    try:
                        self.threading_manager.execute_async(
                            self.local_knowledge.re_index_if_needed,
                            timeout=2
                        )
                    except Exception as e:
                        logger.error(f"Error re-indexando notas: {e}")
        else:
            # Primero intentar con intenciones locales
            local_intent = self._match_intent(command_text)

            if local_intent and local_intent != 'unknown':
                # Procesar con intención local
                response_text = self._get_response_for_intent(local_intent, original_text=command_text)
                used_web_search = False
                action_executed = False
                intent_name = local_intent
            else:
                # Procesar con web search + DeepSeek
                response_text, used_web_search = await self._process_conversational(command_text)
                action_executed = False
                intent_name = 'conversational'

        # 5. Mostrar respuesta
        self.ui_manager.show_assistant_message(response_text, used_web_search=used_web_search)

        # 6. Sintetizar y hablar respuesta con auto-mute
        spoken = False
        if speak:
            try:
                # No mostrar panel "Hablando" para no repetir después de Asistente

                # Usar response_generator.speak() que incluye auto-mute
                spoken = await self.response_generator.speak(response_text, block=True)

            except Exception as e:
                logger.error(f"Error hablando respuesta: {e}")

        # 7. Volver a escuchar (solo actualizar estado; el panel "Escuchando" lo muestra main)
        self.ui_manager.update_state_silent(SystemState.ESCUCHANDO)

        return {
            'success': True,
            'intent': intent_name,
            'response_text': response_text,
            'spoken': spoken,
            'used_web_search': used_web_search,
            'action_executed': action_executed
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
    
    async def _process_action(self, intent) -> str:
        """
        Procesa una acción del sistema.
        
        Args:
            intent: Intent clasificado con action_type y parameters
            
        Returns:
            Mensaje de respuesta para el usuario
            
        Requisito: 2.6 - Procesar acciones del sistema
        """
        try:
            # Ejecutar acción en thread separado con timeout
            future = self.threading_manager.execute_async(
                self.action_router.route_and_execute,
                intent,
                timeout=30
            )
            
            result = future.result(timeout=30)
            
            # Generar respuesta según resultado
            if result.success:
                return result.message
            else:
                return f"Lo siento, {self.user_name}. {result.error}"
                
        except Exception as e:
            logger.error(f"Error procesando acción: {e}")
            return f"Lo siento, {self.user_name}, ocurrió un error al ejecutar la acción."
    
    async def _process_conversational_with_notes(self, command_text: str, query: str) -> tuple[str, bool]:
        """
        Procesa un comando conversacional con contexto de notas locales.
        
        Args:
            command_text: Texto del comando
            query: Query para buscar en notas
            
        Returns:
            Tupla (response_text, used_web_search)
            
        Requisito: 8.2 - Procesar note_read intent
        """
        notes_context = ""
        
        # Buscar notas relevantes si Local RAG está habilitado
        if self.local_knowledge and query:
            try:
                # Ejecutar búsqueda en thread separado
                future = self.threading_manager.execute_async(
                    self.local_knowledge.search,
                    query,
                    timeout=5
                )
                
                notes = future.result(timeout=5)
                
                if notes:
                    # Formatear contexto
                    notes_context = self.local_knowledge.format_context(notes)
                    logger.info(f"Encontradas {len(notes)} notas relevantes para query: '{query}'")
                else:
                    logger.info(f"No se encontraron notas para query: '{query}'")
                    return f"No encontré notas sobre {query}, {self.user_name}.", False
                    
            except Exception as e:
                logger.error(f"Error buscando notas: {e}")
                notes_context = ""
        
        # Si no hay contexto de notas, responder que no hay información
        if not notes_context:
            return f"No encontré notas sobre {query}, {self.user_name}.", False
        
        # Preparar prompt para DeepSeek con contexto de notas
        system_prompt = self._build_system_prompt(notes_context=notes_context)
        
        # Llamar a DeepSeek en thread (Pensando ya se mostró una vez al inicio del comando)
        future = self.threading_manager.execute_async(
            self._call_deepseek,
            command_text,
            system_prompt,
            timeout=60
        )
        
        try:
            response_text = future.result(timeout=60)
        except Exception as e:
            logger.error(f"DeepSeek falló: {e}")
            response_text = "Lo siento, no pude procesar tu solicitud."
        
        return response_text, False  # used_web_search = False
    
    def _get_vector_store(self):
        """Inicialización perezosa del cache vectorial (evita cargar modelo al arranque)."""
        if self._vector_store is not None:
            return self._vector_store
        if not self._vector_cache_enabled:
            return None
        try:
            from src.vector_store import VectorStore
            self._vector_store = VectorStore(
                persist_dir=os.path.join(self.data_dir, "chroma_db"),
                min_similarity=0.88,
                max_cache_entries=2000,
                backend=self._vector_cache_backend,
            )
            logger.info("Cache vectorial inicializado: backend=%s (ahorro de créditos DeepSeek)", self._vector_cache_backend)
            return self._vector_store
        except Exception as e:
            logger.warning("Cache vectorial no disponible: %s", e)
            self._vector_cache_enabled = False
            return None

    async def _process_conversational(self, command_text: str) -> tuple[str, bool]:
        """
        Procesa un comando conversacional con web search + DeepSeek.
        
        Args:
            command_text: Texto del comando
            
        Returns:
            Tupla (response_text, used_web_search)
            
        Requisito: 2.5 - Preservar flujo conversacional de Fase 2
        """
        # Consultar cache vectorial antes de llamar a DeepSeek (ahorro de créditos)
        store = self._get_vector_store()
        if store:
            cached = store.get_cached_response(command_text)
            if cached is not None:
                return cached, False

        # Verificar necesidad de web search
        needs_search = self.query_router.requires_web_search(command_text)
        web_context = ""
        
        # Ejecutar web search si es necesario
        if needs_search and self.web_search:
            self._update_state(SystemState.BUSCANDO)
            self.ui_manager.show_searching_indicator()
            
            # Ejecutar en thread con timeout
            future = self.threading_manager.execute_async(
                self.web_search.search,
                command_text,
                timeout=30
            )
            
            try:
                web_context = future.result(timeout=30)
                if web_context:
                    logger.info(f"Web search completado: {len(web_context)} caracteres")
                else:
                    logger.warning("Web search no retornó resultados")
            except Exception as e:
                logger.error(f"Web search falló: {e}")
                web_context = ""
        
        # Preparar prompt para DeepSeek
        system_prompt = self._build_system_prompt(web_context)
        
        # Llamar a DeepSeek en thread (Pensando ya se mostró una vez al inicio del comando)
        future = self.threading_manager.execute_async(
            self._call_deepseek,
            command_text,
            system_prompt,
            timeout=60
        )
        
        try:
            response_text = future.result(timeout=60)
        except Exception as e:
            logger.error(f"DeepSeek falló: {e}")
            response_text = "Lo siento, no pude procesar tu solicitud."

        # Guardar en cache vectorial para futuras preguntas similares
        if response_text and store:
            if getattr(store, "backend", None) == "supabase":
                logger.info("Guardando respuesta en Supabase (cache vectorial)...")
            store.add_to_cache(command_text, response_text)

        return response_text, bool(web_context)
    async def _process_conversational_with_notes(self, command_text: str, query: str) -> tuple[str, bool]:
        """
        Procesa un comando conversacional con contexto de notas locales.

        Args:
            command_text: Texto del comando
            query: Query para buscar en notas

        Returns:
            Tupla (response_text, used_web_search)

        Requisito: 8.2 - Procesar note_read intent
        """
        notes_context = ""

        # Buscar notas relevantes si Local RAG está habilitado
        if self.local_knowledge and query:
            try:
                # Ejecutar búsqueda en thread separado
                future = self.threading_manager.execute_async(
                    self.local_knowledge.search,
                    query,
                    timeout=5
                )

                notes = future.result(timeout=5)

                if notes:
                    # Formatear contexto
                    notes_context = self.local_knowledge.format_context(notes)
                    logger.info(f"Encontradas {len(notes)} notas relevantes para query: '{query}'")
                else:
                    logger.info(f"No se encontraron notas para query: '{query}'")
                    return f"No encontré notas sobre {query}, {self.user_name}.", False

            except Exception as e:
                logger.error(f"Error buscando notas: {e}")
                notes_context = ""

        # Si no hay contexto de notas, responder que no hay información
        if not notes_context:
            return f"No encontré notas sobre {query}, {self.user_name}.", False

        # Preparar prompt para DeepSeek con contexto de notas
        system_prompt = self._build_system_prompt(notes_context=notes_context)

        # Llamar a DeepSeek en thread (Pensando ya se mostró una vez al inicio del comando)
        future = self.threading_manager.execute_async(
            self._call_deepseek,
            command_text,
            system_prompt,
            timeout=60
        )

        try:
            response_text = future.result(timeout=60)
        except Exception as e:
            logger.error(f"DeepSeek falló: {e}")
            response_text = "Lo siento, no pude procesar tu solicitud."

        return response_text, False  # used_web_search = False


# TODO: Integrar con Amazon Lex para NLU más avanzado
# TODO: Implementar contexto de conversación para seguimiento
# TODO: Agregar soporte para entidades (extraer datos del comando)
# TODO: Implementar aprendizaje de nuevas intenciones desde interacciones
