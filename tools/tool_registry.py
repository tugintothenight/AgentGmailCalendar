import json
from typing import Dict, Any
from models.schemas import ToolExecutionResult 

from memory.hydra_db import HydraMemoryDB
from tools.gmail_services import GmailService
from tools.calendar_services import CalendarService
from config import DB_FILE

class ToolExecutor:
    """Quản đốc xưởng: Khởi tạo các Service và điều phối lệnh từ Agent."""
    
    def __init__(self):
        self.hydra_db = HydraMemoryDB(db_path=DB_FILE)
        self.gmail_svc = GmailService()
        self.calendar_svc = CalendarService()
        self.tool_registry = {
            "hydradb_store": self.hydra_db.store,
            "hydradb_retrieve": self.hydra_db.retrieve,
            "fetch_raw_emails": self._wrap_fetch_emails,
            "schedule_event": self._wrap_schedule_event,
        }
        
    def _wrap_fetch_emails(self, keyword: str = None, num_emails: int = 5):
        if keyword: return self.gmail_svc.get_email_by_keyword(keyword, n=num_emails)
        return self.gmail_svc.get_new_emails(n=num_emails)
        
    def _wrap_schedule_event(self, title: str, start_time: str, end_time: str, attendees: list = []):
        return self.calendar_svc.create_calendar_event(title, start_time, end_time, attendees)

    def _validate_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Hàm kiểm tra dữ liệu đầu vào chống sập API"""
        if tool_name == "schedule_event":
            required = ["title", "start_time", "end_time"]
            for field in required:
                if field not in parameters or not parameters[field]:
                    return f"Thiếu thông tin bắt buộc: {field}"
            
            if "T" not in parameters.get("start_time", ""):
                return "Sai định dạng thời gian start_time (Phải là ISO 8601)"
        return None
    
    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Thực thi tool và đóng gói kết quả"""
        print(f"[Tool Executor] ⚙️ Đang chạy {tool_name} với tham số: {parameters}")
        
        if tool_name not in self.tool_registry:
            return ToolExecutionResult(tool_name, False, None, f"Tool '{tool_name}' không tồn tại!")
        
        validation_error = self._validate_parameters(tool_name, parameters)
        if validation_error:
            return ToolExecutionResult(tool_name, False, None, validation_error)
    
        try:
            tool_func = self.tool_registry[tool_name]
            result = tool_func(**parameters)
            
            if isinstance(result, str):
                try: result = json.loads(result)
                except: pass
                
            print(f"[KẾT QUẢ TOOL: {tool_name}]: {str(result)[:300]}...")
            return ToolExecutionResult(tool_name, True, result)
            
        except Exception as e:
            return ToolExecutionResult(tool_name, False, None, f"Lỗi chạy {tool_name}: {str(e)}")