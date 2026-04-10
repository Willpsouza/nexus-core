from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Label
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding
from utils.logger import logger

class DriverScreen(Screen):
    """Tela principal gerenciada pelo Driver Gráfico."""
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("t", "toggle_theme", "Theme", show=True),
    ]

    def __init__(self, wm_callback):
        super().__init__()
        self.wm_callback = wm_callback
        self.root_container = None

    def compose(self) -> ComposeResult:
        yield Header()
        # Área principal onde o WM vai desenhar as janelas
        yield Container(id="wm-desktop")
        yield Footer()

    def on_mount(self) -> None:
        self.root_container = self.query_one("#wm-desktop", Container)
        logger.info("Graphic Driver Screen Mounted", component="GRAPHIC")
        # Notifica o WM que a tela está pronta
        if self.wm_callback:
            self.wm_callback(self.root_container)

    def action_toggle_theme(self) -> None:
        self.theme = "dark" if self.theme == "light" else "dark"

class GraphicDriverApp(App):
    """Aplicação Principal que atua como Driver de Vídeo."""
    
    CSS = """
    #wm-desktop {
        width: 100%;
        height: 100%;
        background: $surface;
        border: solid $primary;
    }
    .nexus-window {
        background: $panel;
        border: solid $accent;
        padding: 1;
        margin: 1;
        width: auto;
        height: auto;
    }
    .window-title {
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(self, wm_init_callback):
        super().__init__()
        self.wm_init_callback = wm_init_callback

    def on_mount(self) -> None:
        self.push_screen(DriverScreen(self.wm_init_callback))

def run_graphic_driver(wm_init_callback):
    """Inicia o loop gráfico."""
    logger.info("Starting Graphic Driver...", component="GRAPHIC")
    app = GraphicDriverApp(wm_init_callback)
    app.run()