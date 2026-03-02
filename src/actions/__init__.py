"""
Actions Package - Acciones del sistema

Este paquete contiene todas las acciones que Kiro puede ejecutar:
- YouTubeAction: Reproducir videos de YouTube
- AppLauncherAction: Abrir aplicaciones del sistema
- WebBrowserAction: Abrir sitios web
- FileWriterAction: Crear y escribir notas en Markdown
"""

from src.actions.action import Action, ActionResult
from src.actions.youtube_action import YouTubeAction
from src.actions.app_launcher_action import AppLauncherAction
from src.actions.web_browser_action import WebBrowserAction
from src.actions.file_writer_action import FileWriterAction


__all__ = [
    'Action',
    'ActionResult',
    'YouTubeAction',
    'AppLauncherAction',
    'WebBrowserAction',
    'FileWriterAction',
]
