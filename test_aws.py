import boto3
import os
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

print("⏳ Probando conexión con AWS...")

try:
    # Usamos el servicio STS de Amazon para verificar nuestra identidad
    sts_client = boto3.client(
        'sts',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION')
    )
    
    identidad = sts_client.get_caller_identity()
    
    print("\n✅ ¡CONEXIÓN EXITOSA!")
    print(f"👤 Tu ID de cuenta es: {identidad['Account']}")
    print("☁️  Tus llaves tienen acceso a la nube de Amazon y están listas para usarse.")

except Exception as e:
    print("\n❌ ERROR DE CONEXIÓN")
    print("Hubo un problema con tus llaves. Asegúrate de haberlas copiado bien y sin espacios extra.")
    print(f"Detalle del error: {e}")