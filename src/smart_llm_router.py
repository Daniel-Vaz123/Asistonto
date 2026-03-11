"""
Smart LLM Router - Clasificación inteligente de comandos usando DeepSeek

Este módulo reemplaza IntentClassifier basado en regex por clasificación LLM
que entiende variaciones naturales del lenguaje ("apunta por ahí que...",
"recuérdame que...", "anota esto...").

Retorna JSON estructurado con intent, parámetros y nivel de confianza.

Requisitos implementados:
- 1.1: Clasificar comandos con DeepSeek
- 1.2: Retornar JSON estructurado
- 1.3: Soportar todos los intents (conversational, note_create, note_read, youtube, app_launch, web_search)
- 1.4: Verificar confidence threshold
- 1.5: Fallback a conversational si confidence baja
- 1.6: Timeout de 3 segundos
- 1.7: Manejo de errores con fallback
- 1.8: Extraer parámetros según tipo de intent
- 1.9: Mapear intents a enums
"""

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Tipos de intent soportados"""
    CONVERSATIONAL = "conversational"
    ACTION = "action"


class ActionType(Enum):
    """Tipos de acción soportados"""
    YOUTUBE = "youtube"
    APP = "app"
    WEB = "web"
    FILE = "file"


@dataclass
class Intent:
    """
    Resultado de clasificación.
    
    Attributes:
        intent_type: Tipo de intención (conversational o action)
        action_type: Tipo de acción (solo si intent_type es ACTION)
        parameters: Parámetros extraídos del comando
        confidence: Nivel de confianza (0.0-1.0)
    """
    intent_type: IntentType
    action_type: Optional[ActionType] = None
    parameters: Dict[str, Any] = None
    confidence: float = 1.0
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class SmartLLMRouter:
    """
    Clasificador inteligente usando DeepSeek.
    
    Reemplaza IntentClassifier basado en regex con clasificación LLM
    que entiende variaciones naturales del lenguaje.
    """
    
    # Prompt de clasificación con few-shot examples
    CLASSIFICATION_SYSTEM_PROMPT = """Eres un clasificador de intenciones para un asistente de voz.

Tu tarea es analizar comandos del usuario y retornar un JSON con esta estructura EXACTA:
{
  "intent": "conversational" | "file" | "youtube" | "app" | "web",
  "parameters": {},
  "confidence": 0.0-1.0
}

INTENTS SOPORTADOS:

1. conversational: Preguntas generales, conversación
   - Ejemplos: "¿Qué es Python?", "Cuéntame un chiste", "¿Cómo estás?"
   - Parameters: {}

2. file: Crear/guardar nota o leer notas
   - Ejemplos CREAR (sé AGRESIVO, cualquier cosa que parezca información a guardar):
     * "Toma nota: reunión mañana"
     * "Apunta por ahí que la función compila"
     * "Recuérdame comprar leche"
     * "Anota esto: el proyecto va al 80%"
     * "Guarda que mañana tengo clase"
     * "El mini sumo está casi listo"
     * "Avancé bastante en las características"
   - Ejemplos LEER (CRÍTICO - cualquier mención de revisar/leer/buscar notas):
     * "¿Qué notas tengo sobre ChromaSys?"
     * "Busca mis notas de Python"
     * "¿Qué hemos anotado del mini sumo?"
     * "Revisa mis notas sobre el proyecto"
     * "¿Qué apunté sobre la reunión?"
     * "Según mis notas, ¿cómo va el avance?"
     * "Revisa las notas guardadas y dime de qué es mi junta"
     * "Qué dice la nota de mañana"
     * "Dime de qué trata la nota sobre la escuela"
     * "Revisa mis apuntes del proyecto"
     * "Lee mis notas y dime qué tengo pendiente"
     * "Consulta mis notas sobre el mini sumo"
     * "Busca en mis apuntes sobre la reunión"
     * "¿Qué información tengo guardada sobre...?"
   - Parameters CREAR: {"content": "texto de la nota"}
   - Parameters LEER: {"query": "término de búsqueda", "action": "read"}

3. youtube: Reproducir video de YouTube
   - Ejemplos: "Pon música relajante en YouTube", "Reproduce videos de Python", "Busca en YouTube tutoriales"
   - Parameters: {"query": "término de búsqueda"}

4. app: Abrir aplicación
   - Ejemplos: "Abre Chrome", "Inicia Spotify", "Ejecuta el bloc de notas"
   - Parameters: {"app_name": "nombre de la app"}

5. web: Buscar en internet o abrir sitio web
   - Ejemplos: "Busca en Google sobre Python", "Ve a Facebook", "Abre Gmail"
   - Parameters: {"website": "nombre del sitio"} o {"query": "término de búsqueda"}

REGLAS CRÍTICAS:
- Retorna SOLO el JSON, sin texto adicional
- confidence debe ser 0.0-1.0 (usa 0.9+ si estás seguro, 0.7-0.9 si hay ambigüedad, <0.7 si no estás seguro)
- Tolera errores de transcripción (ora/hora, ola/hola, anota/nota)
- Para NOTAS: Si el usuario menciona información que parece importante o dice algo como "apunta", "anota", "guarda", "recuerda", clasifica como file con {"content": "..."}
- Para LEER NOTAS: Si menciona "revisar", "leer", "buscar", "consultar", "qué dice", "qué tengo" seguido de "notas", "apuntes", "guardado", clasifica SIEMPRE como file con {"query": "...", "action": "read"}
- SÉ AGRESIVO con note_create: Si hay duda entre conversational y file, elige file si el contenido parece información a recordar
- SÉ MUY AGRESIVO con note_read: Si el usuario pregunta por información guardada, notas, apuntes, o dice "revisa", "lee", "busca" + "notas/apuntes", SIEMPRE clasifica como file con action="read"
"""
    
    def __init__(
        self,
        deepseek_client,
        timeout: int = 3,
        confidence_threshold: float = 0.7,
        temperature: float = 0.1,
        max_tokens: int = 200
    ):
        """
        Inicializa el Smart LLM Router.
        
        Args:
            deepseek_client: Cliente de DeepSeek configurado
            timeout: Timeout en segundos para clasificación
            confidence_threshold: Umbral mínimo de confianza
            temperature: Temperature para DeepSeek (0.1 = determinístico)
            max_tokens: Máximo de tokens en respuesta
        """
        self.client = deepseek_client
        self.timeout = timeout
        self.confidence_threshold = confidence_threshold
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(
            f"SmartLLMRouter inicializado: "
            f"timeout={timeout}s, confidence_threshold={confidence_threshold}"
        )
    
    def classify(self, command: str) -> Intent:
        """
        Clasifica comando usando DeepSeek.
        
        Flujo:
        1. Construir prompt de clasificación
        2. Llamar a DeepSeek con timeout
        3. Parsear JSON response
        4. Validar estructura y campos
        5. Verificar confidence threshold
        6. Retornar Intent o fallback
        
        Args:
            command: Comando del usuario
            
        Returns:
            Intent con tipo, acción, parámetros y confianza
        """
        start_time = time.time()
        
        try:
            # Construir prompt
            user_prompt = f"Comando: {command}"
            
            # Llamar a DeepSeek con timeout
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": self.CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout
            )
            
            # Extraer texto de respuesta
            response_text = response.choices[0].message.content.strip()
            
            # Parsear JSON
            data = self._parse_json_response(response_text)
            if not data:
                return self._fallback_intent("JSON inválido")
            
            # Validar estructura
            if not self._validate_json_structure(data):
                return self._fallback_intent("Estructura JSON inválida")
            
            # Verificar confidence threshold
            confidence = data.get("confidence", 0.0)
            if confidence < self.confidence_threshold:
                self.logger.warning(
                    f"Confidence baja ({confidence:.2f}), usando fallback"
                )
                return self._fallback_intent(f"Confidence baja: {confidence:.2f}")
            
            # Crear Intent
            intent = self._create_intent_from_json(data)
            
            # Log resultado
            elapsed = time.time() - start_time
            self.logger.info(
                f"Clasificación exitosa: intent={data['intent']}, "
                f"confidence={confidence:.2f}, time={elapsed:.3f}s"
            )
            
            return intent
            
        except TimeoutError:
            self.logger.error("Timeout en clasificación DeepSeek")
            return self._fallback_intent("Timeout")
        
        except Exception as e:
            self.logger.error(f"Error en clasificación: {e}", exc_info=True)
            return self._fallback_intent(f"Exception: {str(e)}")
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """
        Parsea JSON de respuesta con fallback multi-nivel.
        
        Args:
            response: Texto de respuesta de DeepSeek
            
        Returns:
            Dict con JSON parseado o None si falla
        """
        try:
            # Intentar parsear directamente
            return json.loads(response)
        except json.JSONDecodeError:
            # Intentar extraer JSON de texto con markdown
            try:
                # Buscar JSON entre ```json y ```
                if "```json" in response:
                    start = response.find("```json") + 7
                    end = response.find("```", start)
                    json_str = response[start:end].strip()
                    return json.loads(json_str)
                
                # Buscar JSON entre { y }
                start = response.find("{")
                end = response.rfind("}") + 1
                if start != -1 and end > start:
                    json_str = response[start:end]
                    return json.loads(json_str)
                
            except Exception:
                pass
            
            self.logger.error(f"No se pudo parsear JSON: {response}")
            return None
    
    def _validate_json_structure(self, data: Dict) -> bool:
        """
        Valida estructura de JSON.
        
        Args:
            data: Dict con JSON parseado
            
        Returns:
            True si estructura es válida, False en caso contrario
        """
        # Verificar campos requeridos
        if "intent" not in data:
            self.logger.error("JSON sin campo 'intent'")
            return False
        
        if "parameters" not in data:
            self.logger.error("JSON sin campo 'parameters'")
            return False
        
        if "confidence" not in data:
            self.logger.error("JSON sin campo 'confidence'")
            return False
        
        # Validar tipos
        if not isinstance(data["intent"], str):
            self.logger.error("Campo 'intent' no es string")
            return False
        
        if not isinstance(data["parameters"], dict):
            self.logger.error("Campo 'parameters' no es dict")
            return False
        
        if not isinstance(data["confidence"], (int, float)):
            self.logger.error("Campo 'confidence' no es número")
            return False
        
        # Validar valores
        valid_intents = [
            "conversational", "file", "youtube", "app", "web"
        ]
        if data["intent"] not in valid_intents:
            self.logger.error(f"Intent inválido: {data['intent']}")
            return False
        
        confidence = data["confidence"]
        if not (0.0 <= confidence <= 1.0):
            self.logger.error(f"Confidence fuera de rango: {confidence}")
            return False
        
        return True
    
    def _create_intent_from_json(self, data: Dict) -> Intent:
        """
        Crea Intent desde JSON validado.
        
        Args:
            data: Dict con JSON validado
            
        Returns:
            Intent object
        """
        intent_str = data["intent"]
        parameters = data["parameters"]
        confidence = data["confidence"]
        
        # Mapear intent string a enums
        if intent_str == "conversational":
            return Intent(
                intent_type=IntentType.CONVERSATIONAL,
                parameters=parameters,
                confidence=confidence
            )
        
        # Mapear action intents
        action_mapping = {
            "youtube": ActionType.YOUTUBE,
            "app": ActionType.APP,
            "web": ActionType.WEB,
            "file": ActionType.FILE
        }
        
        action_type = action_mapping.get(intent_str)
        if action_type:
            return Intent(
                intent_type=IntentType.ACTION,
                action_type=action_type,
                parameters=parameters,
                confidence=confidence
            )
        
        # Fallback (no debería llegar aquí si validación funciona)
        return self._fallback_intent("Intent no mapeado")
    
    def _fallback_intent(self, reason: str) -> Intent:
        """
        Retorna intent conversational como fallback.
        
        Args:
            reason: Razón del fallback
            
        Returns:
            Intent conversational con confidence baja
        """
        self.logger.warning(f"Usando fallback: {reason}")
        return Intent(
            intent_type=IntentType.CONVERSATIONAL,
            parameters={},
            confidence=0.5
        )
