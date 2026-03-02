"""
Feedback Preventer - Prevención de auto-transcripción de audio

Este módulo implementa un mecanismo de sincronización thread-safe usando
threading.Event para prevenir que Kiro se auto-transcriba cuando está hablando.

El problema que resuelve:
Cuando Amazon Polly reproduce audio por los altavoces, el micrófono captura
ese audio y Vosk lo transcribe, generando comandos erróneos o bucles de
conversación. Este módulo "silencia" la captura de audio mientras Kiro habla,
sin modificar los parámetros de PyAudio o Vosk.

Mecanismo:
- threading.Event actúa como flag compartido thread-safe
- set_speaking() antes de reproducir audio → flag = True
- Main thread verifica is_speaking() → si True, ignora audio
- clear_speaking() después de reproducir → flag = False
- Main thread vuelve a procesar audio normalmente

Requisitos implementados:
- 1.1: Establecer Speaking_State al reproducir
- 1.2: Ignorar audio mientras Speaking_State es verdadero
- 1.3: Limpiar Speaking_State en <100ms
- 1.4: Reanudar captura después de hablar
- 1.5: Usar threading.Event para sincronización
- 11.1: Thread-safety garantizado
"""

import threading
import logging
import time
from typing import Optional


logger = logging.getLogger(__name__)


class FeedbackPreventer:
    """
    Previene feedback de audio usando threading.Event para sincronización.
    
    El mecanismo funciona así:
    1. Antes de reproducir audio: set_speaking() → speaking_event.set()
    2. Main thread verifica: is_speaking() → speaking_event.is_set()
    3. Si True: ignorar audio del stream
    4. Después de reproducir: clear_speaking() → speaking_event.clear()
    
    threading.Event es thread-safe por diseño, no requiere locks adicionales.
    
    Attributes:
        _speaking_event: threading.Event para sincronización
        _transition_count: Contador de transiciones (para debugging/testing)
        _lock: Lock solo para el contador (no para el Event)
    """
    
    def __init__(self):
        """
        Inicializa el Event de sincronización.
        
        threading.Event internamente usa un Condition variable + boolean flag:
        - set() → flag = True, notifica a todos los threads esperando
        - clear() → flag = False
        - is_set() → retorna flag (lectura atómica)
        """
        # threading.Event: primitiva de sincronización thread-safe
        self._speaking_event = threading.Event()
        
        # Logger para debugging
        self.logger = logging.getLogger(__name__)
        
        # Contador de transiciones (para debugging/testing)
        self._transition_count = 0
        self._lock = threading.Lock()  # Solo para el contador
        
        self.logger.info("FeedbackPreventer inicializado")
    
    def set_speaking(self):
        """
        Marca que Kiro está hablando.
        
        Debe llamarse ANTES de reproducir audio.
        Thread-safe, puede llamarse desde cualquier thread.
        
        Flujo interno:
        1. Event.set() establece flag interno a True (operación atómica)
        2. Notifica a todos los threads bloqueados en wait()
        3. Retorna inmediatamente (no bloqueante)
        
        Complejidad: O(1), ~100 nanosegundos
        
        Requisito: 1.1 - Establecer Speaking_State al reproducir
        """
        self._speaking_event.set()
        
        with self._lock:
            self._transition_count += 1
        
        self.logger.debug("FeedbackPreventer: Speaking mode ENABLED")
    
    def clear_speaking(self):
        """
        Marca que Kiro terminó de hablar.
        
        Debe llamarse DESPUÉS de reproducir audio.
        Thread-safe, puede llamarse desde cualquier thread.
        
        Flujo interno:
        1. Event.clear() establece flag interno a False (operación atómica)
        2. Retorna inmediatamente (no bloqueante)
        
        Complejidad: O(1), ~100 nanosegundos
        
        Requisito: 1.3 - Limpiar Speaking_State en <100ms
        """
        self._speaking_event.clear()
        
        with self._lock:
            self._transition_count += 1
        
        self.logger.debug("FeedbackPreventer: Speaking mode DISABLED")
    
    def is_speaking(self) -> bool:
        """
        Verifica si Kiro está hablando actualmente.
        
        Thread-safe, puede llamarse desde main thread.
        
        Flujo interno:
        1. Event.is_set() lee flag interno (lectura atómica)
        2. Retorna inmediatamente (no bloqueante)
        
        Complejidad: O(1), ~50 nanosegundos
        Thread-safe: Sí, lectura atómica garantizada por CPython GIL
        
        Returns:
            True si está hablando (audio debe ignorarse)
            False si puede escuchar (audio debe procesarse)
            
        Requisito: 1.2 - Verificar Speaking_State para ignorar audio
        """
        return self._speaking_event.is_set()
    
    def wait_until_finished(self, timeout: Optional[float] = None) -> bool:
        """
        Bloquea hasta que Kiro termine de hablar.
        
        Útil para sincronización en tests o shutdown.
        
        Flujo interno:
        1. Si flag es False, retorna inmediatamente
        2. Si flag es True, bloquea hasta que clear() sea llamado
        3. Si timeout expira, retorna False
        
        Args:
            timeout: Segundos máximos a esperar (None = infinito)
            
        Returns:
            True si terminó de hablar
            False si timeout expiró
            
        Requisito: 11.1 - Sincronización thread-safe
        """
        if not self.is_speaking():
            return True
        
        # Esperar a que el event sea cleared
        # Polling con sleep corto para evitar bloqueo indefinido
        start_time = time.time()
        
        while self.is_speaking():
            if timeout and (time.time() - start_time) > timeout:
                self.logger.warning("wait_until_finished: Timeout alcanzado")
                return False
            time.sleep(0.01)  # 10ms polling
        
        return True
    
    def get_transition_count(self) -> int:
        """
        Retorna número de transiciones (para testing).
        
        Returns:
            Número total de llamadas a set_speaking() y clear_speaking()
        """
        with self._lock:
            return self._transition_count


# TODO: Agregar métricas de tiempo hablando vs escuchando
# TODO: Implementar callback cuando cambia estado (para UI)
# TODO: Agregar soporte para múltiples fuentes de audio simultáneas
