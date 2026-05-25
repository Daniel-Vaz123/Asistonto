# Implementation Plan: GUI Avatar Fase 1 Offline

## Overview

Migración de la interfaz de terminal de Asistonto a una GUI moderna con CustomTkinter, avatar visual animado, STT offline con Vosk, TTS offline con pyttsx3 y manejador de comandos locales. La implementación sigue la arquitectura de tres hilos (Main/GUI, Audio, TTS) con comunicación thread-safe via `queue.Queue`.

## Tasks

- [x] 1. Preparar dependencias y configuración base
  - [x] 1.1 Agregar nuevas dependencias a `requirements.txt`
    - Añadir `customtkinter>=5.2.0` y `pyttsx3>=2.90` al bloque de GUI Fase 1
    - _Requirements: 10.1_

  - [x] 1.2 Actualizar `config.json` con la clave `vosk_model_path`
    - Agregar `"vosk_model_path": "models/vosk-model-small-es-0.42"` al JSON raíz
    - _Requirements: 10.4_

- [x] 2. Implementar módulo de tema visual
  - [x] 2.1 Crear `src/gui/theme.py` con constantes de color y tipografía
    - Definir `BG_PRIMARY`, `BG_SECONDARY`, `ACCENT_CYAN`, `ACCENT_PURPLE`, `ACCENT_GREEN`, `TEXT_PRIMARY`, `TEXT_SECONDARY`
    - Definir `AVATAR_COLORS` (dict estado→color) y `STATE_LABELS` (dict estado→texto)
    - Definir constantes de fuente: `FONT_FAMILY`, `FONT_SIZE_SM/MD/LG`, `FONT_BOLD`, `FONT_NORMAL`, `FONT_SMALL`
    - Crear `src/gui/__init__.py` vacío
    - _Requirements: 1.1, 1.4_

- [x] 3. Implementar AvatarWidget
  - [x] 3.1 Crear `src/gui/avatar_widget.py` con `AvatarState` enum y clase `AvatarWidget`
    - Definir `AvatarState(Enum)` con valores IDLE, LISTENING, PROCESSING, SPEAKING
    - Implementar `AvatarWidget(ctk.CTkFrame)` con canvas interno y `AnimationState` dataclass
    - Implementar `set_state(state: AvatarState)` idempotente: si `state == self._current_state`, retornar sin efectos secundarios
    - Implementar `_cancel_animation()` que cancela el `after()` pendiente
    - Implementar `_animate_idle()`: respiración suave escala 0.8→1.0, ciclo 3000 ms, color `AVATAR_COLORS["IDLE"]`
    - Implementar `_animate_listening()`: pulso rápido escala 0.9→1.1, ciclo 800 ms, color `ACCENT_CYAN`
    - Implementar `_animate_processing()`: arco rotatorio, ciclo 1000 ms, color `ACCENT_PURPLE`
    - Implementar `_animate_speaking()`: ondas concéntricas, ciclo 400 ms, color `ACCENT_GREEN`
    - Garantizar que la transición completa en < 200 ms (cancelar animación anterior antes de iniciar nueva)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 3.2 Escribir property test para AvatarWidget — Property 1: Invariante de estado único
    - **Property 1: Invariante de Estado del Avatar**
    - **Validates: Requirements 2.1**
    - Usar `hypothesis` con `st.lists(st.sampled_from(list(AvatarState)), min_size=1, max_size=50)`
    - Verificar que tras cada `set_state()`, `widget._current_state` es exactamente uno de los cuatro estados válidos
    - Archivo: `tests/gui/test_avatar_widget.py`

  - [ ]* 3.3 Escribir property test para AvatarWidget — Property 2: Idempotencia de set_state
    - **Property 2: Idempotencia de set_state**
    - **Validates: Requirements 2.2**
    - Usar `hypothesis` con `st.sampled_from(list(AvatarState))`
    - Verificar que llamar `set_state(s)` dos veces consecutivas no cambia `after_id` en la segunda llamada
    - Archivo: `tests/gui/test_avatar_widget.py`

- [x] 4. Implementar ChatLogWidget
  - [x] 4.1 Crear `src/gui/chat_log_widget.py` con clase `ChatLogWidget`
    - Implementar `ChatLogWidget(ctk.CTkFrame)` con `ctk.CTkTextbox` interno y tags de color
    - Implementar `add_user_message(text)`: formato `[HH:MM:SS] Tú: <text>`, color `ACCENT_CYAN`, auto-scroll
    - Implementar `add_assistant_message(text)`: formato `[HH:MM:SS] Asistonto: <text>`, color `ACCENT_GREEN`, auto-scroll
    - Implementar `add_error_message(text)`: color `#ef4444`, auto-scroll
    - Implementar `_append(text, tag)`: inserta texto con tag y llama `see("end")`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 4.2 Escribir property test para ChatLogWidget — Property 3: Mensajes contienen timestamp
    - **Property 3: Mensajes del Chat Log contienen texto y timestamp**
    - **Validates: Requirements 3.1, 3.2**
    - Usar `hypothesis` con `st.text(min_size=1, max_size=500).filter(lambda s: s.strip())`
    - Verificar que el contenido del textbox contiene `text` y un timestamp `HH:MM:SS`
    - Archivo: `tests/gui/test_chat_log_widget.py`

  - [ ]* 4.3 Escribir property test para ChatLogWidget — Property 4: No-pérdida de mensajes
    - **Property 4: No-pérdida de mensajes en el Chat Log**
    - **Validates: Requirements 3.3**
    - Usar `hypothesis` con lista de tuplas `(sampled_from(["user","assistant"]), text_strategy)`
    - Verificar que tras agregar todos los mensajes, cada texto original aparece en el textbox
    - Archivo: `tests/gui/test_chat_log_widget.py`

- [x] 5. Implementar MainWindow y protocolo de eventos
  - [x] 5.1 Crear `src/gui/main_window.py` con `GUIEvent`, `EventType` y clase `MainWindow`
    - Definir `EventType(Enum)`: TRANSCRIPTION, WAKE_WORD, STATE_CHANGE, ERROR, TTS_DONE
    - Definir `GUIEvent(dataclass)` con campos `type`, `payload`, `timestamp`
    - Implementar `MainWindow(ctk.CTk)` con layout 900×650 px mínimo, dos columnas (300px izq / 600px der)
    - Columna izquierda: `AvatarWidget` + label de estado + botón "Escuchar"
    - Columna derecha: `ChatLogWidget`
    - Implementar `set_avatar_state(state)`: delega a `AvatarWidget.set_state()` y actualiza label con `STATE_LABELS`
    - Implementar `_poll_queue()`: consume todos los `GUIEvent` disponibles, reprograma `after(50, _poll_queue)`
    - Implementar `_on_listen_button()`: deshabilita botón, llama `on_listen_pressed` callback
    - Implementar `_on_close()`: llama `ResourceManager.shutdown()` con timeout 6s, luego `destroy()`
    - Aplicar paleta de colores de `theme.py` a todos los widgets
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 4.3, 4.4, 4.5, 8.2, 8.3_

  - [ ]* 5.2 Escribir property test para MainWindow — Property 5: Label sincronizado con Avatar_State
    - **Property 5: Label de estado sincronizado con Avatar_State**
    - **Validates: Requirements 4.3, 4.4**
    - Usar `hypothesis` con `st.sampled_from(list(AvatarState))`
    - Verificar que tras `set_avatar_state(s)`, el texto del label es exactamente `theme.STATE_LABELS[s.value]`
    - Archivo: `tests/gui/test_main_window.py`

  - [ ]* 5.3 Escribir property test para MainWindow — Property 6: Botón habilitado iff estado no es LISTENING/PROCESSING
    - **Property 6: Botón "Escuchar" habilitado iff estado no es LISTENING ni PROCESSING**
    - **Validates: Requirements 4.5**
    - Usar `hypothesis` con `st.sampled_from(list(AvatarState))`
    - Verificar que el botón está habilitado si y solo si `s not in {LISTENING, PROCESSING}`
    - Archivo: `tests/gui/test_main_window.py`

- [~] 6. Checkpoint — Verificar componentes GUI base
  - Asegurar que todos los tests de `tests/gui/` pasan. Preguntar al usuario si hay dudas sobre el diseño visual antes de continuar.

- [ ] 7. Implementar OfflineCommandHandler
  - [~] 7.1 Crear `src/offline/offline_command_handler.py` con clase `OfflineCommandHandler`
    - Crear `src/offline/__init__.py` vacío
    - Definir patrones compilados: `_HORA_PATTERN`, `_CHISTE_PATTERN`, `_APP_PATTERN`
    - Definir `_CHISTES: List[str]` con al menos 5 chistes en español
    - Definir `_APP_MAP: Dict[str, str]` con mapeo nombre→binario (calc.exe, notepad.exe, explorer.exe, mspaint.exe, chrome.exe)
    - Implementar `handle(text) -> Optional[str]`: envuelto en `try/except Exception`, retorna `str` no vacío o `None`
    - Implementar `_handle_hora()`: usa `datetime.now().strftime("%H:%M:%S")`
    - Implementar `_handle_chiste()`: usa `random.choice(_CHISTES)`
    - Implementar `_handle_app(app_key)`: verifica con `shutil.which()`, ejecuta con `subprocess.Popen()`, retorna confirmación o error descriptivo
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 7.2 Escribir property test para OfflineCommandHandler — Property 8: Completitud de respuestas
    - **Property 8: Completitud de respuestas del OfflineCommandHandler**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
    - Usar `hypothesis` con `st.one_of(hora_variants, chiste_variants, app_variants)`
    - Mockear `shutil.which()` y `subprocess.Popen()` para evitar ejecución real
    - Verificar que `handle(text)` retorna `str` con `len > 0`
    - Archivo: `tests/offline/test_offline_command_handler.py`

  - [ ]* 7.3 Escribir property test para OfflineCommandHandler — Property 9: None para entradas no reconocidas
    - **Property 9: OfflineCommandHandler retorna None para entradas no reconocidas**
    - **Validates: Requirements 7.5**
    - Usar `hypothesis` con `st.text(min_size=1).filter(lambda t: not any(p.search(t) for p in [...]))`
    - Verificar que `handle(text)` retorna exactamente `None`
    - Archivo: `tests/offline/test_offline_command_handler.py`

- [ ] 8. Implementar TTSEngine (pyttsx3)
  - [~] 8.1 Crear `src/offline/tts_local.py` con clase `TTSEngine`
    - Implementar `TTSEngine.__init__()`: inicializar `_stop_event = threading.Event()` y `_current_thread = None`
    - Implementar `speak(text, on_done)`: lanza hilo daemon que llama `pyttsx3.init()` internamente, ejecuta `engine.say(text)` + `engine.runAndWait()`, luego `root.after(0, on_done)` al terminar
    - Si `pyttsx3.init()` falla: loguear error y llamar `on_done()` igualmente para no dejar avatar en SPEAKING
    - Implementar `stop()`: señaliza `_stop_event` para detener el hilo activo
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 8.2 Escribir tests de ejemplo para TTSEngine
    - Mockear `pyttsx3.init()` para verificar que `on_done` se llama tras `speak()`
    - Verificar que si `pyttsx3.init()` lanza excepción, `on_done` se llama igualmente
    - Archivo: `tests/offline/test_tts_local.py`

- [ ] 9. Implementar STTEngine (Vosk)
  - [~] 9.1 Crear `src/offline/stt_local.py` con clase `STTEngine`
    - Implementar `STTEngine.__init__()` con parámetros: `model_path`, `audio_manager`, `wake_words`, `event_queue`, `fuzzy_threshold=0.70`
    - Implementar `start()`: lanza `_stt_loop` en hilo daemon
    - Implementar `stop()`: llama `_stop_event.set()`; el hilo termina en ≤ 5 s (timeout de `get_audio_chunk=1.0s`)
    - Implementar `_stt_loop()`: inicializa `vosk.Model(model_path)` y `KaldiRecognizer`; si modelo no existe, pone `GUIEvent(ERROR, msg)` en queue y retorna; loop: `get_audio_chunk(timeout=1.0)` → `AcceptWaveform()` → parse JSON → `event_queue.put_nowait(GUIEvent(TRANSCRIPTION, text))` → detectar wake words; manejar `queue.Full` descartando evento más antiguo
    - Implementar `_check_wake_word(text)`: coincidencia exacta primero, luego fuzzy con `SequenceMatcher` umbral 0.70 (reutilizar lógica de `WakeWordDetector._check_for_wake_word`)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 8.1, 8.4_

  - [ ]* 9.2 Escribir property test para STTEngine — Property 7: Detección de wake words fuzzy
    - **Property 7: Detección de wake words con coincidencia fuzzy**
    - **Validates: Requirements 5.5**
    - Usar `hypothesis` con `st.sampled_from(["asistente", "alexa", "hola asistente"])` y prefijos/sufijos aleatorios
    - Mockear `vosk.Model` y `AudioManager.get_audio_chunk()`
    - Verificar que `_check_wake_word(f"{prefix} {wake_word} {suffix}")` retorna el wake word
    - Archivo: `tests/offline/test_stt_local.py`

  - [ ]* 9.3 Escribir tests de ejemplo para STTEngine — error de modelo Vosk
    - Verificar que si el modelo no existe, se pone `GUIEvent(ERROR, ...)` en la queue
    - Verificar que `stop()` hace que el hilo termine en ≤ 5 s
    - Archivo: `tests/offline/test_stt_local.py`

- [~] 10. Checkpoint — Verificar componentes offline
  - Asegurar que todos los tests de `tests/offline/` pasan. Preguntar al usuario si hay dudas antes de continuar.

- [ ] 11. Implementar ResourceManager y punto de entrada
  - [~] 11.1 Implementar `ResourceManager` en `src/gui_main.py`
    - Definir clase `ResourceManager` con `shutdown()` idempotente (usar `threading.Event` para ignorar señales adicionales)
    - `shutdown()`: detiene `STTEngine.stop()` + `AudioManager.stop_continuous_capture()` (join timeout 5s) + `AudioManager.cleanup()` de forma atómica en `try/finally`; detiene `TTSEngine.stop()`; loguea "Recursos liberados correctamente"; llama `window.destroy()`
    - Usar bloques `try/finally` para garantizar liberación ante excepciones
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [~] 11.2 Implementar `VoiceAssistantGUI` y punto de entrada en `src/gui_main.py`
    - Implementar `VoiceAssistantGUI.__init__()`: instanciar `queue.Queue`, `AudioManager` (desde config.json), `STTEngine`, `TTSEngine`, `OfflineCommandHandler`, `ResourceManager`, `MainWindow`
    - Implementar `run()`: cargar `config.json` (sample_rate, chunk_size, channels, vosk_model_path, wake_words); registrar handlers SIGTERM/SIGINT; iniciar `AudioManager.start_continuous_capture()` + `STTEngine.start()`; llamar `window.mainloop()`
    - Implementar `handle_transcription(text)`: `ChatLog.add_user_message()` → Avatar PROCESSING → `command_handler.handle(text)` → si respuesta: `ChatLog.add_assistant_message()` + `TTS.speak()` → si None: mensaje "No entendí el comando."
    - Implementar `_on_tts_done()`: Avatar → IDLE
    - Conectar `_poll_queue` de `MainWindow` para despachar eventos: TRANSCRIPTION → `handle_transcription`, WAKE_WORD → Avatar LISTENING, ERROR → `ChatLog.add_error_message`, STATE_CHANGE → `set_avatar_state`
    - Bloque `if __name__ == "__main__"`: instanciar y llamar `VoiceAssistantGUI().run()`
    - _Requirements: 1.3, 1.5, 8.1, 8.2, 8.3, 8.4, 10.1, 10.2, 10.3, 10.4_

  - [ ]* 11.3 Escribir property test para ResourceManager — Property 10: Liveness de terminación del Audio Thread
    - **Property 10: Liveness de terminación del Audio Thread**
    - **Validates: Requirements 9.1**
    - Usar `hypothesis` con estados internos simulados del STTEngine (idle, procesando, detectando)
    - Mockear `AudioManager` y `STTEngine` para verificar que `shutdown()` completa en ≤ 5 s
    - Verificar idempotencia: llamar `shutdown()` dos veces no lanza excepciones
    - Archivo: `tests/test_resource_manager.py`

  - [ ]* 11.4 Escribir tests de ejemplo para cierre limpio
    - Verificar que SIGTERM/SIGINT disparan `ResourceManager.shutdown()`
    - Verificar que el log contiene "Recursos liberados correctamente" tras shutdown
    - Archivo: `tests/test_resource_manager.py`

- [~] 12. Checkpoint final — Integración completa
  - Ejecutar `python src/gui_main.py` para verificar que la ventana abre correctamente con Avatar en IDLE.
  - Asegurar que todos los tests pasan con `pytest tests/ -v`.
  - Preguntar al usuario si hay ajustes visuales o de comportamiento antes de cerrar la fase.

## Notes

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los tests de `AvatarWidget` y `ChatLogWidget` requieren un `tk.Tk()` root; usar `pytest-mock` para mockear `canvas.after()` y evitar el event loop real
- Los tests de `STTEngine` mockean `vosk.KaldiRecognizer` y `AudioManager.get_audio_chunk()`
- Los tests de `TTSEngine` mockean `pyttsx3.init()`
- Los tests de `OfflineCommandHandler` mockean `shutil.which()` y `subprocess.Popen()`
- `pyttsx3.init()` se llama dentro del hilo TTS (no en el constructor) para evitar conflictos con el event loop de tkinter en Windows
- El polling de la queue se hace cada 50 ms con `root.after(50, _poll_queue)` — suficientemente rápido sin saturar el event loop
- `vosk_model_path` por defecto: `"models/vosk-model-small-es-0.42"` — usar `scripts/download_vosk_model.py` si no existe

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["3.1", "4.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "4.2", "4.3"] },
    { "id": 4, "tasks": ["5.1", "7.1", "8.1", "9.1"] },
    { "id": 5, "tasks": ["5.2", "5.3", "7.2", "7.3", "8.2", "9.2", "9.3"] },
    { "id": 6, "tasks": ["11.1", "11.2"] },
    { "id": 7, "tasks": ["11.3", "11.4"] }
  ]
}
```
