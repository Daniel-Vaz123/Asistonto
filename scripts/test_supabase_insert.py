"""
Prueba de inserción en Supabase qa_cache.
Ejecutar desde la raíz del proyecto:  python scripts/test_supabase_insert.py

Muestra el error exacto si la conexión o el INSERT fallan.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

def main():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    if not url or not key:
        print("Falta SUPABASE_URL o SUPABASE_SERVICE_KEY en .env")
        return 1

    print("Conectando a Supabase...")
    try:
        from supabase import create_client
        client = create_client(url, key)
    except Exception as e:
        print("Error al conectar (¿pip install supabase?):", e)
        return 1

    print("Generando embedding de prueba...")
    try:
        from src.vector_store import embed_text
        embedding = embed_text("prueba de conexión")
        print(f"  Embedding: {len(embedding)} dimensiones")
    except Exception as e:
        print("Error al generar embedding (¿sentence-transformers?):", e)
        return 1

    # Probar INSERT: primero como lista
    payload = {
        "query_text": "prueba de conexión",
        "response_text": "Si ves esto en la tabla, el INSERT funcionó.",
        "embedding": embedding,
    }
    print("Insertando fila en qa_cache (embedding como lista)...")
    try:
        r = client.table("qa_cache").insert(payload).execute()
        print("  OK. Filas insertadas:", len(r.data) if r.data else 1)
        return 0
    except Exception as e:
        print("  Error con lista:", e)
        # Probar como string (formato pgvector)
        embedding_str = "[" + ",".join(str(round(x, 6)) for x in embedding) + "]"
        payload["embedding"] = embedding_str
        print("Intentando con embedding como string...")
        try:
            r = client.table("qa_cache").insert(payload).execute()
            print("  OK con string. Filas insertadas:", len(r.data) if r.data else 1)
            return 0
        except Exception as e2:
            print("  Error con string:", e2)
            return 1

if __name__ == "__main__":
    sys.exit(main())
