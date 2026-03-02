"""
Gestor de interfaz rica para consola usando la librería rich.

Este módulo proporciona una interfaz visual profesional con paneles coloridos,
indicadores de estado y feedback visual claro.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box
from src.models import SystemState


class RichUIManager:
    """Gestor de interfaz rica para consola"""
    
    # Colores del sistema para cada estado
    STATE_COLORS = {
        SystemState.ESCUCHANDO: "green",
        SystemState.PROCESANDO: "yellow",
        SystemState.BUSCANDO: "blue",
        SystemState.HABLANDO: "cyan"
    }
    
    # Iconos para cada estado
    STATE_ICONS = {
        SystemState.ESCUCHANDO: "🎤",
        SystemState.PROCESANDO: "⚙️",
        SystemState.BUSCANDO: "🔍",
        SystemState.HABLANDO: "🔊"
    }
    
    def __init__(self):
        """Inicializa console y componentes de rich"""
        self.console = Console()
        self.current_state = SystemState.ESCUCHANDO
    
    def show_banner(self):
        """Muestra banner de inicio del sistema"""
        banner_text = Text()
        banner_text.append("ASISTONTO\n", style="bold cyan")
        banner_text.append("Asistente de Voz Inteligente\n", style="white")
        banner_text.append("Fase 2: Web Search + Rich UI + Threading", style="dim")
        
        panel = Panel(
            banner_text,
            box=box.DOUBLE,
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def update_state(self, state: SystemState):
        """
        Actualiza panel de estado del sistema.
        
        Args:
            state: Nuevo estado del sistema
        """
        self.current_state = state
        color = self.STATE_COLORS[state]
        icon = self.STATE_ICONS[state]
        
        panel = Panel(
            f"{icon} {state.value}",
            border_style=color,
            box=box.ROUNDED
        )
        self.console.print(panel)
    
    def show_user_message(self, text: str):
        """
        Muestra mensaje del usuario con formato.
        
        Args:
            text: Texto del mensaje del usuario
        """
        message = Text()
        message.append("💬 Tú: ", style="bold white")
        message.append(text, style="white")
        
        panel = Panel(message, border_style="white", box=box.ROUNDED)
        self.console.print(panel)
    
    def show_assistant_message(self, text: str, used_web_search: bool = False):
        """
        Muestra respuesta del asistente con formato.
        
        Args:
            text: Texto de la respuesta del asistente
            used_web_search: Si se usó búsqueda web para esta respuesta
        """
        message = Text()
        message.append("🤖 Kiro: ", style="bold cyan")
        message.append(text, style="cyan")
        
        panel = Panel(message, border_style="cyan", box=box.ROUNDED)
        self.console.print(panel)
        
        # Mostrar indicador si se usó web search
        if used_web_search:
            self.console.print("  [dim]🌐 Información de internet[/dim]")
    
    def show_thinking_indicator(self):
        """Muestra indicador animado de 'pensando'"""
        self.console.print("[yellow]⚙️  Pensando...[/yellow]")
    
    def show_searching_indicator(self):
        """Muestra indicador animado de 'buscando'"""
        self.console.print("[blue]🔍 Buscando en internet...[/blue]")
    
    def show_speaking_indicator(self):
        """Muestra indicador animado de 'hablando'"""
        self.console.print("[cyan]🔊 Hablando...[/cyan]")
    
    def show_error(self, error_message: str):
        """
        Muestra mensaje de error.
        
        Args:
            error_message: Mensaje de error a mostrar
        """
        error_text = Text()
        error_text.append("❌ Error: ", style="bold red")
        error_text.append(error_message, style="red")
        
        panel = Panel(error_text, border_style="red", box=box.ROUNDED)
        self.console.print(panel)
