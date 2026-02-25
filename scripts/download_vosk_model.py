"""
Descarga el modelo Vosk en español (necesario para modo gratuito/local).

Uso:
  python scripts/download_vosk_model.py          # Modelo pequeño (~39 MB), más rápido, menos preciso
  python scripts/download_vosk_model.py --big    # Modelo grande (~1.4 GB), más preciso (recomendado si transcribe mal)
"""
import sys
import zipfile
import urllib.request
from pathlib import Path

MODELS = {
    "small": {
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip",
        "zip": "vosk-model-small-es-0.42.zip",
        "dir": "vosk-model-small-es-0.42",
        "desc": "pequeño (39 MB)",
    },
    "big": {
        "url": "https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip",
        "zip": "vosk-model-es-0.42.zip",
        "dir": "vosk-model-es-0.42",
        "desc": "grande (1.4 GB, más preciso)",
    },
}

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"


def main():
    use_big = "--big" in sys.argv
    key = "big" if use_big else "small"
    info = MODELS[key]
    zip_path = MODEL_DIR / info["zip"]
    extract_path = MODEL_DIR / info["dir"]

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if extract_path.exists() and (extract_path / "am").exists():
        print(f"El modelo {info['desc']} ya está en {extract_path}. Listo.")
        print(f'En config.json usa: "vosk_model_path": "model/{info["dir"]}"')
        return 0

    print(f"Descargando modelo Vosk español {info['desc']}...")
    try:
        req = urllib.request.Request(info["url"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            total_mb = total / (1024 * 1024)
            chunk_size = 256 * 1024  # 256 KB
            downloaded = 0
            with open(zip_path, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = 100 * downloaded / total
                        mb = downloaded / (1024 * 1024)
                        print(f"\r  {mb:.1f} MB / {total_mb:.1f} MB ({pct:.1f}%)", end="", flush=True)
                    else:
                        print(f"\r  {downloaded / (1024*1024):.1f} MB", end="", flush=True)
            print()
    except Exception as e:
        print(f"\nError descargando: {e}")
        print("Descarga manual:", info["url"])
        print("Descomprime el ZIP en la carpeta 'model' del proyecto.")
        if zip_path.exists():
            zip_path.unlink(missing_ok=True)
        return 1

    print("Descomprimiendo...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(MODEL_DIR)
    zip_path.unlink(missing_ok=True)
    print(f"Listo. Modelo en: {extract_path}")
    print(f'En config.json pon: "local": {{ "vosk_model_path": "model/{info["dir"]}" }}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
