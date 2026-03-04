"""
Comprueba que la base vectorial en Supabase esté creada y accesible.

Ejecutar desde la raíz del proyecto:
  python scripts/check_supabase_vector.py

Verifica:
  - Variables SUPABASE_URL y SUPABASE_SERVICE_KEY en .env
  - Conexión al proyecto
  - Tabla public.qa_cache existe y es accesible
  - Función match_qa_cache existe (RPC)
  - Extensión pgvector (indirectamente, al poder usar vector)
"""

import os
import sys

# Raíz del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def main():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()

    print("=" * 60)
    print("  Comprobación de Supabase (cache vectorial)")
    print("=" * 60)

    if not url:
        print("\n  No se encontró SUPABASE_URL en .env")
        print("  Añade: SUPABASE_URL=https://tu-proyecto.supabase.co")
        return 1
    if not key:
        print("\n  No se encontró SUPABASE_SERVICE_KEY en .env")
        print("  Añade la clave desde Supabase → Project Settings → API")
        return 1

    print(f"\n  URL: {url[:50]}...")
    print(f"  Key: {key[:20]}... (oculta)")

    try:
        from supabase import create_client
        client = create_client(url, key)
        print("\n  Conexión al proyecto: OK")
    except Exception as e:
        print(f"\n  Error conectando a Supabase: {e}")
        return 1

    # 1) Tabla qa_cache
    try:
        r = client.table("qa_cache").select("id", count="exact").limit(1).execute()
        count = getattr(r, "count", None) if hasattr(r, "count") else len(r.data or [])
        print(f"  Tabla 'qa_cache': OK (registros actuales: {count})")
    except Exception as e:
        print(f"  Tabla 'qa_cache': FALLO - {e}")
        print("  Crea la tabla con el SQL del paso 3 en docs/SUPABASE_VECTOR_SETUP.md")
        return 1

    # 2) Función RPC match_qa_cache (llamada con vector de 384 ceros)
    try:
        dummy_embedding = [0.0] * 384
        r = client.rpc("match_qa_cache", {
            "query_embedding": dummy_embedding,
            "match_count": 1,
            "max_distance": 1.0,
        }).execute()
        print("  Función 'match_qa_cache': OK")
    except Exception as e:
        print(f"  Función 'match_qa_cache': FALLO - {e}")
        print("  Crea la función con el SQL del paso 5 en docs/SUPABASE_VECTOR_SETUP.md")
        return 1

    print("\n  Todo listo. Puedes usar vector_cache_backend: 'supabase' en config.json")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
