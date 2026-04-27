import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
from datetime import datetime, time

from config import TELEGRAM_BOT_TOKEN
from models.session import UserSession
from core.llm_engine import LLMEngine
from core.orchestrator import AgentOrchestrator
from tools.tool_registry import ToolExecutor
from security.pipeline import SecurityPipeline

from memory.hydra_db import HYDRADB_TOOLS
from tools.gmail_services import GMAIL_TOOLS
from tools.calendar_services import CALENDAR_TOOLS

AVAILABLE_TOOLS = HYDRADB_TOOLS + GMAIL_TOOLS + CALENDAR_TOOLS


class TelegramInterface:
    """Class cho phép Agent giao tiếp với user qua Telegram. Chỉ xử lý Message và Nút bấm."""
    
    def __init__(self):
        self.bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
        self.llm_engine = LLMEngine()
        self.tool_executor = ToolExecutor()
        self.security = SecurityPipeline()
        self.orchestrator = AgentOrchestrator(
            llm_engine=self.llm_engine,
            tool_executor=self.tool_executor,
            security_pipeline=self.security
        )
        self.user_sessions = {}
        self.pending_approvals = {}
        self.hitl_counter = 0

        self._register_handlers()

    def _register_handlers(self):
        @self.bot.message_handler(commands=['start', 'reset'])
        def _on_start(message):
            chat_id = str(message.chat.id)
            if chat_id in self.user_sessions:
                self.user_sessions[chat_id].clear_history()
            self.bot.send_message(chat_id, "Đã reset bộ nhớ tạm")

        @self.bot.message_handler(func=lambda message: True)
        def _on_message(message):
            self.handle_message(message)

        @self.bot.callback_query_handler(func=lambda call: True)
        def _on_callback(call):
            self.handle_callback(call)

    def _get_or_create_session(self, chat_id: str) -> UserSession:
        if chat_id not in self.user_sessions:
            time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            day_of_week = datetime.now().strftime("%A")
            system_instruction = f"""You are Mini-Fang, an elite AI Assistant for Sếp.
RULES:
1. Reply in Vietnamese. Call user "Sếp", yourself "em".
2. You MUST USE TOOLS to accomplish tasks.
3. NEVER output raw JSON tool calls in plain text. Use the tool calling mechanism.
4. Time now: {time_now} ({day_of_week})
"""       
            self.user_sessions[chat_id] = UserSession(chat_id, system_instruction)
        return self.user_sessions[chat_id]

    def handle_message(self, message):
        chat_id = str(message.chat.id)
        user_input = message.text
        print(f"\n[User input]: {user_input}")
        
        # L1
        l1_check = self.security.check_prompt_injection(user_input)
        if l1_check.get("status") == "BLOCK":
            self.bot.send_message(chat_id, "xin lỗi, mệnh lệnh có dấu hiệu nguy hiểm")
            return
            
        session = self._get_or_create_session(chat_id)
        session.add_message("user", user_input)
        self.security.reset_circuit_breaker()
        print("\n=== [DEBUG NÃO AI] ===")
        for m in session.messages:
            print(m) 
        print("======================\n")
        msg = self.bot.send_message(chat_id, "🔄...")
        self._run_agent(chat_id, session, msg.message_id)

    def _compress_session(self, session, threshold=15, keep_recent=10):
        """Tóm tắt cuốn chiếu + Cửa sổ trượt dự phòng"""
        # Nếu chưa vượt ngưỡng thì chưa cần làm gì
        if len(session.messages) <= threshold:
            return

        print("\n[Hệ thống] Phát hiện Context quá dài. Đang tiến hành nén...")
        
        system_prompt = session.messages[0]
        recent_messages = session.messages[-keep_recent:] # Giữ nguyên 10 tin mới nhất
        old_messages = session.messages[1:-keep_recent]   # Móc các tin cũ ra để nén
        
        text_to_summarize = ""
        for m in old_messages:
            role = m.get("role", "unknown")
            content = m.get("content", "")
            if content and isinstance(content, str):
                text_to_summarize += f"{role.upper()}: {content}\n"
                
        if not text_to_summarize.strip():
            session.messages = [system_prompt] + recent_messages
            return

        summary_prompt = [
            {"role": "system", "content": "Bạn là chuyên gia lưu trữ ký ức. Tóm tắt cốt lõi đoạn hội thoại sau dưới 80 từ bằng tiếng Việt."},
            {"role": "user", "content": text_to_summarize}
        ]
        
        try:
            # case 1: Gọi LLM Tóm tắt cuốn chiếu
            summary_result = self.llm_engine.generate_response(summary_prompt)
            if summary_result.get("status") == "text":
                compressed_text = summary_result["data"]
            else:
                raise Exception("LLM không trả về văn bản.")
        except Exception as e:
            # case 2: Cửa sổ trượt (Khi mạng lỗi / API sập)
            print(f"[Cảnh báo] Lỗi API nén: {e}. Kích hoạt Cửa sổ trượt bảo vệ RAM!")
            session.messages = [system_prompt] + recent_messages
            return
            
        # Lưu lịch sử vào EPISODIC MEMORY
        try:
            self.tool_executor.hydra_db.store(
                memory_text=f"Tóm tắt cuộc trò chuyện với Sếp: {compressed_text}",
                memory_type="episodic",
                tags=["chat_history", "conversation"]
            )
        except Exception as e:
            print(f"[Lỗi HydraDB] {e}")

        memory_message = {
            "role": "system", 
            "content": f"[KÝ ỨC ĐÃ TÓM TẮT TỪ TRƯỚC]: {compressed_text}"
        }
        
        session.messages = [system_prompt, memory_message] + recent_messages
        print("[Hệ thống] Ép xung trí nhớ thành công!")

    def _run_agent(self, chat_id, session, msg_id):
        self._compress_session(session)
        result = self.orchestrator.execute_loop(session, AVAILABLE_TOOLS)
        
        if result["status"] == "success":
            self.bot.edit_message_text(result["message"], chat_id, msg_id)
            
        elif result["status"] == "pending_approval":
            self.bot.edit_message_text("Cần phê duyệt để đi tiếp:", chat_id, msg_id)
            pending_tools = result.get("pending_tools", [])

            for pt in pending_tools:
                self._create_approval_request(chat_id, pt["name"], pt["params"], pt["id"])
                
        elif result["status"] == "error":
            self.bot.edit_message_text(f"Lỗi Hệ Thống: {result['message']}", chat_id, msg_id)

    def _create_approval_request(self, chat_id: str, tool_name: str, parameters: dict, tool_call_id: str):
        """Vẽ nút bấm HITL"""
        self.hitl_counter += 1
        safe_id = str(self.hitl_counter)
        
        self.pending_approvals[safe_id] = {
            "tool_name": tool_name,
            "params": parameters,
            "tool_call_id": tool_call_id
        }
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✅", callback_data=f"HITL_YES_{safe_id}"),
            InlineKeyboardButton("❌", callback_data=f"HITL_NO_{safe_id}")
        )
        
        self.bot.send_message(
            chat_id,
            f"**YÊU CẦU QUYỀN TRUY CẬP**\nTool: `{tool_name}`\nTham số: `{json.dumps(parameters, ensure_ascii=False)}`",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    def handle_callback(self, call):
        chat_id = str(call.message.chat.id)
        
        try: self.bot.answer_callback_query(call.id)
        except: pass
            
        data = call.data
        if not data.startswith("HITL_"): return
        
        action = "YES" if "YES" in data else "NO"
        safe_id = data.split("_")[-1]
        
        try: self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        except: pass
        
        if safe_id not in self.pending_approvals:
            self.bot.send_message(chat_id, "Nút này đã hết hạn. Vui lòng nhắn lại lệnh.")
            return
            
        approval = self.pending_approvals.pop(safe_id)
        session = self._get_or_create_session(chat_id)
        
        if action == "NO":
            self.bot.send_message(chat_id, f"Đã chặn Tool: `{approval['tool_name']}`.")
            session.add_tool_message(approval['tool_call_id'], approval['tool_name'], json.dumps({"error": "Đã bị từ chối quyền."}))
        else:
            self.bot.send_message(chat_id, f"Đã duyệt! Đang chạy Tool: `{approval['tool_name']}`...")
            result = self.tool_executor.execute(approval['tool_name'], approval['params'])
            session.add_tool_message(approval['tool_call_id'], approval['tool_name'], result.to_json_string())
            
        msg = self.bot.send_message(chat_id, "🔄 Đang tổng hợp kết quả...")
        
        self._run_agent(chat_id, session, msg.message_id)

    def start(self):
        print("----HỆ ĐIỀU HÀNH ĐÃ KHỞI ĐỘNG----")
        self.bot.infinity_polling(timeout=10, long_polling_timeout=5)