import asyncio
from typing import Dict, Any, List, Optional, Callable
from utils.logger import logger
from modules.base_module import BaseModule, ModuleState

class SystemBus:
    """
    Barramento de Eventos Assíncrono (Pub/Sub).
    Desacopla completamente os módulos.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        logger.debug("SystemBus initialized", component="KERNEL")

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    async def publish(self, event_type: str, data: Any = None):
        """Dispara um evento para todos os inscritos assincronamente."""
        if event_type in self._subscribers:
            tasks = []
            for callback in self._subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        tasks.append(callback(data))
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Subscriber error for event {event_type}: {e}", component="SYSBUS")
            
            if tasks:
                # Executa todos em paralelo mas captura erros individualmente
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        logger.warning(f"Async subscriber exception: {res}", component="SYSBUS")

class Kernel:
    """
    O Núcleo do NEXUS CORE.
    Gerencia o ciclo de vida dos módulos, o SysBus e o estado global.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Kernel, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.modules: Dict[str, BaseModule] = {}
        self.sysbus = SystemBus()
        self._running = False
        self._shutdown_event = asyncio.Event()
        
        # Registra eventos internos
        self.sysbus.subscribe("SYSTEM_SHUTDOWN", self._on_shutdown_event)
        
        self._initialized = True
        logger.info("NEXUS CORE Kernel initialized (Singleton)", component="KERNEL")

    async def _on_shutdown_event(self, data):
        logger.info("Shutdown signal received by Kernel", component="KERNEL")
        self._running = False

    async def register_module(self, module: BaseModule) -> bool:
        """Registra e carrega um módulo dinamicamente."""
        if module.name in self.modules:
            logger.warning(f"Module {module.name} already registered", component="KERNEL")
            return False

        # Verifica dependências
        for dep in module.dependencies:
            if dep not in self.modules or self.modules[dep].state != ModuleState.ACTIVE:
                logger.error(f"Dependency missing for {module.name}: {dep}", component="KERNEL")
                return False

        self.modules[module.name] = module
        success = await module.on_load(self)
        
        if not success:
            del self.modules[module.name]
            
        return success

    async def unregister_module(self, name: str) -> bool:
        """Descarrega e remove um módulo dinamicamente."""
        if name not in self.modules:
            return False
        
        module = self.modules[name]
        
        # Verifica se outros módulos dependem deste
        for other_name, other_mod in self.modules.items():
            if name in other_mod.dependencies and other_mod.state == ModuleState.ACTIVE:
                logger.error(f"Cannot unload {name}. Module {other_name} depends on it.", component="KERNEL")
                return False

        await module.on_unload()
        del self.modules[name]
        logger.info(f"Module {name} unregistered", component="KERNEL")
        return True

    async def run(self):
        """Loop principal do Kernel."""
        self._running = True
        logger.info("Kernel main loop started", component="KERNEL")
        
        while self._running:
            # Aqui entraria o Watchdog e tarefas de manutenção
            await asyncio.sleep(0.5)
            
            # Exemplo de heartbeat do sistema
            if len(self.modules) > 0:
                active_count = sum(1 for m in self.modules.values() if m.state == ModuleState.ACTIVE)
                logger.debug(f"System Heartbeat: {active_count}/{len(self.modules)} modules active", component="KERNEL")

        await self.shutdown()

    async def shutdown(self):
        """Desliga o kernel e todos os módulos ordenadamente."""
        logger.info("Initiating Kernel shutdown sequence...", component="KERNEL")
        
        # Descarrega módulos em ordem inversa (LIFO)
        for name in list(reversed(self.modules.keys())):
            await self.unregister_module(name)
            
        logger.info("NEXUS CORE Kernel halted.", component="KERNEL")