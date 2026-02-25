"""
Descarga el modelo de Vosk en español (pequeño, ~45 MB).
Ejecutar una vez desde la carpeta Asistonto: python scripts/download_vosk_model.py
"""

import os
import sys
import zipfile
import urllib.request

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
MODEL_DIR = "model"
MODEL_NAME = "vosk-model-small-es-0.42"


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base)
    path = os.path.join(MODEL_DIR, MODEL_NAME)
    if os.path.isdir(path):
        print(f"El modelo ya existe en {path}. No se descarga nada.")
        return 0
    os.makedirs(MODEL_DIR, exist_ok=True)
    zip_path = os.path.join(MODEL_DIR, f"{MODEL_NAME}.zip")
    print(f"Descargando modelo español (small) desde {MODEL_URL} ...")
    try:
        urllib.request.urlretrieve(MODEL_URL, zip_path)
    except Exception as e:
        print(f"Error descargando: {e}")
        print("Descarga manual: ", MODEL_URL)
        print("Descomprime el ZIP dentro de la carpeta model/")
        return 1
    print("Descomprimiendo...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(MODEL_DIR)
    os.remove(zip_path)
    print(f"Listo. Modelo en {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
