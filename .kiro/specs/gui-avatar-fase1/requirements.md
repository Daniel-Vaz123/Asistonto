# Requirements Document

## Introduction

Esta feature reemplaza la interfaz de terminal de Asistonto por una GUI moderna con un avatar visual interactivo. La Fase 1 opera completamente offline: sin AWS, sin APIs externas, sin búsqueda web. El objetivo es demostrar la arquitectura GUI + audio concurrente con tres comandos funcionales (hora, chiste, calculadora), sentando las bases para fases posteriores que reintegrarán los servicios cloud.

El sistema mantiene el `AudioManager` y el modelo Vosk existentes, añadiendo una capa de presentación desacoplada mediante threading para garantizar que el ciclo de captura de audio nunca bloquee el main loop de la GUI.

## Glosario

- **GUI_App**: La aplicación de interfaz gráfica de usuario basada en CustomTkinter o PyQt6/PySide6.
- **Avatar_Widget**: El componente visual que representa al asistente con animaciones de estado.
- **Avatar_State**: Uno de los cuatro estados posibles del avatar: `Idle`, `Listening`, `Processing`, `Speaking`.
- **Worker_Thread**: El hilo secundario (QThread o threading.Thread) que ejecuta el ciclo de captura de audio y STT sin bloquear el GUI loop.
- **Offline_Command_Handler**: El módulo que clasifica y ejecuta los tres comandos offline soportados en Fase 1.
- **Local_STT**: El wrapper sobre Vosk que realiza reconocimiento de voz offline.
- **Local_TTS**: El wrapper sobre pyttsx3 que realiza síntesis de voz offline.
- **Chat_Panel**: El panel de log de interacción que muestra el historial de mensajes del usuario y del asistente.
- **State_Indicator**: El componente textual que muestra el estado actual del asistente en la GUI.
- **Wake_Word**: La palabra o frase de activación que inicia el ciclo de escucha (ej. "asistente").
- **Inline_Command**: Texto pronunciado inmediatamente después del wake word en la misma frase.
- **GUI_Loop**: El ciclo principal de eventos de la biblioteca de GUI (CustomTkinter mainloop o Qt event loop).
- **Audio_Buffer**: El buffer circular del `AudioManager` existente que almacena chunks de audio PCM.
- **Confidence_Score**: Valor numérico entre 0.0 y 1.0 que indica la certeza del reconocimiento de voz.

---

## Requirements

### Requirement 1: Ventana Principal de la GUI

**User Story:** Como usuario, quiero una ventana de aplicación moderna con modo oscuro y estilo minimalista, para que la interacción con el asistente sea visualmente agradable y no distraiga.

#### Criterios de Aceptación

1. THE `GUI_App` SHALL inicializar una ventana principal con un título visible que identifique al asistente.
2. THE `GUI_App` SHALL aplicar un tema oscuro como configuración predeterminada al arrancar.
3. THE `GUI_App` SHALL establecer un tamaño mínimo de ventana de 600×400 píxeles para garantizar la legibilidad de todos los componentes.
4. THE `GUI_App` SHALL renderizar bordes redondeados y una paleta de colores con fondo oscuro (valor hexadecimal entre `#0D0D0D` y `#2B2B2B`) y acentos en tonos neón o pastel.
5. WHEN el usuario cierra la ventana principal, THE `GUI_App` SHALL detener el `Worker_Thread` y liberar todos los recursos de audio antes de terminar el proceso.
6. IF el `Worker_Thread` no termina en un plazo de 3 segundos tras la señal de cierre, THEN THE `GUI_App` SHALL forzar la terminación del hilo y registrar el evento en el log.

---

### Requirement 2: Avatar con Máquina de Estados Visual

**User Story:** Como usuario, quiero ver un avatar animado que refleje el estado actual del asistente (inactivo, escuchando, procesando, hablando), para entender en todo momento qué está haciendo el sistema.

#### Criterios de Aceptación

1. THE `Avatar_Widget` SHALL soportar exactamente cuatro estados: `Idle`, `Listening`, `Processing` y `Speaking`.
2. WHEN el `Avatar_Widget` recibe una solicitud de transición a un `Avatar_State` válido, THE `Avatar_Widget` SHALL actualizar su representación visual en un plazo máximo de 100 ms.
3. IF el `Avatar_Widget` recibe una solicitud de transición a un estado no definido en el conjunto `{Idle, Listening, Processing, Speaking}`, THEN THE `Avatar_Widget` SHALL ignorar la solicitud y registrar una advertencia en el log sin alterar el estado actual.
4. THE `Avatar_Widget` SHALL representar el estado `Idle` con una animación de respiración suave (variación periódica de opacidad o escala).
5. THE `Avatar_Widget` SHALL representar el estado `Listening` con un indicador visual de onda de audio activa (ej. círculos concéntricos pulsantes o barras de nivel).
6. THE `Avatar_Widget` SHALL representar el estado `Processing` con una animación de carga giratoria o pulsante.
7. THE `Avatar_Widget` SHALL representar el estado `Speaking` con una animación sincronizada con la reproducción de TTS (ej. movimiento de boca o pulso de color).
8. WHILE el `Avatar_Widget` se encuentra en cualquier `Avatar_State`, THE `State_Indicator` SHALL mostrar el nombre del estado actual en texto legible.
9. FOR ALL secuencias válidas de transiciones de estado, THE `Avatar_Widget` SHALL terminar en un `Avatar_State` perteneciente al conjunto `{Idle, Listening, Processing, Speaking}` (invariante de estados válidos).

---

### Requirement 3: Concurrencia — Worker Thread de Audio

**User Story:** Como desarrollador, quiero que el ciclo de captura de audio y el reconocimiento de voz corran en un hilo separado, para que la GUI nunca se congele durante operaciones de audio.

#### Criterios de Aceptación

1. THE `Worker_Thread` SHALL ejecutar el ciclo de captura de audio del `AudioManager` en un hilo separado del `GUI_Loop`.
2. WHEN el `Worker_Thread` inicia, THE `Worker_Thread` SHALL invocar `AudioManager.start_continuous_capture()` sin bloquear el hilo principal de la `GUI_App`.
3. WHILE el `Worker_Thread` está ejecutando operaciones de captura o STT, THE `GUI_Loop` SHALL permanecer responsivo y procesar eventos de UI en un plazo máximo de 100 ms.
4. THE `Worker_Thread` SHALL comunicar resultados al `GUI_Loop` exclusivamente mediante mecanismos thread-safe (señales Qt, `queue.Queue`, o callbacks registrados en el hilo principal).
5. WHEN el `Worker_Thread` detecta un wake word o completa una transcripción, THE `Worker_Thread` SHALL emitir un evento al `GUI_Loop` con el texto transcrito y el `Confidence_Score` asociado.
6. IF el `Worker_Thread` encuentra una excepción no recuperable durante la captura de audio, THEN THE `Worker_Thread` SHALL emitir un evento de error al `GUI_Loop` y transicionar el `Avatar_Widget` al estado `Idle`.
7. FOR ALL duraciones de operación de audio simuladas entre 0 ms y 5000 ms, THE `GUI_Loop` SHALL procesar al menos un evento de UI por cada 100 ms de operación de audio (propiedad de no-bloqueo).

---

### Requirement 4: Reconocimiento de Voz Offline (Local STT)

**User Story:** Como usuario, quiero que el asistente entienda mis comandos de voz sin conexión a internet, para poder usarlo en cualquier entorno.

#### Criterios de Aceptación

1. THE `Local_STT` SHALL utilizar el modelo Vosk existente en el proyecto para transcribir audio PCM a texto en español.
2. WHEN `Local_STT` recibe un chunk de audio PCM de 16 bits mono a 16000 Hz, THE `Local_STT` SHALL retornar un resultado de transcripción parcial o final dentro de 500 ms.
3. IF `Local_STT` recibe audio con nivel RMS inferior al umbral de ruido calibrado por el `AudioManager`, THEN THE `Local_STT` SHALL retornar una cadena vacía o `None` sin lanzar excepción.
4. WHEN `Local_STT` produce una transcripción final, THE `Local_STT` SHALL incluir un `Confidence_Score` entre 0.0 y 1.0.
5. THE `Local_STT` SHALL exponer una interfaz compatible con el `Worker_Thread` mediante un método `transcribe(audio_chunk: bytes) -> TranscriptionResult`.
6. IF el modelo Vosk no está disponible en la ruta configurada al inicializar `Local_STT`, THEN THE `Local_STT` SHALL lanzar una excepción `ModelNotFoundError` con un mensaje descriptivo de la ruta esperada.

---

### Requirement 5: Síntesis de Voz Offline (Local TTS)

**User Story:** Como usuario, quiero que el asistente me responda con voz sin necesidad de internet, para mantener la experiencia conversacional en modo offline.

#### Criterios de Aceptación

1. THE `Local_TTS` SHALL utilizar `pyttsx3` para sintetizar texto en español a audio reproducible.
2. WHEN `Local_TTS` recibe un texto no vacío, THE `Local_TTS` SHALL iniciar la reproducción de audio en el dispositivo de salida configurado.
3. WHEN `Local_TTS` inicia la reproducción, THE `Local_TTS` SHALL notificar al `Avatar_Widget` para transicionar al estado `Speaking`.
4. WHEN `Local_TTS` completa la reproducción, THE `Local_TTS` SHALL notificar al `Avatar_Widget` para transicionar al estado `Idle`.
5. IF `Local_TTS` recibe una cadena vacía o `None`, THEN THE `Local_TTS` SHALL ignorar la solicitud sin lanzar excepción y registrar una advertencia en el log.
6. THE `Local_TTS` SHALL ejecutar la síntesis y reproducción en el `Worker_Thread` para no bloquear el `GUI_Loop`.
7. WHERE la voz configurada en `pyttsx3` no esté disponible en el sistema, THE `Local_TTS` SHALL seleccionar la primera voz disponible en español o, si no existe ninguna en español, la primera voz disponible en el sistema.

---

### Requirement 6: Manejador de Comandos Offline

**User Story:** Como usuario, quiero que el asistente responda a tres comandos básicos sin internet (hora, chiste, calculadora), para tener funcionalidad útil en modo offline.

#### Criterios de Aceptación

1. THE `Offline_Command_Handler` SHALL clasificar el texto transcrito en una de las siguientes intenciones: `TIME_QUERY`, `JOKE_REQUEST`, `CALCULATOR_LAUNCH`, o `UNKNOWN`.
2. WHEN `Offline_Command_Handler` recibe texto que contiene variantes de "qué hora es" (ej. "dime la hora", "hora actual", "qué hora tienes"), THE `Offline_Command_Handler` SHALL clasificar la intención como `TIME_QUERY`.
3. WHEN `Offline_Command_Handler` recibe una intención `TIME_QUERY`, THE `Offline_Command_Handler` SHALL retornar una cadena con la hora actual del sistema en formato "Son las HH:MM" obtenida mediante `datetime.now()`.
4. WHEN `Offline_Command_Handler` recibe texto que contiene variantes de "cuéntame un chiste" (ej. "dime un chiste", "cuéntame algo gracioso"), THE `Offline_Command_Handler` SHALL clasificar la intención como `JOKE_REQUEST`.
5. WHEN `Offline_Command_Handler` recibe una intención `JOKE_REQUEST`, THE `Offline_Command_Handler` SHALL retornar un elemento seleccionado aleatoriamente de una lista local de al menos 10 chistes predefinidos.
6. WHEN `Offline_Command_Handler` recibe texto que contiene variantes de "abre la calculadora" (ej. "calculadora", "abre calculadora", "inicia la calculadora"), THE `Offline_Command_Handler` SHALL clasificar la intención como `CALCULATOR_LAUNCH`.
7. WHEN `Offline_Command_Handler` recibe una intención `CALCULATOR_LAUNCH`, THE `Offline_Command_Handler` SHALL ejecutar el proceso del sistema correspondiente a la calculadora nativa (`calc.exe` en Windows, `gnome-calculator` o `kcalc` en Linux, `Calculator` en macOS).
8. IF `Offline_Command_Handler` no puede clasificar el texto en ninguna intención conocida, THEN THE `Offline_Command_Handler` SHALL retornar la intención `UNKNOWN` con una respuesta de fallback predefinida (ej. "Lo siento, ese comando no está disponible en modo offline").
9. FOR ALL textos de entrada no vacíos, THE `Offline_Command_Handler` SHALL retornar exactamente una intención del conjunto `{TIME_QUERY, JOKE_REQUEST, CALCULATOR_LAUNCH, UNKNOWN}` (propiedad de completitud de clasificación).
10. FOR ALL textos semánticamente equivalentes a un comando conocido (variantes de frase), THE `Offline_Command_Handler` SHALL clasificar todos en la misma intención (propiedad de consistencia semántica).
11. FOR ALL invocaciones de `JOKE_REQUEST`, el resultado retornado SHALL ser un elemento perteneciente a la lista local de chistes predefinidos (invariante de pertenencia al conjunto).

---

### Requirement 7: Panel de Log de Interacción (Chat Panel)

**User Story:** Como usuario, quiero ver un historial de la conversación en pantalla, para revisar lo que dije y lo que respondió el asistente.

#### Criterios de Aceptación

1. THE `Chat_Panel` SHALL mostrar los mensajes del usuario con una etiqueta visual diferenciada (ej. "Tú:") y los mensajes del asistente con otra etiqueta (ej. "Asistonto:").
2. WHEN el `Worker_Thread` completa una transcripción final, THE `Chat_Panel` SHALL agregar una entrada de usuario con el texto transcrito.
3. WHEN el `Offline_Command_Handler` produce una respuesta, THE `Chat_Panel` SHALL agregar una entrada del asistente con el texto de la respuesta.
4. THE `Chat_Panel` SHALL hacer scroll automático hacia el mensaje más reciente cada vez que se agrega una nueva entrada.
5. THE `Chat_Panel` SHALL mantener un historial de al menos 100 entradas sin degradación de rendimiento visible.
6. IF el `Chat_Panel` supera las 200 entradas, THEN THE `Chat_Panel` SHALL eliminar las entradas más antiguas para mantener el historial en un máximo de 200 entradas.
7. FOR ALL secuencias de N mensajes agregados al `Chat_Panel` (donde N ≤ 200), THE `Chat_Panel` SHALL contener exactamente N entradas con el contenido y el autor correctos (propiedad de integridad del historial).
8. WHEN se agrega una entrada al `Chat_Panel`, THE `Chat_Panel` SHALL incluir una marca de tiempo en formato "HH:MM:SS" junto a cada mensaje.

---

### Requirement 8: Botón de Escucha Forzada

**User Story:** Como usuario, quiero un botón en la GUI que active el modo de escucha sin necesidad de pronunciar el wake word, para situaciones donde el reconocimiento de wake word falla o prefiero activar manualmente.

#### Criterios de Aceptación

1. THE `GUI_App` SHALL mostrar un botón de escucha forzada visible y accesible en la ventana principal.
2. WHEN el usuario hace clic en el botón de escucha forzada, THE `GUI_App` SHALL transicionar el `Avatar_Widget` al estado `Listening` e iniciar el ciclo de captura de comando en el `Worker_Thread`.
3. WHILE el `Avatar_Widget` se encuentra en el estado `Listening` por activación del botón, THE `GUI_App` SHALL deshabilitar el botón de escucha forzada para evitar activaciones concurrentes.
4. WHEN el ciclo de captura de comando finaliza (por silencio o timeout), THE `GUI_App` SHALL rehabilitar el botón de escucha forzada.
5. IF el `Worker_Thread` ya está procesando un comando cuando el usuario hace clic en el botón, THEN THE `GUI_App` SHALL ignorar el clic y mostrar el estado actual en el `State_Indicator` sin iniciar un nuevo ciclo.

---

### Requirement 9: Detección de Wake Word Offline

**User Story:** Como usuario, quiero activar el asistente pronunciando una palabra clave sin tocar el teclado, para una experiencia de uso manos libres.

#### Criterios de Aceptación

1. THE `Worker_Thread` SHALL monitorear continuamente el `Audio_Buffer` en busca del wake word configurado usando `Local_STT`.
2. WHEN `Local_STT` detecta el wake word con un `Confidence_Score` mayor o igual a 0.7, THE `Worker_Thread` SHALL emitir un evento de wake word detectado al `GUI_Loop`.
3. WHEN el `GUI_Loop` recibe el evento de wake word detectado, THE `GUI_App` SHALL transicionar el `Avatar_Widget` al estado `Listening`.
4. WHEN el wake word es detectado con un `Inline_Command` (texto adicional en la misma frase), THE `Worker_Thread` SHALL procesar el `Inline_Command` directamente sin esperar una segunda frase.
5. IF el `Worker_Thread` detecta el wake word mientras el `Avatar_Widget` se encuentra en el estado `Speaking`, THEN THE `Worker_Thread` SHALL ignorar la detección para evitar que el asistente se active con su propia voz.
6. THE `Worker_Thread` SHALL aplicar una ventana de supresión de 3 segundos tras cada detección de wake word para evitar activaciones repetidas por el mismo evento de audio.

---

### Requirement 10: Punto de Entrada y Orquestación

**User Story:** Como desarrollador, quiero un punto de entrada dedicado para la GUI que inicialice todos los componentes en el orden correcto, para poder ejecutar la Fase 1 de forma independiente sin afectar el `main.py` existente.

#### Criterios de Aceptación

1. THE `GUI_App` SHALL ser iniciada desde `gui_main.py` como punto de entrada independiente, sin modificar ni importar `main.py`.
2. WHEN `gui_main.py` es ejecutado, THE `GUI_App` SHALL inicializar los componentes en el siguiente orden: `AudioManager` → `Local_STT` → `Local_TTS` → `Offline_Command_Handler` → `Worker_Thread` → `GUI_Loop`.
3. IF algún componente falla durante la inicialización, THEN THE `GUI_App` SHALL mostrar un mensaje de error descriptivo en la ventana principal y permitir al usuario cerrar la aplicación de forma limpia.
4. THE `GUI_App` SHALL cargar la configuración de audio desde `config.json` (parámetros `sample_rate`, `chunk_size`, `channels`) para mantener consistencia con el sistema existente.
5. THE `GUI_App` SHALL registrar todos los eventos de inicialización, errores y transiciones de estado en el archivo de log existente (`logs/voice_assistant.log`).

---

### Requirement 11: Restricciones de Alcance (Fase 1)

**User Story:** Como arquitecto del sistema, quiero que la Fase 1 opere estrictamente offline, para garantizar que la arquitectura GUI sea validada de forma independiente antes de reintegrar servicios cloud.

#### Criterios de Aceptación

1. THE `GUI_App` SHALL operar sin realizar ninguna llamada de red a servicios externos durante la Fase 1.
2. IF cualquier módulo de la Fase 1 intenta importar o instanciar `TranscribeStreamingClientWrapper`, `ResponseGenerator` (con Polly), `CommandProcessor`, o cualquier cliente de AWS, THEN THE `GUI_App` SHALL lanzar una excepción `Phase1ViolationError` en tiempo de inicialización.
3. THE `Offline_Command_Handler` SHALL limitarse a los tres comandos definidos: `TIME_QUERY`, `JOKE_REQUEST`, y `CALCULATOR_LAUNCH`, sin invocar `IntentClassifier`, `ActionRouter`, ni `CommandProcessor` del sistema existente.
4. THE `Local_STT` SHALL utilizar exclusivamente el modelo Vosk local, sin invocar `TranscribeStreamingClientWrapper` ni ningún servicio de transcripción en la nube.
5. THE `Local_TTS` SHALL utilizar exclusivamente `pyttsx3`, sin invocar `ResponseGenerator` ni Amazon Polly.
