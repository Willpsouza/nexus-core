import datetime
import pickle
import os
from typing import Dict, List, Optional, Any
from utils.logger import logger

DISK_FILE = "nexus_disk.img"

class VFSNodeType:
    FILE = "FILE"
    DIRECTORY = "DIRECTORY"

class VFSNode:
    def __init__(self, name: str, node_type: str, parent: Optional['VFSDirectory'] = None):
        self.name = name
        self.node_type = node_type
        self.parent = parent
        self.created_at = datetime.datetime.now()

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
        self.content = data
        return True

    def read(self) -> bytes:
        return self.content

class VFSDirectory(VFSNode):
    def __init__(self, name: str, parent: Optional['VFSDirectory'] = None):
        super().__init__(name, VFSNodeType.DIRECTORY, parent)
        self.children: Dict[str, VFSNode] = {}

    def add_node(self, node: VFSNode) -> bool:
        if node.name in self.children: return False
        node.parent = self
        self.children[node.name] = node
        return True

    def remove_node(self, name: str) -> bool:
        if name not in self.children: return False
        del self.children[name]
        return True

    def get_node(self, name: str) -> Optional[VFSNode]:
        return self.children.get(name)

    def list_contents(self) -> List[str]:
        return list(self.children.keys())

class VirtualFileSystem:
    def __init__(self):
        self.root = VFSDirectory("")
        self.current_dir: VFSDirectory = self.root
        self._disk_loaded = False
        
        # Tenta carregar do disco imediatamente
        if os.path.exists(DISK_FILE):
            self.load_state()
        else:
            logger.info("No existing disk image found. Starting fresh.", component="DISK")
            
        logger.info("VFS initialized", component="VFS")

    def _resolve_path(self, path: str) -> Optional[VFSNode]:
        if path == "/": return self.root

        # Caminho absoluto
        if path.startswith('/'):
            current = self.root
            parts = [p for p in path.split('/') if p]
        else:
            # Caminho relativo
            current = self.current_dir
            parts = [p for p in path.split('/') if p]

        for part in parts:
            if part == "..":
                if current.parent: current = current.parent
            elif part == ".":
                continue
            else:
                if isinstance(current, VFSDirectory):
                    node = current.get_node(part)
                    if node: current = node
                    else: return None
                else: return None
        return current

    def mkdir(self, path: str) -> bool:
        path = path.strip('/')
        if not path:
            return False
        parts = [p for p in path.split('/') if p and p != '.']
        if not parts:
            return False

        # Traverse or create intermediate directories
        current = self.current_dir
        for part in parts[:-1]:
            if part == '..':
                if current.parent:
                    current = current.parent
                else:
                    return False
            else:
                node = current.get_node(part)
                if node:
                    if not isinstance(node, VFSDirectory):
                        return False  # A file exists with this name
                    current = node
                else:
                    # Auto-create intermediate directories
                    new_dir = VFSDirectory(part)
                    current.add_node(new_dir)
                    current = new_dir

        # Create the final directory
        name = parts[-1]
        if current.get_node(name):
            return False  # Already exists
        current.add_node(VFSDirectory(name))
        return True

    def touch(self, path: str) -> bool:
        path = path.strip('/')
        if not path:
            return False
        parts = [p for p in path.split('/') if p and p != '.']
        if not parts:
            return False

        # Traverse to parent directory
        current = self.current_dir
        for part in parts[:-1]:
            if part == '..':
                if current.parent:
                    current = current.parent
                else:
                    return False
            else:
                node = current.get_node(part)
                if node:
                    if not isinstance(node, VFSDirectory):
                        return False  # A file exists with this name
                    current = node
                else:
                    return False  # Parent directory doesn't exist

        # Create the file
        name = parts[-1]
        if current.get_node(name):
            return False  # Already exists
        current.add_node(VFSFile(name))
        return True

    def ls(self, path: str = ".") -> List[str]:
        target = self.current_dir if path == "." else self._resolve_path(path)
        if target and isinstance(target, VFSDirectory):
            return target.list_contents()
        return []

    def cd(self, path: str) -> bool:
        target = self._resolve_path(path)
        if target and isinstance(target, VFSDirectory):
            self.current_dir = target
            return True
        return False

    def cat(self, path: str) -> Optional[bytes]:
        node = self._resolve_path(path)
        if node and isinstance(node, VFSFile):
            return node.read()
        return None

    def rm(self, path: str) -> bool:
        node = self._resolve_path(path)
        if node and node.parent:
            return node.parent.remove_node(node.name)
        return False

    # --- Persistência (Disk Driver) ---
    
    def _serialize_node(self, node: VFSNode) -> dict:
        """Converte a árvore de nós em um dicionário salvável"""
        data = {
            'name': node.name,
            'type': node.node_type,
            'created': node.created_at,
            'children': {}
        }
        if isinstance(node, VFSFile):
            data['content'] = node.content
        
        if isinstance(node, VFSDirectory):
            for name, child in node.children.items():
                data['children'][name] = self._serialize_node(child)
                
        return data

    def _deserialize_node(self, data: dict, parent: Optional[VFSDirectory] = None) -> VFSNode:
        """Reconstrói a árvore de nós a partir do dicionário"""
        if data['type'] == VFSNodeType.FILE:
            node = VFSFile(data['name'], parent)
            node.content = data.get('content', b"")
            node.created_at = data.get('created', datetime.datetime.now())
        else:
            node = VFSDirectory(data['name'], parent)
            node.created_at = data.get('created', datetime.datetime.now())
            for child_data in data.get('children', {}).values():
                child_node = self._deserialize_node(child_data, node)
                node.children[child_node.name] = child_node
        return node

    def save_state(self):
        """Salva a estrutura atual no disco"""
        try:
            # Precisamos resetar o current_dir para a raiz antes de salvar para garantir consistência
            # ou salvar o caminho atual também. Para simplificar, salvamos a árvore toda da raiz.
            root_data = self._serialize_node(self.root)
            
            with open(DISK_FILE, 'wb') as f:
                pickle.dump(root_data, f)
            
            logger.info(f"Disk saved: {DISK_FILE}", component="DISK")
        except Exception as e:
            logger.error(f"Failed to save disk state: {e}", component="DISK")

    def load_state(self):
        """Carrega a estrutura do disco"""
        try:
            with open(DISK_FILE, 'rb') as f:
                root_data = pickle.load(f)
            
            self.root = self._deserialize_node(root_data)
            self.current_dir = self.root # Reset para raiz ao carregar
            self._disk_loaded = True
            logger.info("Disk state loaded successfully.", component="DISK")
        except Exception as e:
            logger.error(f"Failed to load disk state: {e}", component="DISK")
            self.root = VFSDirectory("")
            self.current_dir = self.root

    # --- Métodos Auxiliares para o Shell ---
    def create_directory(self, name: str) -> bool: return self.mkdir(name)
    def create_file(self, name: str) -> bool: return self.touch(name)
    def list_directory(self, path: str = ".") -> list: return self.ls(path)
    def get_current_path(self) -> str: 
        path = []
        curr = self.current_dir
        while curr.parent is not None:
            path.append(curr.name)
            curr = curr.parent
        return "/" + "/".join(reversed(path)) if path else "/"
    
    def read_file(self, path: str) -> Optional[str]:
        data = self.cat(path)
        return data.decode('utf-8') if data else None
    
    def remove(self, name: str) -> bool: return self.rm(name)