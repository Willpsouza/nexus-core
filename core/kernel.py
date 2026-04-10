import asyncio
from typing import Dict, Any, List, Callable
from utils.logger import logger
from modules.base_module import BaseModule, ModuleState

class SystemBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event: str, cb: Callable):
        self._subscribers.setdefault(event, []).append(cb)

    async def publish(self, event: str, data: Any = None):
        for cb in self._subscribers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(cb): await cb(data)
                else: cb(data)
            except Exception as e:
                logger.error(f"SysBus error: {e}", component="SYSBUS")

class Kernel:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Kernel, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self.modules: Dict[str, BaseModule] = {}
        self.sysbus = SystemBus()
        self._running = False
        # Subsistemas Core
        self.memory = None
        self.scheduler = None
        self.vfs = None
        
        self._initialized = True
        logger.info("Kernel Ready", component="KERNEL")

    @staticmethod
    def get_instance():
        if Kernel._instance is None:
            Kernel._instance = Kernel()
        return Kernel._instance

    async def load_standard_modules(self):
        from core.memory import VirtualMemoryManager
        from core.scheduler import AsyncScheduler
        from core.vfs import VirtualFileSystem

        self.memory = VirtualMemoryManager(16)
        self.scheduler = AsyncScheduler()
        self.vfs = VirtualFileSystem()

        # Estrutura inicial
        self.vfs.mkdir("/home")
        self.vfs.mkdir("/data")
        logger.info("Core Modules Loaded (Mem, Sched, VFS)", component="KERNEL")

    def get_module(self, name: str):
        if name == 'VFS': return self.vfs
        if name == 'AsyncScheduler': return self.scheduler
        if name == 'VirtualMemoryManager': return self.memory
        return None

    async def register_module(self, module: BaseModule) -> bool:
        if module.name in self.modules: return False
        self.modules[module.name] = module
        return await module.on_load(self)

    async def run(self):
        self._running = True
        logger.info("Kernel Loop Started", component="KERNEL")
        while self._running:
            await asyncio.sleep(1)
            # Heartbeat opcional
        await self.shutdown()

    async def shutdown(self):
        logger.info("Shutting down...", component="KERNEL")
        self._running = False
        for name in list(reversed(self.modules.keys())):
            await self.unregister_module(name)

    async def unregister_module(self, name: str):
        if name in self.modules:
            await self.modules[name].on_unload()
            del self.modules[name]