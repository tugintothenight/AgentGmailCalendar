from datetime import datetime
from typing import Dict, Any, List

class UserSession:
    """Class quản lý phiên làm việc, lịch sử chat và bộ nhớ tạm của Agent."""
    
    def __init__(self, chat_id: str, system_instruction: str):
        self.chat_id = chat_id
        self.created_at = datetime.now()
        # Khởi tạo tin nhắn đầu tiên luôn là System Prompt
        self.messages = [
            {"role": "system", "content": system_instruction}
        ]
    
    def add_message(self, role: str, content: str, **kwargs):
        message = {"role": role, "content": content}
        message.update(kwargs)
        self.messages.append(message)
    
    def add_tool_message(self, tool_call_id: str, tool_name: str, content: str):
        self.add_message(
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            name=tool_name
        )
    
    def get_messages(self) -> List[Dict[str, Any]]:
        return self.messages
        
    def clear_history(self, keep_system_prompt: bool = True):
        if keep_system_prompt and len(self.messages) > 0:
            self.messages = [self.messages[0]]
        else:
            self.messages = []
            
    def __repr__(self):
        return f"<UserSession chat_id={self.chat_id} messages={len(self.messages)}>"