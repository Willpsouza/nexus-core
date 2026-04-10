import asyncio
import sys
from utils.logger import logger
from core.kernel import Kernel
from modules.wm_module import WindowManagerModule

async def bootstrap():
    kernel = Kernel.get_instance()
    await kernel.load_standard_modules()

    wm = WindowManagerModule()
    await kernel.register_module(wm)

    app = wm.get_app_instance()
    try:
        await app.run_async()
    except asyncio.CancelledError:
        logger.info("Application cancelled, proceeding to shutdown", component="MAIN")

    await kernel.shutdown()

def main():
    try:
        asyncio.run(bootstrap())
    except Exception as e:
        logger.critical(str(e), component="MAIN")
        sys.exit(1)

if __name__ == "__main__":
    main()