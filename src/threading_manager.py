"""
Gestor de threads para operaciones asíncronas.

Este módulo gestiona la ejecución de operaciones bloqueantes en threads separados
para mantener la UI responsiva.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError
from typing import Callable, Any


logger = logging.getLogger(__name__)


class ThreadingManager:
    """Gestor de threads para operaciones asíncronas"""
    
    def __init__(self, max_workers: int = 3):
        """
        Inicializa el gestor de threads.
        
        Args:
            max_workers: Número máximo de threads concurrentes (default: 3)
        """
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="asistonto_worker"
        )
        self.logger = logging.getLogger(__name__)
    
    def execute_async(
        self, 
        func: Callable, 
        *args,
        timeout: int = None,
        **kwargs
    ) -> Future:
        """
        Ejecuta función en thread separado con manejo de errores.
        
        Args:
            func: Función a ejecutar
            timeout: Timeout en segundos (opcional)
            *args, **kwargs: Argumentos para la función
            
        Returns:
            Future object para obtener resultado
        """
        future = self.executor.submit(func, *args, **kwargs)
        
        # Agregar callback para logging de errores
        def error_callback(f: Future):
            try:
                f.result(timeout=timeout)
            except TimeoutError:
                self.logger.error(f"Timeout en {func.__name__}")
            except Exception as e:
                self.logger.error(f"Error en {func.__name__}: {e}", exc_info=True)
        
        future.add_done_callback(error_callback)
        return future
    
    def shutdown(self):
        """Cierra el pool de threads"""
        self.executor.shutdown(wait=True, cancel_futures=True)
