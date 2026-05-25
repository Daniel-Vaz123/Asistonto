# Requirements Document

## Introduction

Esta feature migra la interfaz de terminal de "Asistonto" a una GUI moderna en modo oscuro con un avatar visual interactivo. La Fase 1 opera completamente offline: usa Vosk para reconocimiento de voz local, pyttsx3 para síntesis de voz local, y un manejador de comandos offline para responder a consultas de hora, chistes y apertura de aplicaciones del sistema. El ciclo de audio corre en hilos separados para no bloquear el main loop de la GUI, y se garantiza la liberación de recursos ante cualquier tipo de cierre.

## Glossary

- **GUI_App**: La aplicación de interfaz gráfica de usuario basada en CustomTkinter o PyQt6.
- **Avatar_Widget**: El componente visual que representa el estado del asistente mediante animaciones.
- **Avatar_State**: Uno de los cuatro estados posibles del avatar: IDLE, LISTENING, PROCESSING, SPEAKING.
- **Chat_Log**: El panel de texto tipo chat que registra el historial de interacciones usuario/asistente.
- **Audio_Thread**: El hilo de ejecución dedicado a la captura de audio y reconocimiento de voz (STT).
- **STT_Engine**: El motor de reconocimiento de voz offline basado en Vosk.
- **TTS_Engine**: El motor de síntesis de voz offline basado en pyttsx3.
- **Offline_Command_Handler**: El módulo que procesa comandos offline (hora, chistes, apps).
- **Wake_Word_Detector_Local**: El componente que detecta la palabra de activación usando Vosk sin AWS.
- **VoiceAssistantGUI**: El orquestador principal de la GUI que coordina todos los componentes.
- **Theme**: El módulo que define la paleta de colores modo oscuro y estilos visuales.
- **Resource_Manager**: El componente responsable de liberar recursos (hilos, PyAudio, streams) al cerrar.

## Requirements

### Requirement 1: Ventana Principal de la GUI

**User Story:** Como usuario, quiero una ventana de aplicación moderna en modo oscuro, para no necesitar ver la consola y tener una experiencia visual agradable.

#### Acceptance Criteria

1. THE GUI_App SHALL renderizar una ventana principal con paleta de colores en modo oscuro, bordes redondeados y estilo minimalista al iniciarse.
2. THE GUI_App SHALL mostrar el Avatar_Widget, el Chat_Log y los controles de interacción en la ventana principal de forma simultánea.
3. WHEN el usuario cierra la ventana mediante el botón X, THE GUI_App SHALL iniciar el proceso de cierre limpio de recursos antes de terminar, permitiendo el cierre de la ventana incluso si el proceso de cierre limpio no puede iniciarse correctamente.
4. THE GUI_App SHALL cargar el módulo Theme para aplicar la paleta de colores y estilos de forma consistente en todos los componentes visuales.
5. WHERE el sistema operativo soporte señales SIGTERM o SIGINT, THE GUI_App SHALL registrar handlers para esas señales que inicien el proceso de cierre limpio.

---

### Requirement 2: Avatar Visual con Estados

**User Story:** Como usuario, quiero ver un avatar animado que refleje el estado actual del asistente, para saber en todo momento si está escuchando, procesando o hablando.

#### Acceptance Criteria

1. THE Avatar_Widget SHALL mantener exactamente uno de los cuatro Avatar_State definidos (IDLE, LISTENING, PROCESSING, SPEAKING) en todo momento.
2. WHEN el Avatar_Widget recibe una solicitud de transición al Avatar_State en que ya se encuentra, THE Avatar_Widget SHALL omitir la transición sin ejecutar efectos secundarios ni reiniciar la animación.
3. WHEN el Avatar_State es IDLE, THE Avatar_Widget SHALL mostrar únicamente la animación suave de "respiración" (expansión y contracción periódica del orbe), desactivando cualquier otra animación activa.
4. WHEN el Avatar_State es LISTENING, THE Avatar_Widget SHALL mostrar únicamente la animación de pulso o expansión activa que indique escucha, desactivando cualquier otra animación activa.
5. WHEN el Avatar_State es PROCESSING, THE Avatar_Widget SHALL mostrar únicamente la animación de rotación o spinner que indique procesamiento, desactivando cualquier otra animación activa.
6. WHEN el Avatar_State es SPEAKING, THE Avatar_Widget SHALL mostrar únicamente la animación de ondas de audio o pulso rápido que indique habla, desactivando cualquier otra animación activa.
7. WHEN el VoiceAssistantGUI solicita un cambio de Avatar_State, THE Avatar_Widget SHALL completar la transición de animación en menos de 200 ms.

---

### Requirement 3: Log de Interacción (Chat Log)

**User Story:** Como usuario, quiero ver un historial de lo que dije y lo que respondió el asistente, para poder revisar la conversación en cualquier momento.

#### Acceptance Criteria

1. WHEN el usuario pronuncia un comando reconocido, THE Chat_Log SHALL agregar una entrada con el texto del usuario, un timestamp y diferenciación visual de "usuario" antes de mostrar la respuesta.
2. WHEN el asistente genera una respuesta, THE Chat_Log SHALL agregar una entrada con el texto de la respuesta, un timestamp y diferenciación visual de "asistente".
3. THE Chat_Log SHALL preservar todos los mensajes agregados durante la sesión sin pérdida de ninguna entrada.
4. WHEN se agrega un nuevo mensaje al Chat_Log, THE Chat_Log SHALL hacer scroll automático para mostrar el mensaje más reciente.
5. THE Chat_Log SHALL diferenciar visualmente las entradas de usuario y asistente mediante colores o alineación distintos.

---

### Requirement 4: Controles de Interacción

**User Story:** Como usuario, quiero un botón para forzar la escucha y un indicador de estado textual, para poder interactuar con el asistente sin necesidad de pronunciar la wake word.

#### Acceptance Criteria

1. THE GUI_App SHALL mostrar un botón de "Escuchar" que, al ser presionado, active el modo de escucha de comandos sin requerir la detección de wake word, independientemente de si la detección de wake word está habilitada en el sistema.
2. WHEN el usuario presiona el botón de "Escuchar", THE GUI_App SHALL transicionar el Avatar_State a LISTENING e iniciar la captura de comando.
3. THE GUI_App SHALL mostrar un indicador de estado textual que refleje el Avatar_State actual (por ejemplo: "En espera", "Escuchando...", "Procesando...", "Hablando...") en todo momento, incluso cuando el estado no haya cambiado desde el inicio.
4. WHEN el Avatar_State cambia, THE GUI_App SHALL actualizar el indicador de estado textual de forma sincronizada con el cambio de animación del Avatar_Widget.
5. WHILE el Avatar_State es LISTENING o PROCESSING, THE GUI_App SHALL deshabilitar el botón de "Escuchar" para evitar activaciones concurrentes.

---

### Requirement 5: Motor STT Offline (Vosk)

**User Story:** Como usuario, quiero que el asistente reconozca mi voz sin conexión a internet, para poder usarlo en entornos sin conectividad.

#### Acceptance Criteria

1. THE STT_Engine SHALL inicializar el modelo Vosk desde el sistema de archivos local sin realizar llamadas a servicios externos.
2. WHEN el Audio_Thread captura audio del micrófono, THE STT_Engine SHALL procesar los chunks de audio y producir transcripciones parciales y finales.
3. WHEN el STT_Engine produce una transcripción final no vacía, THE STT_Engine SHALL notificar al VoiceAssistantGUI mediante un callback thread-safe.
4. IF el modelo Vosk no se encuentra en la ruta configurada, THEN THE STT_Engine SHALL registrar un error descriptivo y notificar al VoiceAssistantGUI para mostrar un mensaje de error en el Chat_Log.
5. THE STT_Engine SHALL detectar las wake words configuradas ("asistente", "alexa", "hola asistente") en el flujo de transcripción continua usando coincidencia exacta o aproximada.
6. IF el Audio_Thread no puede producir ninguna transcripción a partir del audio capturado, THEN THE STT_Engine SHALL notificar al VoiceAssistantGUI con un mensaje de error descriptivo mediante un callback thread-safe.

---

### Requirement 6: Motor TTS Offline (pyttsx3)

**User Story:** Como usuario, quiero que el asistente me responda con voz sin conexión a internet, para no depender de AWS Polly en la Fase 1.

#### Acceptance Criteria

1. THE TTS_Engine SHALL inicializar pyttsx3 con el motor de voz disponible en el sistema operativo sin realizar llamadas a servicios externos.
2. WHEN el VoiceAssistantGUI solicita síntesis de texto, THE TTS_Engine SHALL convertir el texto a audio y reproducirlo en el dispositivo de salida configurado.
3. WHILE el TTS_Engine está reproduciendo audio, THE VoiceAssistantGUI SHALL mantener el Avatar_State en SPEAKING, independientemente del mecanismo de reproducción utilizado.
4. WHEN el TTS_Engine termina la reproducción de audio, THE TTS_Engine SHALL notificar al VoiceAssistantGUI mediante un callback thread-safe para que transite el Avatar_State a IDLE.
5. IF el TTS_Engine no puede inicializar el motor de voz, THEN THE TTS_Engine SHALL registrar un error descriptivo y el VoiceAssistantGUI SHALL mostrar la respuesta únicamente en el Chat_Log sin reproducción de audio.

---

### Requirement 7: Manejador de Comandos Offline

**User Story:** Como usuario, quiero que el asistente responda a comandos básicos sin internet, para poder consultar la hora, escuchar un chiste o abrir aplicaciones del sistema.

#### Acceptance Criteria

1. WHEN el Offline_Command_Handler recibe un texto que coincide con los patrones de consulta de hora ("qué hora es", "dime la hora"), THE Offline_Command_Handler SHALL retornar una cadena no vacía con la hora actual del sistema obtenida mediante `datetime`.
2. WHEN el Offline_Command_Handler recibe un texto que coincide con los patrones de chiste ("cuéntame un chiste", "dime un chiste"), THE Offline_Command_Handler SHALL retornar una cadena no vacía seleccionada aleatoriamente de una lista estática local de al menos 5 chistes.
3. WHEN el Offline_Command_Handler recibe un texto que coincide con los patrones de apertura de aplicación ("abre la calculadora", "abre el bloc de notas"), THE Offline_Command_Handler SHALL verificar la existencia del binario nativo antes de intentar ejecutarlo, ejecutarlo mediante `subprocess` o `os` si existe, y retornar una cadena de confirmación no vacía.
4. THE Offline_Command_Handler SHALL retornar una respuesta no vacía para cualquier texto de entrada que coincida con un patrón de comando válido reconocido.
5. IF el Offline_Command_Handler recibe un texto que no coincide con ningún patrón de comando offline, THEN THE Offline_Command_Handler SHALL retornar `None` para indicar que el comando no es manejable offline.
6. IF el Offline_Command_Handler intenta abrir una aplicación y el binario no se encuentra en el sistema, THEN THE Offline_Command_Handler SHALL retornar una cadena de error descriptiva no vacía en lugar de lanzar una excepción.

---

### Requirement 8: Arquitectura de Concurrencia

**User Story:** Como desarrollador, quiero que el ciclo de audio no bloquee el main loop de la GUI, para que la interfaz permanezca responsiva durante la captura y el procesamiento de voz.

#### Acceptance Criteria

1. THE Audio_Thread SHALL ejecutarse en un hilo separado del main loop de la GUI_App durante toda la sesión.
2. WHEN el Audio_Thread produce un resultado de transcripción o un cambio de estado, THE Audio_Thread SHALL comunicarlo al main loop de la GUI_App mediante un mecanismo thread-safe (señales Qt o `queue.Queue` con `tkinter.after`).
3. THE GUI_App SHALL procesar las actualizaciones de estado provenientes del Audio_Thread sin bloquear el renderizado de la interfaz.
4. WHEN el VoiceAssistantGUI solicita iniciar la captura de audio, THE Audio_Thread SHALL comenzar a capturar dentro de los 500 ms siguientes a la solicitud; si no puede cumplir ese plazo, SHALL continuar el intento de captura sin cancelar la operación.

---

### Requirement 9: Cierre Limpio y Liberación de Recursos

**User Story:** Como desarrollador, quiero que todos los recursos se liberen correctamente ante cualquier tipo de cierre, para evitar fugas de memoria, hilos huérfanos o bloqueos del micrófono.

#### Acceptance Criteria

1. WHEN el Resource_Manager recibe la primera señal de cierre (botón X, SIGTERM, SIGINT o excepción no capturada), THE Resource_Manager SHALL detener el Audio_Thread en un plazo máximo de 5 segundos contados desde esa primera señal, ignorando señales de cierre adicionales que lleguen durante ese período.
2. WHEN el Resource_Manager detiene el Audio_Thread, THE Resource_Manager SHALL liberar el stream de PyAudio y cerrar el micrófono de forma atómica, de modo que ambas operaciones tengan éxito juntas antes de continuar con el cierre.
3. WHEN el Resource_Manager recibe una señal de cierre, THE Resource_Manager SHALL detener el TTS_Engine y liberar el motor de pyttsx3.
4. THE Resource_Manager SHALL usar bloques `try/finally` o context managers para garantizar la liberación de recursos incluso ante excepciones no capturadas.
5. WHEN el proceso termina, THE Resource_Manager SHALL registrar en el log que todos los recursos fueron liberados correctamente.

---

### Requirement 10: Punto de Entrada de la GUI

**User Story:** Como usuario, quiero ejecutar la GUI con un único comando, para no tener que configurar nada manualmente para la Fase 1.

#### Acceptance Criteria

1. THE GUI_App SHALL inicializarse completamente —incluyendo config, AudioManager, Audio_Thread y Avatar_State en IDLE— al ejecutar `python src/gui_main.py` sin requerir argumentos de línea de comandos.
2. WHEN la GUI_App se inicializa, THE GUI_App SHALL verificar que el modelo Vosk esté disponible localmente y mostrar un mensaje de error en el Chat_Log si no lo está.
3. WHEN la GUI_App se inicializa, THE GUI_App SHALL iniciar el Audio_Thread automáticamente y transicionar el Avatar_State a IDLE.
4. THE GUI_App SHALL cargar la configuración de audio desde `config.json` (sample_rate, chunk_size, channels) para inicializar el AudioManager existente.
