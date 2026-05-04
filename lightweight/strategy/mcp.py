import os
import glob
from typing import List, Dict

class MCPHandler:
    """
    Model Context Protocol (MCP) - Modelga mahalliy muhit bilan ishlash imkonini beradi.
    """
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = os.path.abspath(workspace_root)

    def list_files(self, pattern: str = "*") -> List[str]:
        """Mahalliy fayllar ro'yxatini olish"""
        return glob.glob(os.path.join(self.workspace_root, pattern))

    def read_file(self, file_path: str) -> str:
        """Fayl tarkibini o'qish"""
        full_path = os.path.join(self.workspace_root, file_path)
        if not os.path.exists(full_path):
            return f"Xato: {file_path} topilmadi."
        
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read(5000) # Xavfsizlik uchun faqat 5000 belgi

    def get_context(self) -> str:
        """Model uchun joriy muhit kontekstini tayyorlash"""
        files = self.list_files()
        context = "Joriy loyiha fayllari:\n" + "\n".join([os.path.basename(f) for f in files[:10]])
        return context
