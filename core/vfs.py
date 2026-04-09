import datetime
from typing import Dict, List, Optional, Union
from enum import Enum
from utils.logger import logger

class VFSNodeType(Enum):
    FILE = "FILE"
    DIRECTORY = "DIRECTORY"

class VFSNode:
    def __init__(self, name: str, node_type: VFSNodeType, parent: Optional['VFSDirectory'] = None):
        self.name = name
        self.node_type = node_type
        self.parent = parent
        self.created_at = datetime.datetime.now()
        self.modified_at = datetime.datetime.now()

    def get_path(self) -> str:
        if self.parent is None:
            return "/"
        parent_path = self.parent.get_path()
        if parent_path == "/":
            return f"/{self.name}"
        return f"{parent_path}/{self.name}"

class VFSFile(VFSNode):
    def __init__(self, name: str, parent: Optional['VFSDirectory'] = None):
        super().__init__(name, VFSNodeType.FILE, parent)
        self.content: bytes = b""

    def write(self, data: bytes) -> bool:
        try:
            self.content = data
            self.modified_at = datetime.datetime.now()
            return True
        except Exception as e:
            logger.error(f"Write failed for {self.get_path()}: {e}", component="VFS")
            return False

    def read(self, offset: int = 0, size: Optional[int] = None) -> bytes:
        if offset < 0 or offset > len(self.content):
            return b""
        end = len(self.content) if size is None else offset + size
        return self.content[offset:end]

class VFSDirectory(VFSNode):
    def __init__(self, name: str, parent: Optional['VFSDirectory'] = None):
        super().__init__(name, VFSNodeType.DIRECTORY, parent)
        self.children: Dict[str, VFSNode] = {}

    def add_node(self, node: VFSNode) -> bool:
        if node.name in self.children:
            return False
        node.parent = self
        self.children[node.name] = node
        self.modified_at = datetime.datetime.now()
        return True

    def remove_node(self, name: str) -> bool:
        if name not in self.children:
            return False
        del self.children[name]
        self.modified_at = datetime.datetime.now()
        return True

    def get_node(self, name: str) -> Optional[VFSNode]:
        return self.children.get(name)

    def list_contents(self) -> List[str]:
        return list(self.children.keys())

class VirtualFileSystem:
    def __init__(self):
        self.root = VFSDirectory("")
        self.current_dir: VFSDirectory = self.root
        logger.info("VirtualFileSystem initialized with root '/'", component="VFS")

    def _resolve_path(self, path: str) -> Optional[VFSNode]:
        if path == "/":
            return self.root
        
        parts = path.split('/')
        if path.startswith('/'):
            current = self.root
            parts = parts[1:]
        else:
            current = self.current_dir

        for part in parts:
            if part == "" or part == ".":
                continue
            if part == "..":
                if current.parent:
                    current = current.parent
                continue
            
            if not isinstance(current, VFSDirectory):
                return None
            
            node = current.get_node(part)
            if node is None:
                return None
            current = node
        
        return current

    def mkdir(self, path: str) -> bool:
        full_path = self._resolve_path(path)
        if full_path:
            logger.warning(f"Directory already exists: {path}", component="VFS")
            return False
        
        # Criar caminho intermediário se necessário (simplificado para criar apenas o último nó no diretório atual se relativo)
        # Para simplificar, vamos assumir que o pai existe ou é absoluto
        dir_name = path.split('/')[-1]
        parent_path = '/'.join(path.split('/')[:-1])
        
        if not parent_path or path.startswith('/') and path.count('/') == 1:
            parent = self.root
        else:
            parent_node = self._resolve_path(parent_path if path.startswith('/') else f"{self.current_dir.get_path()}/{parent_path}")
            if not parent_node or not isinstance(parent_node, VFSDirectory):
                logger.error(f"Parent directory not found for {path}", component="VFS")
                return False
            parent = parent_node

        new_dir = VFSDirectory(dir_name)
        if parent.add_node(new_dir):
            logger.debug(f"Directory created: {new_dir.get_path()}", component="VFS")
            return True
        return False

    def touch(self, path: str) -> bool:
        node = self._resolve_path(path)
        if node:
            return False # Já existe
        
        file_name = path.split('/')[-1]
        parent_path = '/'.join(path.split('/')[:-1])
        
        if not parent_path or (path.startswith('/') and path.count('/') == 1):
            parent = self.root
        else:
            # Lógica simplificada de resolução do pai
            abs_parent = parent_path if path.startswith('/') else f"{self.current_dir.get_path()}/{parent_path}"
            # Limpar duplas barras se houver
            abs_parent = abs_parent.replace('//', '/')
            parent_node = self._resolve_path(abs_parent)
            if not parent_node or not isinstance(parent_node, VFSDirectory):
                logger.error(f"Parent directory not found for {path}", component="VFS")
                return False
            parent = parent_node

        new_file = VFSFile(file_name)
        if parent.add_node(new_file):
            logger.debug(f"File created: {new_file.get_path()}", component="VFS")
            return True
        return False

    def write_file(self, path: str, data: bytes) -> bool:
        node = self._resolve_path(path)
        if not node:
            logger.error(f"File not found: {path}", component="VFS")
            return False
        if not isinstance(node, VFSFile):
            logger.error(f"Not a file: {path}", component="VFS")
            return False
        
        success = node.write(data)
        if success:
            logger.debug(f"Wrote {len(data)} bytes to {path}", component="VFS")
        return success

    def read_file(self, path: str) -> Optional[bytes]:
        node = self._resolve_path(path)
        if not node or not isinstance(node, VFSFile):
            return None
        return node.read()

    def ls(self, path: str = ".") -> Optional[List[str]]:
        if path == ".":
            target = self.current_dir
        else:
            node = self._resolve_path(path)
            if not node:
                return None
            target = node
        
        if not isinstance(target, VFSDirectory):
            return None
        return target.list_contents()

    def cd(self, path: str) -> bool:
        node = self._resolve_path(path)
        if node and isinstance(node, VFSDirectory):
            self.current_dir = node
            logger.debug(f"Changed directory to: {node.get_path()}", component="VFS")
            return True
        logger.error(f"Cannot change to directory: {path}", component="VFS")
        return False

# Instância global (opcional, mas útil para testes rápidos)
vfs = VirtualFileSystem()