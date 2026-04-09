import asyncio
from typing import Any, Dict, Callable
from utils.logger import logger

class ModuleState:
    UNLOADED = "UNLOADED"
    LOADING = "LOADING"
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"
    UNLOADING = "UNLOADING"

class BaseModule:
    """
    Classe base para todos os módulos do NEXUS CORE.
    Garante padronização, lifecycle management e isolamento de erros.
    """
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.state = ModuleState.UNLOADED
        self.dependencies: list[str] = []
        self._event_handlers: Dict[str, Callable] = {}
        logger.info(f"Module '{name}' v{version} instance created", component="MODULE_SYS")

    async def on_load(self, kernel: Any) -> bool:
        """
        Chamado quando o módulo é carregado pelo Kernel.
        Retorne True para sucesso, False para falha.
        """
        self.state = ModuleState.LOADING
        logger.debug(f"Loading module: {self.name}", component="MODULE_SYS")
        try:
            # Lógica específica de inicialização deve ser sobrescrita
            await self.init(kernel)
            self.state = ModuleState.ACTIVE
            logger.info(f"Module '{self.name}' loaded successfully", component="MODULE_SYS")
            return True
        except Exception as e:
            self.state = ModuleState.ERROR
            logger.error(f"Failed to load module '{self.name}': {e}", component="MODULE_SYS")
            return False

    async def init(self, kernel: Any):
        """Override this method for specific initialization logic."""
        pass

    async def on_unload(self):
        """Chamado antes do módulo ser descarregado. Limpeza obrigatória."""
        self.state = ModuleState.UNLOADING
        logger.debug(f"Unloading module: {self.name}", component="MODULE_SYS")
        try:
            await self.cleanup()
            self.state = ModuleState.UNLOADED
            logger.info(f"Module '{self.name}' unloaded successfully", component="MODULE_SYS")
        except Exception as e:
            logger.error(f"Error unloading module '{self.name}': {e}", component="MODULE_SYS")
            self.state = ModuleState.ERROR

    async def cleanup(self):
        """Override this for specific cleanup logic."""
        pass

    async def handle_event(self, event_type: str, data: Any):
        """Processa eventos recebidos pelo SysBus."""
        if self.state != ModuleState.ACTIVE:
            return
        
        handler = self._event_handlers.get(event_type)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Event handler error in {self.name} for {event_type}: {e}", component="MODULE_SYS")

    def subscribe(self, event_type: str, handler: Callable):
        """Inscreve o módulo em um evento do SysBus."""
        self._event_handlers[event_type] = handler