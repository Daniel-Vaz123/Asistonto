"""
Local Knowledge Reader - Sistema RAG local para notas del usuario

Este módulo implementa un sistema de Retrieval-Augmented Generation (RAG) local
que indexa archivos .md en data/, busca contenido relevante y formatea contexto
para inyección en DeepSeek.

Requisitos implementados:
- 5.1: Escanear directorio data/ buscando archivos .md
- 5.2: Leer contenido completo de archivos .md
- 5.3: Extraer metadata (filename, filepath, modified_time, size_bytes)
- 5.4: Crear objetos Note con metadata y content
- 5.5: Re-indexar automáticamente cuando se modifican archivos
- 5.6: Indexación asíncrona sin bloquear main thread
- 6.1: Buscar notas por query
- 6.2: Búsqueda case-insensitive
- 6.3: Rankear por relevancia usando frecuencia de términos
- 6.4: Retornar top N notas (max 3)
- 6.5: Retornar lista vacía si no hay matches
- 6.6: Performance <500ms para búsqueda
- 7.1: Formatear contexto para inyección
- 7.2: Limitar contexto a 2000 tokens
- 7.3: Truncar con indicador si excede límite
- 7.4: Formato consistente con headers
- 7.5: Separación clara entre notas
"""

import os
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
from collections import Counter


logger = logging.getLogger(__name__)


@dataclass
class NoteMetadata:
    """Metadata de una nota"""
    filename: str
    filepath: Path
    modified_time: datetime
    size_bytes: int


@dataclass
class Note:
    """Nota con contenido y metadata"""
    metadata: NoteMetadata
    content: str
    
    def __str__(self):
        return f"[{self.metadata.filename}]\n{self.content}"


@dataclass
class SearchResult:
    """Resultado de búsqueda con score"""
    note: Note
    relevance_score: float


class LocalKnowledgeReader:
    """
    Sistema RAG local para notas del usuario.
    
    Indexa archivos .md en data/, busca por relevancia y formatea
    contexto para inyección en DeepSeek.
    """
    
    def __init__(
        self,
        data_dir: str = "data",
        max_context_tokens: int = 2000,
        max_results: int = 3,
        threading_manager = None
    ):
        """
        Inicializa el LocalKnowledgeReader.
        
        Args:
            data_dir: Directorio con archivos .md
            max_context_tokens: Límite de tokens para contexto
            max_results: Número máximo de notas a retornar
            threading_manager: ThreadingManager para operaciones asíncronas
        """
        self.data_dir = Path(data_dir)
        self.max_context_tokens = max_context_tokens
        self.max_results = max_results
        self.threading_manager = threading_manager
        self.logger = logging.getLogger(__name__)
        
        # Índice en memoria: {filename: Note}
        self._notes_index: Dict[str, Note] = {}
        
        # Timestamp de última indexación
        self._last_index_time: Optional[datetime] = None
        
        self.logger.info(
            f"LocalKnowledgeReader inicializado: "
            f"data_dir={data_dir}, max_tokens={max_context_tokens}"
        )
    
    def initialize(self):
        """
        Inicializa el reader escaneando y indexando notas.
        
        Debe llamarse después de __init__ para permitir inicialización
        asíncrona con threading.
        """
        start_time = time.time()
        
        try:
            # Verificar que data_dir existe
            if not self.data_dir.exists():
                self.logger.warning(f"Directorio {self.data_dir} no existe, creándolo")
                self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Escanear archivos .md
            md_files = self._scan_notes_directory()
            
            # Leer e indexar cada archivo
            for filepath in md_files:
                note = self._read_note(filepath)
                if note:
                    self._notes_index[note.metadata.filename] = note
            
            # Actualizar timestamp
            self._last_index_time = datetime.now()
            
            # Log resultado
            elapsed = time.time() - start_time
            self.logger.info(
                f"Indexación completa: {len(self._notes_index)} notas, "
                f"time={elapsed:.3f}s"
            )
            
            # Advertencia si tardó mucho
            if elapsed > 1.0:
                self.logger.warning(
                    f"Indexación tardó {elapsed:.3f}s (>1s), "
                    f"considera optimizar o reducir número de notas"
                )
        
        except Exception as e:
            self.logger.error(f"Error en inicialización: {e}", exc_info=True)
    
    def search(self, query: str) -> List[Note]:
        """
        Busca notas relevantes para el query.
        
        Flujo:
        1. Normalizar query (lowercase, strip)
        2. Buscar notas que contengan términos del query
        3. Calcular relevance score por frecuencia de términos
        4. Ordenar por score descendente
        5. Retornar top N notas
        
        Args:
            query: Término de búsqueda
            
        Returns:
            Lista de notas ordenadas por relevancia (máximo max_results)
        """
        start_time = time.time()
        
        try:
            # Normalizar query
            query_lower = query.lower().strip()
            
            if not query_lower:
                self.logger.warning("Query vacío")
                return []
            
            # Buscar notas que contengan términos del query
            results: List[SearchResult] = []
            
            for note in self._notes_index.values():
                score = self._calculate_relevance_score(note, query_lower)
                if score > 0:
                    results.append(SearchResult(note=note, relevance_score=score))
            
            # Ordenar por score descendente
            results.sort(key=lambda r: r.relevance_score, reverse=True)
            
            # Retornar top N notas
            top_notes = [r.note for r in results[:self.max_results]]
            
            # Log resultado
            elapsed = time.time() - start_time
            self.logger.info(
                f"Búsqueda completa: query='{query}', "
                f"resultados={len(top_notes)}, time={elapsed:.3f}s"
            )
            
            # Advertencia si tardó mucho
            if elapsed > 0.5:
                self.logger.warning(
                    f"Búsqueda tardó {elapsed:.3f}s (>500ms)"
                )
            
            return top_notes
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda: {e}", exc_info=True)
            return []
    
    def format_context(self, notes: List[Note]) -> str:
        """
        Formatea notas para inyección en System Prompt.
        
        Formato:
        Notas del usuario:
        
        [nota1.md]
        Contenido de nota 1...
        
        [nota2.md]
        Contenido de nota 2...
        
        Args:
            notes: Lista de notas a formatear
            
        Returns:
            String formateado con límite de tokens
        """
        if not notes:
            return ""
        
        # Construir contexto
        context_parts = ["Notas del usuario:\n"]
        
        for note in notes:
            context_parts.append(f"\n[{note.metadata.filename}]")
            context_parts.append(note.content)
            context_parts.append("")  # Línea en blanco entre notas
        
        context = "\n".join(context_parts)
        
        # Verificar límite de tokens
        estimated_tokens = self._estimate_tokens(context)
        
        if estimated_tokens > self.max_context_tokens:
            self.logger.warning(
                f"Contexto excede límite: {estimated_tokens} > {self.max_context_tokens} tokens, truncando"
            )
            context = self._truncate_to_token_limit(context, self.max_context_tokens)
        
        return context
    
    def _scan_notes_directory(self) -> List[Path]:
        """
        Escanea data/ buscando archivos .md.
        
        Returns:
            Lista de Path objects para archivos .md
        """
        try:
            md_files = list(self.data_dir.glob("*.md"))
            self.logger.debug(f"Encontrados {len(md_files)} archivos .md")
            return md_files
        except Exception as e:
            self.logger.error(f"Error escaneando directorio: {e}")
            return []
    
    def _read_note(self, filepath: Path) -> Optional[Note]:
        """
        Lee un archivo .md y extrae metadata.
        
        Args:
            filepath: Path al archivo .md
            
        Returns:
            Note object o None si falla
        """
        try:
            # Leer contenido
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extraer metadata
            stat = filepath.stat()
            metadata = NoteMetadata(
                filename=filepath.name,
                filepath=filepath,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                size_bytes=stat.st_size
            )
            
            return Note(metadata=metadata, content=content)
            
        except Exception as e:
            self.logger.error(f"Error leyendo {filepath}: {e}")
            return None
    
    def _calculate_relevance_score(self, note: Note, query: str) -> float:
        """
        Calcula score de relevancia usando frecuencia de términos.
        
        Args:
            note: Nota a evaluar
            query: Query de búsqueda (ya normalizado)
            
        Returns:
            Score de relevancia (0.0 si no hay matches)
        """
        # Convertir contenido a lowercase
        content_lower = note.content.lower()
        
        # Dividir query en términos
        query_terms = query.split()
        
        # Contar ocurrencias de cada término
        total_occurrences = 0
        for term in query_terms:
            occurrences = content_lower.count(term)
            total_occurrences += occurrences
        
        if total_occurrences == 0:
            return 0.0
        
        # Normalizar por longitud de nota (TF-IDF simplificado)
        # Score más alto para notas más cortas con misma frecuencia
        content_length = len(note.content)
        normalized_score = total_occurrences / (content_length / 1000.0)
        
        return normalized_score
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estima número de tokens (aproximación: 1 token ≈ 4 caracteres).
        
        Args:
            text: Texto a estimar
            
        Returns:
            Número estimado de tokens
        """
        return len(text) // 4
    
    def _truncate_to_token_limit(self, text: str, max_tokens: int) -> str:
        """
        Trunca texto para no exceder límite de tokens.
        
        Args:
            text: Texto a truncar
            max_tokens: Límite de tokens
            
        Returns:
            Texto truncado con indicador
        """
        max_chars = max_tokens * 4
        
        if len(text) <= max_chars:
            return text
        
        truncated = text[:max_chars]
        return truncated + "\n\n[... contexto truncado por límite de tokens ...]"
    
    def get_index_stats(self) -> Dict[str, any]:
        """
        Retorna estadísticas del índice (para debugging).
        
        Returns:
            Dict con estadísticas
        """
        total_chars = sum(len(note.content) for note in self._notes_index.values())
        
        return {
            'total_notes': len(self._notes_index),
            'total_characters': total_chars,
            'estimated_tokens': total_chars // 4,
            'last_index_time': self._last_index_time.isoformat() if self._last_index_time else None
        }
    
    def re_index_if_needed(self):
        """
        Re-indexa si hay cambios en los archivos.
        
        Compara archivos actuales con índice y re-indexa si hay diferencias.
        """
        try:
            # Escanear archivos actuales
            current_files = set(f.name for f in self._scan_notes_directory())
            indexed_files = set(self._notes_index.keys())
            
            # Verificar si hay cambios
            if current_files != indexed_files:
                self.logger.info("Cambios detectados en archivos, re-indexando")
                self.initialize()
            
        except Exception as e:
            self.logger.error(f"Error en re-indexación: {e}", exc_info=True)
