"""
Vector Store - Base de datos vectorial para cache de Q&A y búsqueda semántica

Reduce llamadas a DeepSeek almacenando preguntas/respuestas en un índice vectorial.
Antes de llamar a la API se busca una pregunta similar; si la similitud es alta
se devuelve la respuesta cacheada (ahorro de créditos).

Backends:
- chroma: almacenamiento local en disco (data/chroma_db).
- supabase: almacenamiento en Supabase (PostgreSQL + pgvector). Ver docs/SUPABASE_VECTOR_SETUP.md.
"""

import logging
import os
from pathlib import Path
from typing import Optional, List, Tuple, Any

logger = logging.getLogger(__name__)

# Chroma y embedding (lazy)
_chroma_client = None
_embedding_fn = None
_embedding_model = None

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def _get_embedding_function():
    """Obtiene la función de embeddings para Chroma (modelo multilingüe)."""
    global _embedding_fn
    if _embedding_fn is None:
        try:
            from chromadb.utils import embedding_functions
            _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL_NAME
            )
            logger.info("Embedding function cargada: %s", EMBEDDING_MODEL_NAME)
        except Exception as e:
            logger.warning("No se pudo cargar sentence-transformers/Chroma: %s", e)
            raise
    return _embedding_fn


def _get_embedding_model():
    """Obtiene el modelo de embeddings (para Supabase: embed sin Chroma)."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            logger.info("Modelo de embeddings cargado: %s", EMBEDDING_MODEL_NAME)
        except Exception as e:
            logger.warning("No se pudo cargar SentenceTransformer: %s", e)
            raise
    return _embedding_model


def embed_text(text: str) -> List[float]:
    """
    Convierte un texto en vector de dimensión EMBEDDING_DIM.
    Usado por el backend Supabase (no depende de Chroma).
    """
    model = _get_embedding_model()
    vec = model.encode(text, normalize_embeddings=True, show_progress_bar=False)
    return vec.tolist()


def _get_client(persist_dir: str):
    """Obtiene el cliente persistente de Chroma."""
    global _chroma_client
    if _chroma_client is None:
        try:
            import chromadb
            path = Path(persist_dir)
            path.mkdir(parents=True, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=str(path))
            logger.info("Chroma PersistentClient inicializado en %s", persist_dir)
        except Exception as e:
            logger.warning("No se pudo inicializar Chroma: %s", e)
            raise
    return _chroma_client


class VectorStore:
    """
    Cache vectorial de preguntas/respuestas para reducir llamadas a DeepSeek.

    - Almacena (pregunta, respuesta) con embedding de la pregunta.
    - Antes de llamar a DeepSeek, busca la pregunta más similar; si supera
      min_similarity, devuelve la respuesta cacheada.
    - Backend: "chroma" (local) o "supabase" (pgvector en la nube).
    """

    COLLECTION_QA = "qa_cache"
    TABLE_QA = "qa_cache"
    RPC_MATCH = "match_qa_cache"

    def __init__(
        self,
        persist_dir: str = "data/chroma_db",
        min_similarity: float = 0.88,
        max_cache_entries: int = 2000,
        backend: str = "chroma",
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
    ):
        """
        Args:
            persist_dir: Directorio donde Chroma persiste (solo si backend="chroma").
            min_similarity: Umbral de similitud (0-1) para usar respuesta cacheada.
            max_cache_entries: Límite de entradas en cache.
            backend: "chroma" (local) o "supabase".
            supabase_url: URL del proyecto Supabase (si backend="supabase").
            supabase_key: service_role key de Supabase (si backend="supabase").
        """
        self.persist_dir = persist_dir
        self.min_similarity = min_similarity
        self.max_cache_entries = max_cache_entries
        self.backend = (backend or "chroma").lower()
        self.supabase_url = (supabase_url or os.getenv("SUPABASE_URL") or "").strip()
        self.supabase_key = (supabase_key or os.getenv("SUPABASE_SERVICE_KEY") or "").strip()
        self._collection = None
        self._supabase: Any = None
        self._ids_seen: List[str] = []

    def _get_collection(self):
        if self.backend != "chroma":
            return None
        if self._collection is None:
            client = _get_client(self.persist_dir)
            ef = _get_embedding_function()
            self._collection = client.get_or_create_collection(
                name=self.COLLECTION_QA,
                embedding_function=ef,
                metadata={"description": "Cache de preguntas/respuestas para ahorrar DeepSeek"},
            )
            logger.debug("Colección Chroma '%s' lista", self.COLLECTION_QA)
        return self._collection

    def _get_supabase(self):
        if self.backend != "supabase":
            return None
        if self._supabase is None:
            if not self.supabase_url or not self.supabase_key:
                raise ValueError("SUPABASE_URL y SUPABASE_SERVICE_KEY son necesarios para backend=supabase")
            from supabase import create_client
            self._supabase = create_client(self.supabase_url, self.supabase_key)
            logger.info("Cliente Supabase inicializado (cache vectorial)")
        return self._supabase

    def get_cached_response(self, query: str) -> Optional[str]:
        """
        Busca una respuesta cacheada para una pregunta similar.

        Args:
            query: Texto de la pregunta del usuario.

        Returns:
            Respuesta cacheada si existe una pregunta muy similar; None en caso contrario.
        """
        if not query or not query.strip():
            return None
        q = query.strip()
        try:
            if self.backend == "supabase":
                return self._get_cached_response_supabase(q)
            coll = self._get_collection()
            if not coll:
                return None
            # Chroma: distancias L2; con embeddings normalizados: similarity ≈ 1 - (distance^2 / 2)
            results = coll.query(
                query_texts=[q],
                n_results=1,
                include=["metadatas", "distances"],
            )
            if not results or not results["distances"] or not results["distances"][0]:
                return None
            distance = float(results["distances"][0][0])
            similarity = max(0.0, 1.0 - (distance * distance) / 2.0)
            if similarity < self.min_similarity:
                return None
            metadatas = results["metadatas"][0]
            if not metadatas or "response" not in metadatas[0]:
                return None
            cached = metadatas[0]["response"]
            logger.info("Cache vectorial hit (similitud=%.2f): se usa respuesta cacheada", similarity)
            return cached
        except Exception as e:
            logger.debug("Vector store get_cached_response: %s", e)
            return None

    def _get_cached_response_supabase(self, query: str) -> Optional[str]:
        """Búsqueda por similitud en Supabase (RPC match_qa_cache)."""
        sb = self._get_supabase()
        if not sb:
            return None
        embedding = embed_text(query)
        # Distancia coseno: 0 = idéntico. max_distance = 1 - min_similarity
        max_distance = max(0.0, 1.0 - self.min_similarity)
        try:
            r = sb.rpc(
                self.RPC_MATCH,
                {
                    "query_embedding": embedding,
                    "match_count": 1,
                    "max_distance": max_distance,
                },
            ).execute()
            if not r.data or len(r.data) == 0:
                return None
            row = r.data[0]
            distance = float(row.get("distance", 1.0))
            similarity = 1.0 - distance
            response_text = row.get("response_text")
            if not response_text:
                return None
            logger.info("Cache vectorial Supabase hit (similitud=%.2f): se usa respuesta cacheada", similarity)
            return response_text
        except Exception as e:
            logger.debug("Supabase get_cached_response: %s", e)
            return None

    def add_to_cache(self, query: str, response: str) -> None:
        """
        Guarda una pregunta y su respuesta en el cache vectorial.

        Args:
            query: Pregunta del usuario.
            response: Respuesta generada (p. ej. por DeepSeek).
        """
        if not query or not query.strip() or not response or not response.strip():
            return
        q = query.strip()
        resp = response.strip()[:1500]
        try:
            if self.backend == "supabase":
                self._add_to_cache_supabase(q, resp)
                return
            coll = self._get_collection()
            if not coll:
                return
            count = coll.count()
            if count >= self.max_cache_entries:
                self._evict_oldest(coll)
            doc_id = f"qa_{hash(q) % (10 ** 10)}"
            coll.upsert(
                ids=[doc_id],
                documents=[q],
                metadatas=[{"response": resp}],
            )
            logger.debug("Añadido al cache vectorial: id=%s", doc_id)
        except Exception as e:
            if self.backend == "supabase":
                logger.warning(
                    "Cache Supabase: no se pudo guardar (conexión, clave o formato): %s",
                    e,
                    exc_info=True,
                )
            else:
                logger.debug("Vector store add_to_cache: %s", e)

    def _add_to_cache_supabase(self, query: str, response: str) -> None:
        """Inserta en Supabase qa_cache (query_text, response_text, embedding)."""
        try:
            sb = self._get_supabase()
        except Exception as e:
            logger.warning("Cache Supabase: no se pudo conectar (¿supabase instalado? ¿URL/key en .env?): %s", e)
            raise
        try:
            embedding = embed_text(query)
        except Exception as e:
            logger.warning("Cache Supabase: no se pudo generar embedding (¿sentence-transformers?): %s", e)
            raise
        try:
            # Enviar como lista; si PostgREST da error de tipo, probar embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            payload = {
                "query_text": query,
                "response_text": response,
                "embedding": embedding,
            }
            sb.table(self.TABLE_QA).insert(payload).execute()
            logger.info("Cache vectorial Supabase: respuesta guardada correctamente")
            self._evict_supabase_if_needed(sb)
        except Exception as e:
            logger.warning(
                "Supabase add_to_cache falló (RLS, clave service_role o formato): %s",
                e,
                exc_info=True,
            )
            raise

    def _evict_supabase_if_needed(self, sb) -> None:
        """Elimina filas más antiguas si se supera max_cache_entries."""
        try:
            r = sb.table(self.TABLE_QA).select("id", count="exact").execute()
            count = r.count if hasattr(r, "count") and r.count is not None else len(r.data or [])
            if count <= self.max_cache_entries:
                return
            to_remove = count - int(self.max_cache_entries * 0.8)
            # Obtener IDs de las filas más antiguas y borrarlas (requiere RPC o delete por id)
            old = sb.table(self.TABLE_QA).select("id").order("created_at", desc=False).limit(to_remove).execute()
            if old.data:
                ids = [row["id"] for row in old.data]
                sb.table(self.TABLE_QA).delete().in_("id", ids).execute()
                logger.info("Cache vectorial Supabase: evicted %d entradas", len(ids))
        except Exception as e:
            logger.debug("Supabase evict: %s", e)

    def _evict_oldest(self, coll) -> None:
        """Elimina entradas cuando se supera max_cache_entries (solo Chroma)."""
        if not coll:
            return
        try:
            all_ids = coll.get()["ids"]
            if len(all_ids) <= self.max_cache_entries:
                return
            to_remove = len(all_ids) - int(self.max_cache_entries * 0.8)
            coll.delete(ids=all_ids[: to_remove])
            logger.info("Cache vectorial: evicted %d entradas", to_remove)
        except Exception as e:
            logger.warning("Error evicting cache: %s", e)

    def stats(self) -> dict:
        """Devuelve estadísticas del cache (número de entradas, etc.)."""
        try:
            if self.backend == "supabase":
                sb = self._get_supabase()
                if sb:
                    r = sb.table(self.TABLE_QA).select("id", count="exact").execute()
                    count = r.count if hasattr(r, "count") and r.count is not None else len(r.data or [])
                    return {"count": count, "backend": "supabase"}
                return {"count": 0, "backend": "supabase"}
            coll = self._get_collection()
            return {"count": coll.count() if coll else 0, "backend": "chroma", "collection": self.COLLECTION_QA}
        except Exception:
            return {"count": 0, "backend": self.backend}


def build_note_chunks(note_content: str, filename: str, chunk_size: int = 400) -> List[Tuple[str, dict]]:
    """
    Divide el contenido de una nota en fragmentos para indexar en vectores.

    Útil para RAG vectorial sobre notas (búsqueda semántica).

    Args:
        note_content: Texto completo de la nota.
        filename: Nombre del archivo (para metadata).
        chunk_size: Aproximadamente caracteres por fragmento.

    Returns:
        Lista de (texto_fragmento, metadata).
    """
    chunks: List[Tuple[str, dict]] = []
    text = (note_content or "").strip()
    if not text:
        return chunks
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Intentar cortar en salto de línea
        if end < len(text):
            last_nl = text.rfind("\n", start, end + 1)
            if last_nl >= start:
                end = last_nl + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append((piece, {"source": filename, "chunk_index": idx}))
            idx += 1
        start = end
    return chunks
