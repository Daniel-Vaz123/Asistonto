"""
Audio Manager - Gestión de dispositivos de audio

Este módulo implementa la clase AudioManager que gestiona la captura continua
de audio desde el micrófono y la reproducción de audio en el altavoz.

Requisitos implementados:
- 1.1: Escuchar audio continuamente desde el micrófono
- 9.2: Calibrar el micrófono y verificar niveles de audio
- 7.2: Reproducir audio de respuesta inmediatamente
"""

import pyaudio
import numpy as np
import threading
import queue
import logging
import time
from typing import Optional, Dict, List
from collections import deque


logger = logging.getLogger(__name__)


class AudioManager:
    """
    Gestiona dispositivos de audio (micrófono y altavoz) con captura continua
    y reproducción de audio.
    
    Características:
    - Captura continua de audio con buffer circular robusto
    - Calibración automática de micrófono
    - Reproducción de audio con cola de gestión
    - Manejo de reconexión si el micrófono falla
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        channels: int = 1,
        input_device_index: Optional[int] = None,
        output_device_index: Optional[int] = None,
        buffer_duration: float = 10.0
    ):
        """
        Inicializa el AudioManager con configuración de audio.
        
        Args:
            sample_rate: Frecuencia de muestreo en Hz (default: 16000)
            chunk_size: Tamaño de chunk para streaming en tiempo real (default: 1024)
            channels: Número de canales de audio (default: 1 - mono)
            input_device_index: Índice del dispositivo de entrada (None = default)
            output_device_index: Índice del dispositivo de salida (None = default)
            buffer_duration: Duración del buffer circular en segundos (default: 10.0)
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.input_device_index = input_device_index
        self.output_device_index = output_device_index
        
        # Calcular tamaño del buffer circular
        self.buffer_max_chunks = int((buffer_duration * sample_rate) / chunk_size)
        
        # Buffer circular robusto usando deque
        self._audio_buffer: deque = deque(maxlen=self.buffer_max_chunks)
        self._buffer_lock = threading.Lock()
        
        # Cola de reproducción para múltiples audios
        self._playback_queue: queue.Queue = queue.Queue()
        
        # Estado de captura
        self._is_capturing = False
        self._capture_thread: Optional[threading.Thread] = None
        self._playback_thread: Optional[threading.Thread] = None
        
        # PyAudio instance
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._input_stream: Optional[pyaudio.Stream] = None
        self._output_stream: Optional[pyaudio.Stream] = None
        
        # Calibración
        self._noise_level: float = 0.0
        self._is_calibrated = False
        
        # Reconexión
        self._max_reconnect_attempts = 3
        self._reconnect_delay = 2.0
        
        logger.info(
            f"AudioManager inicializado: sample_rate={sample_rate}, "
            f"chunk_size={chunk_size}, channels={channels}"
        )
    
    def _initialize_pyaudio(self) -> None:
        """Inicializa PyAudio y verifica dispositivos disponibles."""
        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()
            logger.info("PyAudio inicializado correctamente")

    
    def list_audio_devices(self) -> List[Dict]:
        """
        Lista todos los dispositivos de audio disponibles.
        
        Returns:
            Lista de diccionarios con información de dispositivos
        """
        self._initialize_pyaudio()
        devices = []
        
        for i in range(self._pyaudio.get_device_count()):
            try:
                device_info = self._pyaudio.get_device_info_by_index(i)
                devices.append({
                    'index': i,
                    'name': device_info.get('name'),
                    'max_input_channels': device_info.get('maxInputChannels'),
                    'max_output_channels': device_info.get('maxOutputChannels'),
                    'default_sample_rate': device_info.get('defaultSampleRate')
                })
            except Exception as e:
                logger.warning(f"Error al obtener info del dispositivo {i}: {e}")
        
        return devices
    
    def calibrate_microphone(self, duration: float = 2.0) -> Dict:
        """
        Calibra el micrófono analizando niveles de ruido de fondo.
        
        Este método captura audio durante un período corto para determinar
        el nivel de ruido ambiente y ajustar la sensibilidad automáticamente.
        
        Args:
            duration: Duración de la calibración en segundos (default: 2.0)
        
        Returns:
            Diccionario con resultados de calibración:
            - noise_level: Nivel de ruido detectado (RMS)
            - recommended_threshold: Umbral recomendado para detección de voz
            - device_info: Información del dispositivo de entrada
        
        Requisito: 9.2 - Calibrar el micrófono y verificar niveles de audio
        """
        logger.info(f"Iniciando calibración del micrófono ({duration}s)...")
        
        self._initialize_pyaudio()
        
        # Obtener información del dispositivo de entrada
        if self.input_device_index is not None:
            device_info = self._pyaudio.get_device_info_by_index(self.input_device_index)
        else:
            device_info = self._pyaudio.get_default_input_device_info()
        
        logger.info(f"Dispositivo de entrada: {device_info.get('name')}")
        
        # Abrir stream temporal para calibración
        try:
            calibration_stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=self.chunk_size
            )
            
            # Capturar audio durante el período de calibración
            num_chunks = int((duration * self.sample_rate) / self.chunk_size)
            audio_samples = []
            
            for _ in range(num_chunks):
                try:
                    audio_data = calibration_stream.read(self.chunk_size, exception_on_overflow=False)
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    audio_samples.append(audio_array)
                except Exception as e:
                    logger.warning(f"Error durante captura de calibración: {e}")
            
            calibration_stream.stop_stream()
            calibration_stream.close()
            
            # Analizar niveles de ruido
            if audio_samples:
                all_samples = np.concatenate(audio_samples)
                
                # Calcular RMS (Root Mean Square) como nivel de ruido
                self._noise_level = np.sqrt(np.mean(all_samples.astype(np.float32) ** 2))
                
                # Calcular umbral recomendado (3x el nivel de ruido)
                recommended_threshold = self._noise_level * 3.0
                
                self._is_calibrated = True
                
                result = {
                    'noise_level': float(self._noise_level),
                    'recommended_threshold': float(recommended_threshold),
                    'device_info': {
                        'name': device_info.get('name'),
                        'index': device_info.get('index'),
                        'sample_rate': device_info.get('defaultSampleRate')
                    },
                    'calibrated': True
                }
                
                logger.info(
                    f"Calibración completada: noise_level={self._noise_level:.2f}, "
                    f"threshold={recommended_threshold:.2f}"
                )
                
                return result
            else:
                raise RuntimeError("No se pudo capturar audio durante la calibración")
        
        except Exception as e:
            logger.error(f"Error durante calibración del micrófono: {e}")
            raise
    
    def start_continuous_capture(self) -> None:
        """
        Inicia la captura continua de audio en un thread separado.
        
        El audio capturado se almacena en un buffer circular que mantiene
        los últimos N segundos de audio (configurado en buffer_duration).
        
        Requisito: 1.1 - Escuchar audio continuamente desde el micrófono
        """
        if self._is_capturing:
            logger.warning("La captura ya está en progreso")
            return
        
        logger.info("Iniciando captura continua de audio...")
        
        self._is_capturing = True
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name="AudioCaptureThread"
        )
        self._capture_thread.start()
        
        logger.info("Captura continua iniciada correctamente")
    
    def _capture_loop(self) -> None:
        """
        Loop principal de captura de audio con manejo de reconexión.
        
        Este método se ejecuta en un thread separado y maneja automáticamente
        la reconexión si el micrófono falla.
        """
        reconnect_attempts = 0
        
        while self._is_capturing:
            try:
                self._initialize_pyaudio()
                
                # Abrir stream de entrada
                self._input_stream = self._pyaudio.open(
                    format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=self.input_device_index,
                    frames_per_buffer=self.chunk_size,
                    stream_callback=None
                )
                
                logger.info("Stream de entrada abierto correctamente")
                reconnect_attempts = 0  # Reset contador de reconexión
                
                # Loop de captura
                while self._is_capturing:
                    try:
                        # Leer chunk de audio
                        audio_data = self._input_stream.read(
                            self.chunk_size,
                            exception_on_overflow=False
                        )
                        
                        # Agregar al buffer circular con lock
                        with self._buffer_lock:
                            self._audio_buffer.append(audio_data)
                    
                    except IOError as e:
                        logger.warning(f"IOError durante captura: {e}")
                        # Continuar intentando capturar
                        time.sleep(0.1)
                    
                    except Exception as e:
                        logger.error(f"Error inesperado durante captura: {e}")
                        break
            
            except Exception as e:
                logger.error(f"Error al abrir stream de entrada: {e}")
                
                # Intentar reconexión
                reconnect_attempts += 1
                
                if reconnect_attempts <= self._max_reconnect_attempts:
                    logger.info(
                        f"Intentando reconectar ({reconnect_attempts}/"
                        f"{self._max_reconnect_attempts})..."
                    )
                    time.sleep(self._reconnect_delay)
                else:
                    logger.error("Máximo de intentos de reconexión alcanzado")
                    self._is_capturing = False
                    break
            
            finally:
                # Cerrar stream si está abierto
                if self._input_stream is not None:
                    try:
                        self._input_stream.stop_stream()
                        self._input_stream.close()
                    except Exception as e:
                        logger.warning(f"Error al cerrar stream: {e}")
                    self._input_stream = None
        
        logger.info("Loop de captura finalizado")
    
    def stop_continuous_capture(self) -> None:
        """Detiene la captura continua de audio."""
        if not self._is_capturing:
            logger.warning("La captura no está en progreso")
            return
        
        logger.info("Deteniendo captura continua...")
        
        self._is_capturing = False
        
        # Esperar a que el thread termine
        if self._capture_thread is not None:
            self._capture_thread.join(timeout=5.0)
            if self._capture_thread.is_alive():
                logger.warning("El thread de captura no terminó en el tiempo esperado")
        
        logger.info("Captura continua detenida")
    
    def get_audio_chunk(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Obtiene el chunk de audio más reciente del buffer.
        
        Args:
            timeout: Tiempo máximo de espera en segundos (default: 1.0)
        
        Returns:
            Bytes de audio o None si no hay datos disponibles
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._buffer_lock:
                if len(self._audio_buffer) > 0:
                    return self._audio_buffer[-1]  # Retornar el más reciente
            
            time.sleep(0.01)  # Pequeña espera para no saturar CPU
        
        return None
    
    def get_audio_buffer(self, num_chunks: Optional[int] = None) -> List[bytes]:
        """
        Obtiene múltiples chunks del buffer circular.
        
        Args:
            num_chunks: Número de chunks a obtener (None = todos)
        
        Returns:
            Lista de chunks de audio (bytes)
        """
        with self._buffer_lock:
            if num_chunks is None:
                return list(self._audio_buffer)
            else:
                # Obtener los últimos N chunks
                return list(self._audio_buffer)[-num_chunks:]

    
    def clear_buffer(self) -> None:
        """Limpia el buffer circular de audio."""
        with self._buffer_lock:
            self._audio_buffer.clear()
        logger.debug("Buffer de audio limpiado")
    
    def play_audio(self, audio_data: bytes, block: bool = True) -> None:
        """
        Reproduce audio en el altavoz.
        
        Args:
            audio_data: Bytes de audio a reproducir
            block: Si True, bloquea hasta que termine la reproducción
        
        Requisito: 7.2 - Reproducir audio de respuesta inmediatamente
        """
        if not audio_data:
            logger.warning("No hay datos de audio para reproducir")
            return
        
        # Agregar a la cola de reproducción
        self._playback_queue.put(audio_data)
        
        # Iniciar thread de reproducción si no está activo
        if self._playback_thread is None or not self._playback_thread.is_alive():
            self._playback_thread = threading.Thread(
                target=self._playback_loop,
                daemon=True,
                name="AudioPlaybackThread"
            )
            self._playback_thread.start()
        
        # Esperar si se solicita bloqueo
        if block:
            # Esperar hasta que la cola esté vacía
            self._playback_queue.join()
    
    def _playback_loop(self) -> None:
        """
        Loop de reproducción de audio que procesa la cola de reproducción.
        
        Este método gestiona la cola de reproducción para múltiples audios,
        asegurando que se reproduzcan en orden sin superposición.
        """
        self._initialize_pyaudio()
        
        while True:
            try:
                # Obtener audio de la cola (con timeout para permitir salida)
                audio_data = self._playback_queue.get(timeout=1.0)
                
                try:
                    # Abrir stream de salida
                    output_stream = self._pyaudio.open(
                        format=pyaudio.paInt16,
                        channels=self.channels,
                        rate=self.sample_rate,
                        output=True,
                        output_device_index=self.output_device_index,
                        frames_per_buffer=self.chunk_size
                    )
                    
                    # Reproducir audio en chunks
                    chunk_size_bytes = self.chunk_size * 2  # 2 bytes por sample (int16)
                    
                    for i in range(0, len(audio_data), chunk_size_bytes):
                        chunk = audio_data[i:i + chunk_size_bytes]
                        output_stream.write(chunk)
                    
                    # Cerrar stream
                    output_stream.stop_stream()
                    output_stream.close()
                    
                    logger.debug(f"Audio reproducido: {len(audio_data)} bytes")
                
                except Exception as e:
                    logger.error(f"Error durante reproducción de audio: {e}")
                
                finally:
                    # Marcar tarea como completada
                    self._playback_queue.task_done()
            
            except queue.Empty:
                # No hay más audio en la cola, salir del loop
                break
            
            except Exception as e:
                logger.error(f"Error en loop de reproducción: {e}")
                break
        
        logger.debug("Loop de reproducción finalizado")
    
    def is_capturing(self) -> bool:
        """Retorna True si la captura está activa."""
        return self._is_capturing
    
    def is_calibrated(self) -> bool:
        """Retorna True si el micrófono ha sido calibrado."""
        return self._is_calibrated
    
    def get_noise_level(self) -> float:
        """Retorna el nivel de ruido detectado durante la calibración."""
        return self._noise_level
    
    def get_buffer_size(self) -> int:
        """Retorna el número de chunks actualmente en el buffer."""
        with self._buffer_lock:
            return len(self._audio_buffer)
    
    def cleanup(self) -> None:
        """
        Limpia recursos y cierra conexiones de PyAudio.
        
        Este método debe llamarse al finalizar el uso del AudioManager.
        """
        logger.info("Limpiando recursos de AudioManager...")
        
        # Detener captura si está activa
        if self._is_capturing:
            self.stop_continuous_capture()
        
        # Cerrar streams
        if self._input_stream is not None:
            try:
                self._input_stream.stop_stream()
                self._input_stream.close()
            except Exception as e:
                logger.warning(f"Error al cerrar input stream: {e}")
            self._input_stream = None
        
        if self._output_stream is not None:
            try:
                self._output_stream.stop_stream()
                self._output_stream.close()
            except Exception as e:
                logger.warning(f"Error al cerrar output stream: {e}")
            self._output_stream = None
        
        # Terminar PyAudio
        if self._pyaudio is not None:
            try:
                self._pyaudio.terminate()
            except Exception as e:
                logger.warning(f"Error al terminar PyAudio: {e}")
            self._pyaudio = None
        
        # Limpiar buffer
        self.clear_buffer()
        
        logger.info("Recursos limpiados correctamente")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
        return False


# TODO: Implementar filtrado de ruido básico usando filtros digitales
# TODO: Implementar detección de actividad de voz (VAD) para optimizar procesamiento
# TODO: Considerar implementar compresión de audio para reducir ancho de banda
# TODO: Agregar métricas de calidad de audio (SNR, clipping detection)
