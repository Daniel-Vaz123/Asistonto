"""
Notes DB - Guardado y búsqueda de notas del usuario en Supabase

Las notas se guardan y leen solo en la tabla user_notes (no en archivos locales).
Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env y la tabla user_notes creada.
"""

import logging
import os
from typing import List

logger = logging.getLogger(__name__)

TABLE_NOTES = "user_notes"
_supabase_client = None


def _get_client():
    """Cliente Supabase desde variables de entorno (lazy)."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_KEY") or "").strip()
    if not url or not key:
        return None
    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
        logger.info("Notes DB: cliente Supabase conectado")
        return _supabase_client
    except Exception as e:
        logger.warning("Notes DB: no se pudo conectar a Supabase: %s", e)
        return None


def save_note(content: str, source: str = "voice") -> bool:
    """
    Guarda una nota en Supabase (tabla user_notes).

    Args:
        content: Texto de la nota.
        source: Origen (ej. "voice", "app").

    Returns:
        True si se guardó correctamente, False en caso contrario.
    """
    if not content or not content.strip():
        return False
    client = _get_client()
    if not client:
        return False
    try:
        client.table(TABLE_NOTES).insert({
            "content": content.strip()[:10000],
            "source": source,
        }).execute()
        logger.info("Nota guardada en Supabase (user_notes)")
        return True
    except Exception as e:
        logger.warning("Notes DB: error al guardar: %s", e)
        return False


def search_notes(query: str, limit: int = 5) -> List[dict]:
    """
    Busca notas en Supabase cuyo contenido contenga el texto (case-insensitive).

    Args:
        query: Término de búsqueda.
        limit: Número máximo de notas a devolver.

    Returns:
        Lista de dicts con keys: id, content, created_at, source.
    """
    if not query or not query.strip():
        return []
    client = _get_client()
    if not client:
        return []
    try:
        term = f"%{query.strip()}%"
        r = (
            client.table(TABLE_NOTES)
            .select("id, content, created_at, source")
            .ilike("content", term)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(r.data) if r.data else []
    except Exception as e:
        logger.warning("Notes DB: error al buscar: %s", e)
        return []


def get_recent_notes(limit: int = 10) -> List[dict]:
    """
    Obtiene las notas más recientes.

    Returns:
        Lista de dicts con keys: id, content, created_at, source.
    """
    client = _get_client()
    if not client:
        return []
    try:
        r = (
            client.table(TABLE_NOTES)
            .select("id, content, created_at, source")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(r.data) if r.data else []
    except Exception as e:
        logger.warning("Notes DB: error al listar: %s", e)
        return []


def is_available() -> bool:
    """Indica si Supabase está configurado y la tabla existe."""
    return _get_client() is not None
