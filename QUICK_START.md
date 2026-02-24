# 🚀 Quick Start - MVP Asistente de Voz

## ⚡ Inicio Rápido (3 pasos)

### 1. Configurar Credenciales

Edita `.env`:
```bash
AWS_ACCESS_KEY_ID=tu_access_key_aqui
AWS_SECRET_ACCESS_KEY=tu_secret_key_aqui
AWS_DEFAULT_REGION=us-east-1
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Ejecutar

```bash
python src/main.py
```

## 🎯 Cómo Usar

1. **Espera** a que el sistema diga "SISTEMA LISTO"
2. **Di** "Asistente" (la palabra de activación)
3. **Verás** el mensaje en VERDE confirmando detección
4. **Habla** tu comando (ej: "qué hora es")
5. **Lee** la transcripción en CYAN

## 🎨 Colores de la Interfaz

- 🟢 **VERDE** = Wake word detectado
- 🟡 **AMARILLO** = Procesando
- 🔵 **CYAN** = Transcripción final
- 🔴 **ROJO** = Error

## 🧪 Verificar Instalación

```bash
python test_mvp.py
```

Este script verifica:
- ✅ Módulos importados
- ✅ Credenciales AWS
- ✅ Dispositivos de audio
- ✅ Conexión a AWS

## 📋 Requisitos

- Python 3.9+
- Micrófono USB
- Conexión a Internet
- Cuenta AWS con acceso a Transcribe

## 💡 Tips

- Habla claro y fuerte
- Reduce ruido de fondo
- Espera 1-2 segundos después del wake word
- El sistema detecta silencio automáticamente

## 🐛 Problemas Comunes

**"Credenciales no configuradas"**
→ Edita `.env` con tus credenciales AWS

**"No se pudo capturar audio"**
→ Verifica que el micrófono esté conectado

**"No detecta wake word"**
→ Habla más fuerte o ajusta `confidence_threshold`

## 📚 Documentación Completa

Ver `MVP_INSTRUCTIONS.md` para documentación detallada.

## 💰 Costos AWS

- Tier gratuito: 60 min/mes (primeros 12 meses)
- Después: $0.024/minuto
- Estimado: ~$1.44/hora de uso continuo

---

**¡Listo para usar! 🎤**
