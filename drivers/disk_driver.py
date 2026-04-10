import pickle
import os
from utils.logger import logger

class DiskDriver:
    def __init__(self, disk_path: str = "nexus_disk.img"):
        self.disk_path = disk_path
        self.is_loaded = False

    def save(self, vfs_root) -> bool:
        try:
            with open(self.disk_path, 'wb') as f:
                pickle.dump(vfs_root, f)
            logger.info(f"Disk saved: {self.disk_path} ({os.path.getsize(self.disk_path)} bytes)", component="DISK")
            return True
        except Exception as e:
            logger.error(f"Disk save failed: {e}", component="DISK")
            return False

    def load(self):
        if not os.path.exists(self.disk_path):
            logger.info("No existing disk image found. Starting fresh.", component="DISK")
            return None
        
        try:
            with open(self.disk_path, 'rb') as f:
                root = pickle.load(f)
            logger.info(f"Disk loaded: {self.disk_path}", component="DISK")
            self.is_loaded = True
            return root
        except Exception as e:
            logger.error(f"Disk load failed: {e}", component="DISK")
            return None