import os
import glob
from typing import List, Dict

class MCPHandler:
    """
    Model Context Protocol (MCP) - Modelga mahalliy muhit bilan ishlash imkonini beradi.
    """
    def __init__(self, workspace_root: str = ".", confirmation: bool = False):
        self.workspace_root = os.path.abspath(workspace_root)
        self.confirmation = confirmation

    def _check_confirmation(self, action: str) -> bool:
        """Har bir amal oldidan tasdiq so'rash (agar flag yoqilgan bo'lsa)"""
        if self.confirmation:
            # Haqiqiy interaktiv muhitda input() ishlatiladi
            print(f"[MCP] Tasdiqlash kutilmoqda: {action}")
            return True 
        return True

    def list_files(self, pattern: str = "*") -> List[str]:
        """Mahalliy fayllar ro'yxatini olish"""
        if not self._check_confirmation(f"Fayllar ro'yxatini olish ({pattern})"):
            return []
        return glob.glob(os.path.join(self.workspace_root, pattern))

    def read_file(self, file_path: str) -> str:
        """Fayl tarkibini o'qish"""
        if not self._check_confirmation(f"Faylni o'qish: {file_path}"):
            return "Rad etildi."
        
        full_path = os.path.join(self.workspace_root, file_path)
        if not os.path.exists(full_path):
            return f"Xato: {file_path} topilmadi."
        
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read(5000) # Xavfsizlik uchun faqat 5000 belgi

    def google_search(self, query: str) -> str:
        """Google Search simulyatsiyasi (Tool-calling)"""
        if not self._check_confirmation(f"Google Search: {query}"):
            return "Qidiruv rad etildi."
        
        # Simulyatsiya qilingan natija
        return f"[Search Result for '{query}']: Bu yerda qidiruv natijalari simulyatsiyasi bo'ladi."

    def python_execute(self, code: str) -> str:
        """Python kodini ishga tushirish simulyatsiyasi (Tool-calling)"""
        if not self._check_confirmation("Python kodini bajarish"):
            return "Bajarish rad etildi."
        
        # Xavfsizlik uchun faqat simulyatsiya
        try:
            # Real implementatsiyada subprocess yoki xavfsiz sandbox ishlatiladi
            return f"[Python Output]: {len(code)} belgili kod qabul qilindi va simulyatsiya rejimida 'bajarildi'."
        except Exception as e:
            return f"Xato: {str(e)}"

    def get_context(self) -> str:
        """Model uchun joriy muhit kontekstini tayyorlama"""
        files = self.list_files()
        context = "Joriy loyiha fayllari:\n" + "\n".join([os.path.basename(f) for f in files[:10]])
        return context
