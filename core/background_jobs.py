import re

from apscheduler.schedulers.background import BackgroundScheduler
from models.session import UserSession
from config import GAP_AUTO_RUN, AUTO_CHECK_MAIL


class BackgroundJobManager:
    """Class quản lý các tác vụ chạy ngầm và lịch trình"""
    
    def __init__(self, orchestrator, bot_interface, available_tools):
        self.orchestrator = orchestrator
        self.bot_interface = bot_interface
        self.tools = available_tools
        self.scheduler = BackgroundScheduler()
        
    def start(self):
        if AUTO_CHECK_MAIL == False:
            return
        print(f"[Background] Đã kích hoạt lịch trình tự động check mail {GAP_AUTO_RUN} phút/lần.")
        self.auto_check_gmail()
        self.scheduler.add_job(
            self.auto_check_gmail, 
            'interval', 
            minutes=GAP_AUTO_RUN, 
            id='check_gmail_job'
        )
        self.scheduler.start()
        
    def auto_check_gmail(self):
        print("\n--- [Background] 🔄 Đang tự động kiểm tra Gmail...")
        from config import ADMIN_CHAT_ID 
        chat_id = ADMIN_CHAT_ID
        # Tạo một Session tạm thời
        system_prompt = """You are a background agent. 
        Task: 
        1. Check the latest emails, Determine whether it is an important email, an advertisement, or spam.
        if there is anything important, summarize the report. 
        If email content NEED schedule and just ONLY email content NEED schedule, add text below your answer 
        with <b></b> tag to ask sếp to allow scheduling. DO NOT add scheduling suggestion if the email does not require scheduling.
        2. Use hydradb_retrieve after checking emails.
        3. Always report in Vietnamese. 
        4. If there is nothing, say exactly 'none'."""
        session = UserSession(chat_id, system_prompt)
        session.add_message("user", "Kiểm tra 1 email mới nhất của tôi.")

        try:
            result = self.orchestrator.execute_loop(session, self.tools)
            if result["status"] == "success":
                report = result["message"]
                report = re.sub(r'<([^<>]+@[^<>]+)>', r'&lt;\1&gt;', report) # lọc email để tránh nhận <email> thành tag trong html
                
                if "none" not in report.strip().lower():
                    # if any(kw in report.lower() for kw in ["meeting", "họp", "gặp mặt", "deadline"]):
                    #     report += '\n\n<b>Sếp có muốn em đặt lịch giúp theo email này không?</b>'
                    final_msg = f"**[Email mới]**\n\n{report}"
                    self.bot_interface.bot.send_message(chat_id, final_msg, parse_mode="HTML")
                    main_session = self.bot_interface._get_or_create_session(chat_id)
                    main_session.add_message("assistant",  final_msg)
                    print("[Background] Đã gửi báo cáo email mới.")
                else:
                    print("[Background] Không có email quan trọng nào mới.")
            
        except Exception as e:
            print(f"[Background] Lỗi khi chạy job tự động: {e}")