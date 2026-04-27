import json
from typing import Any

class ToolExecutionResult:
    """chuẩn hóa kết quả trả về từ mọi Tool"""
    def __init__(self, tool_name: str, success: bool, data: Any = None, error: str = None):
        self.tool_name = tool_name
        self.success = success
        self.data = data
        self.error = error

    def to_json_string(self) -> str:
        if self.success:
            return json.dumps({
                "status": "success",
                "tool": self.tool_name,
                "result": self.data
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "error",
                "tool": self.tool_name,
                "message": self.error
            }, ensure_ascii=False)