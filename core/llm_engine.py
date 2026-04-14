import os
from openai import OpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, LLM_MODEL


class LLMEngine:
    """Class giao tiếp với LLM qua API."""
    
    def __init__(self):
        self.client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )
        self.model = LLM_MODEL

    def generate_response(self, messages: list, tools: list = None) -> dict:
        print("[LLM Engine] Đang kết nối LLM ...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                temperature=0.7,
            )
            
            ai_message = response.choices[0].message
            
            # Nếu LLM gọi Tool, trả về trạng thái tool_call
            if ai_message.tool_calls and len(ai_message.tool_calls) > 0:
                print(f"[LLM Engine] LLM gọi {len(ai_message.tool_calls)} công cụ.")
                return {
                    "status": "tool_call", 
                    "data": ai_message.tool_calls,
                    "message_obj": ai_message
                }
            
            # Nếu LLM không gọi tool,trả lời văn bản bình thường
            content = ai_message.content.strip() if ai_message.content else ""
            print(f"[LLM Engine] Phản hồi văn bản: {content[:50]}...")
            return {
                "status": "text", 
                "data": content,
                "message_obj": ai_message
            }
            
        except Exception as e:
            print(f"[LLM Engine] LỖI API: {e}")
            return {"status": "error", "data": str(e)}