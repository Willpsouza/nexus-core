from enum import Enum
from typing import List, Optional, Any
from utils.logger import logger

class ModuleState(Enum):
    LOADED = "LOADED"
    ACTIVE = "ACTIVE"
    STOPPED = "STOPPED"
    ERROR = "ERROR"

class BaseModule:
    """Classe base para todos os módulos do NEXUS CORE."""
    
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.state = ModuleState.LOADED
        self.dependencies: List[str] = []
        logger.debug(f"Module {name} v{version} instantiated", component="MODULE")
    
    async def on_load(self, kernel: Any) -> bool:
        """Chamado quando o módulo é registrado no Kernel."""
        try:
            logger.info(f"Module {self.name} loading...", component=self.name)
            await self.init(kernel)
            self.state = ModuleState.ACTIVE
            logger.info(f"Module {self.name} activated", component=self.name)
            return True
        except Exception as e:
            logger.error(f"Module {self.name} failed to load: {e}", component=self.name)
            self.state = ModuleState.ERROR
            return False
    
    async def on_unload(self):
        """Chamado quando o módulo é descarregado."""
        try:
            logger.info(f"Module {self.name} unloading...", component=self.name)
            await self.cleanup()
            self.state = ModuleState.STOPPED
            logger.info(f"Module {self.name} stopped", component=self.name)
        except Exception as e:
            logger.error(f"Module {self.name} error during unload: {e}", component=self.name)
    
    async def init(self, kernel: Any):
        """Override this method to initialize your module."""
        pass
    
    async def cleanup(self):
        """Override this method to cleanup your module."""
        pass
    
    async def handle_event(self, event_type: str, data: Any):
        """Override this method to handle events from SystemBus."""
        pass