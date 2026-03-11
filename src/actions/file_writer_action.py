"""
File Writer Action - Creación y escritura de notas en Markdown

Implementa la acción de crear y escribir notas en formato Markdown
en el directorio data/.

Requisitos implementados:
- 6.1: Extraer contenido de nota
- 6.2: Crear archivo en data/
- 6.3: Formato Markdown con timestamp
- 6.4: Filename personalizado o por defecto
- 6.5: Append a archivo existente
- 6.6: Sanitización de filename
- 6.7: Validación de path
- 6.8: Confirmar creación
- 7.1: Timestamp ISO 8601
- 7.2: Formato de entrada con timestamp
- 7.3: Codificación UTF-8
- 7.4: Modo append
- 12.1: Límite de tamaño 10KB
- 12.2: Validación de path dentro de data/
- 12.3: Sanitización de filename
- 12.4: Codificación UTF-8
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from src.actions.action import Action, ActionResult


logger = logging.getLogger(__name__)


class FileWriterAction(Action):
    """
    Acción para crear y escribir notas en formato Markdown.
    
    Las notas se guardan en el directorio data/ con timestamp ISO 8601.
    """
    
    # Límite de tamaño de nota (10KB)
    MAX_NOTE_SIZE = 10 * 1024  # 10KB en bytes
    
    def __init__(self, data_dir: str = "data"):
        """
        Inicializa la acción de escritura de archivos.
        
        Args:
            data_dir: Directorio donde se guardarán las notas
        """
        self.data_dir = Path(data_dir)
        
        # Crear directorio si no existe
        # Requisito: 6.2 - Crear directorio data/
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"FileWriterAction inicializado: data_dir={self.data_dir.absolute()}")
    
    def get_name(self) -> str:
        """Retorna el nombre de la acción."""
        return "File Writer"
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Valida que el parámetro 'content' esté presente y no vacío.
        
        Args:
            parameters: Debe contener 'content' con el contenido de la nota
            
        Returns:
            True si es válido, False en caso contrario
        """
        if not parameters:
            logger.warning("Parámetros vacíos para FileWriterAction")
            return False
        
        content = parameters.get('content', '').strip()
        if not content:
            logger.warning("content vacío para FileWriterAction")
            return False
        
        # Validar tamaño
        # Requisito: 12.1 - Límite de tamaño 10KB
        if len(content.encode('utf-8')) > self.MAX_NOTE_SIZE:
            logger.warning(f"Contenido excede límite de {self.MAX_NOTE_SIZE} bytes")
            return False
        
        return True
    
    def execute(self, parameters: Dict[str, Any]) -> ActionResult:
        """
        Ejecuta la creación/escritura de la nota.
        
        Args:
            parameters: Debe contener:
                - 'content': Contenido de la nota (requerido)
                - 'filename': Nombre del archivo (opcional, default: 'notas.md')
            
        Returns:
            ActionResult con el resultado de la ejecución
            
        Requisito: 6.2 - Crear archivo en data/
        """
        # Validar parámetros
        if not self.validate_parameters(parameters):
            result = ActionResult(
                success=False,
                message="Parámetros inválidos",
                error="El contenido es requerido y no puede exceder 10KB"
            )
            self._log_execution(parameters, result)
            return result
        
        content = parameters['content'].strip()
        filename = parameters.get('filename', 'notas.md')
        
        try:
            # Sanitizar filename
            # Requisito: 6.6, 12.3 - Sanitización de filename
            filename = self._sanitize_filename(filename)
            
            # Asegurar extensión .md
            if not filename.endswith('.md'):
                filename += '.md'
            
            # Construir path completo
            file_path = self.data_dir / filename
            
            # Validar que el path esté dentro de data/
            # Requisito: 6.7, 12.2 - Validación de path
            if not self._is_safe_path(file_path):
                error_msg = "Path inválido: debe estar dentro del directorio data/"
                logger.error(error_msg)
                
                result = ActionResult(
                    success=False,
                    message="Error de seguridad",
                    error=error_msg
                )
                
                self._log_execution(parameters, result)
                return result
            
            # Generar timestamp ISO 8601
            # Requisito: 7.1 - Timestamp ISO 8601
            timestamp = datetime.now().isoformat()
            
            # Formatear entrada con timestamp
            # Requisito: 7.2 - Formato de entrada con timestamp
            entry = f"\n## {timestamp}\n\n{content}\n"
            
            # Determinar si es archivo nuevo o existente
            is_new_file = not file_path.exists()
            
            # Escribir nota
            # Requisito: 7.3, 12.4 - Codificación UTF-8
            # Requisito: 7.4, 6.5 - Modo append
            mode = 'w' if is_new_file else 'a'
            
            with open(file_path, mode, encoding='utf-8') as f:
                if is_new_file:
                    # Escribir header para archivo nuevo
                    f.write(f"# Notas - {filename}\n")
                
                f.write(entry)
            
            logger.info(f"Nota guardada: {file_path} ({'nuevo' if is_new_file else 'append'})")
            
            result = ActionResult(
                success=True,
                message=f"Nota guardada en {filename}",
                data={
                    'filename': filename,
                    'path': str(file_path.absolute()),
                    'is_new': is_new_file,
                    'timestamp': timestamp
                }
            )
            
            self._log_execution(parameters, result)
            return result
            
        except Exception as e:
            error_msg = f"Error al guardar nota: {str(e)}"
            logger.error(error_msg)
            
            result = ActionResult(
                success=False,
                message="Error al guardar nota",
                error=error_msg
            )
            
            self._log_execution(parameters, result)
            return result
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitiza el nombre de archivo removiendo caracteres peligrosos.
        
        Args:
            filename: Nombre de archivo a sanitizar
            
        Returns:
            Nombre de archivo sanitizado
            
        Requisito: 6.6, 12.3 - Sanitización de filename
        """
        # Remover caracteres no permitidos
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        # Remover espacios múltiples y reemplazar por guión
        filename = re.sub(r'\s+', '-', filename)
        
        # Remover puntos al inicio/fin
        filename = filename.strip('.')
        
        # Si queda vacío, usar default
        if not filename:
            filename = 'notas'
        
        return filename
    
    def _is_safe_path(self, file_path: Path) -> bool:
        """
        Verifica que el path esté dentro del directorio data/.
        
        Args:
            file_path: Path a verificar
            
        Returns:
            True si es seguro, False en caso contrario
            
        Requisito: 6.7, 12.2 - Validación de path
        """
        try:
            # Resolver paths absolutos
            file_abs = file_path.resolve()
            data_abs = self.data_dir.resolve()
            
            # Verificar que file_path esté dentro de data_dir
            return str(file_abs).startswith(str(data_abs))
        except Exception as e:
            logger.error(f"Error validando path: {e}")
            return False


# TODO: Agregar soporte para categorías/tags
# TODO: Implementar búsqueda de notas
# TODO: Agregar soporte para edición de notas existentes
# TODO: Implementar backup automático de notas
