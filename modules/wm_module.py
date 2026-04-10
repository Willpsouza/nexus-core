from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Label, Button, Input
from textual.binding import Binding
from textual.screen import Screen
from modules.base_module import BaseModule
from utils.logger import logger
import datetime

class TerminalWindow(Static):
    """Janela de Terminal Emulado"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kernel = None
        self.history = []

    def compose(self) -> ComposeResult:
        yield Static("NEXUS TERMINAL - v1.0", classes="title-bar")
        yield Static("", id="term-output", classes="content-area")
        yield Input(placeholder="Digite comando...", id="term-input")

    def on_mount(self):
        # Garante que os widgets filhos existem antes de acessar
        self.output = self.query_one("#term-output", Static)
        self.input_widget = self.query_one("#term-input", Input)
        self.history = []
        self.write_line("NEXUS CORE Terminal initialized.")
        self.write_line("Type 'help' for available commands.")
        self.input_widget.focus()

    def write_line(self, text: str):
        self.history.append(text)
        if len(self.history) > 50:
            self.history = self.history[-50:]
        self.output.update("\n".join(self.history))

    def on_input_submitted(self, event: Input.Submitted):
        cmd = event.value.strip()
        self.input_widget.value = ""
        if not cmd:
            return
        
        self.write_line(f"user@nexus:~$ {cmd}")
        self.process_command(cmd)

    def process_command(self, cmd: str):
        if not self.kernel or not self.kernel.vfs:
            self.write_line("ERRO: Kernel ou VFS não disponível.")
            return

        parts = cmd.split()
        if not parts:
            return
        
        command = parts[0].lower()
        vfs = self.kernel.vfs
        
        try:
            if command == "help":
                self.write_line("Comandos: ls, cd, pwd, mkdir, touch, cat, rm, ps, mem, clear, exit")
            elif command == "exit":
                self.write_line("Closing terminal...")
                self.remove()
                return
            elif command == "ls":
                path = parts[1] if len(parts) > 1 else "."
                content = vfs.ls(path)
                self.write_line("  ".join(content) if content else "[DIR VAZIO]")
            elif command == "pwd":
                self.write_line(vfs.get_current_path())
            elif command == "cd":
                if len(parts) > 1:
                    if vfs.cd(parts[1]):
                        self.write_line(f"Mudado para {vfs.get_current_path()}")
                    else:
                        self.write_line(f"Erro: Diretorio '{parts[1]}' nao encontrado")
                else:
                    self.write_line("Uso: cd <caminho>")
            elif command == "mkdir":
                if len(parts) > 1:
                    if vfs.mkdir(parts[1]):
                        self.write_line(f"MKDIR: Sucesso")
                    else:
                        self.write_line("Erro: Ja existe ou caminho invalido")
            elif command == "touch":
                if len(parts) > 1:
                    if vfs.touch(parts[1]):
                        self.write_line(f"TOUCH: Arquivo '{parts[1]}' criado")
                    else:
                        self.write_line("Erro: Arquivo ja existe")
            elif command == "cat":
                if len(parts) > 1:
                    content = vfs.read_file(parts[1])
                    if content:
                        self.write_line(content)
                    else:
                        self.write_line("Erro: Arquivo nao encontrado ou vazio")
            elif command == "rm":
                if len(parts) > 1:
                    if vfs.remove(parts[1]):
                        self.write_line(f"RM: '{parts[1]}' removido")
                    else:
                        self.write_line("Erro: Arquivo/diretorio nao encontrado")
            elif command == "ps":
                if self.kernel.scheduler:
                    self.write_line("PID\tNAME\t\tSTATE\tPRIORITY")
                    self.write_line("-" * 40)
                    for pid, proc in self.kernel.scheduler.processes.items():
                        self.write_line(f"{pid}\t{proc.name}\t\t{proc.state.value}\t{proc.priority}")
                else:
                    self.write_line("Scheduler not available")
            elif command == "mem":
                if self.kernel.memory:
                    stats = self.kernel.memory.get_usage_stats()
                    total_mb = stats['total_memory'] / (1024 * 1024)
                    used_mb = stats['used_memory'] / (1024 * 1024)
                    self.write_line(f"Total: {total_mb:.0f}MB | Used: {used_mb:.2f}MB ({stats['usage_percent']:.1f}%)")
                else:
                    self.write_line("Memory manager not available")
            elif command == "clear":
                self.history = []
                self.output.update("")
            else:
                self.write_line(f"Comando desconhecido: {command}")
        except Exception as e:
            self.write_line(f"ERRO CRITICO: {str(e)}")

class MainScreen(Screen):
    def __init__(self, kernel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kernel = kernel

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(datetime.datetime.now().strftime("%H:%M:%S"), id="clock-display")
        
        with Container(id="main-layout"):
            yield Static("SYSTEM STATUS", classes="title-bar")
            yield Static("Kernel: Online\nMemory: OK\nModules: Active\nVFS: Mounted", classes="content-area")
            
        with Horizontal(id="dock"):
            yield Button("Open Terminal", id="btn-term", variant="primary")
            yield Button("Quit System", id="btn-quit", variant="error")
            
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-quit":
            self.app.exit()
        elif event.button.id == "btn-term":
            term = TerminalWindow(id="active-terminal")
            term.kernel = self.kernel
            self.mount(term)
            # Foca no input após a renderização
            self.call_later(self.focus_terminal_input)

    def focus_terminal_input(self):
        try:
            term = self.query_one("#active-terminal", TerminalWindow)
            inp = term.query_one(Input)
            inp.focus()
        except Exception:
            pass

class NexusWMApp(App):
    CSS = """
    Screen { background: #0d1117; }
    
    #main-layout {
        height: 1fr;
        margin: 1;
        border: solid blue;
        background: #161b22;
    }

    .title-bar {
        background: #1f6feb;
        color: white;
        padding: 0 1;
        text-style: bold;
        width: 100%;
    }

    .content-area {
        padding: 1;
        color: #c9d1d9;
        height: 1fr;
        width: 100%;
    }

    #clock-display {
        dock: right;
        padding: 0 1;
        background: #238636;
        color: white;
        margin: 0 1;
    }

    #dock {
        dock: bottom;
        height: 4;
        align: center middle;
        padding: 1;
        background: #21262d;
    }

    Button { margin: 0 2; min-width: 20; }

    /* Estilos do Terminal */
    TerminalWindow {
        layer: foreground;
        width: 90%;
        height: 80%;
        align: center middle;
        background: #000000;
        border: thick green;
        padding: 1;
    }

    TerminalWindow .title-bar {
        background: #00aa00;
        color: black;
        text-align: center;
    }

    TerminalWindow .content-area {
        background: #000000;
        color: #00ff00;
        height: 1fr;
        width: 100%;
        overflow-y: auto;
        text-style: bold;
    }

    TerminalWindow Input {
        dock: bottom;
        background: #000000;
        color: #00ff00;
        border: none;
        padding: 0;
    }
    """

    BINDINGS = [Binding("q", "quit", "Quit")]

    def __init__(self, kernel):
        super().__init__()
        self.kernel = kernel

    def on_mount(self):
        # Apenas carrega a tela principal. Nada de buscar widgets de terminal aqui.
        self.push_screen(MainScreen(self.kernel))

class WindowManagerModule(BaseModule):
    def __init__(self):
        super().__init__("NexusWM", "1.0.0")
        self.app = None

    async def init(self, kernel):
        self.kernel = kernel
        logger.info("Graphical Subsystem Ready", component="WM")

    def get_app_instance(self):
        return NexusWMApp(self.kernel)

    async def cleanup(self):
        logger.info("Graphical Subsystem Halted", component="WM")
        # Salva o estado do disco antes de fechar
        try:
            self.kernel.vfs.save_state()
            logger.info("System State Persisted to Disk", component="DISK")
        except Exception as e:
            logger.error(f"Failed to save disk state: {e}", component="DISK")