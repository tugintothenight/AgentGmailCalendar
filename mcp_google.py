from mcp.server.fastmcp import FastMCP
from gmail_services import GmailService
from calendar_services import CalendarService
import logging
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
mcp = FastMCP("agentGS")

gmail_svc = GmailService()
calendar_svc = CalendarService()

@mcp.tool()
def fetch_raw_emails(num_emails: int) -> str:
    """
    Công cụ này trích xuất nội dung các email chưa đọc mới nhất.
    Hãy sử dụng công cụ này để lấy dữ liệu, sau đó phân tích và tóm tắt và trả lời những gì lấy được.
    Args:
        num_emails: Số lượng email tối đa cần lấy.
    """
    return gmail_svc.get_new_emails(num_emails)

@mcp.tool()
def schedule_event(title: str, start_time: str, end_time: str, attendees: list[str] = None) -> str:
    """Tạo sự kiện trên Google Calendar.
    Args:
            title: Tiêu đề sự kiện.
            start_time: Thời gian bắt đầu. BẮT BUỘC phải theo định dạng ISO 8601 (Ví dụ: 2026-03-19T09:00:00).
            end_time: Thời gian kết thúc. BẮT BUỘC phải theo định dạng ISO 8601 (Ví dụ: 2026-03-19T12:00:00).
            attendees: Danh sách email người tham gia (Ví dụ: ["nguyenvana@gmail.com", "tranvanb@gmail.com"]). Nếu không có ai, truyền mảng rỗng [].
    """
    return calendar_svc.create_calendar_event(title, start_time, end_time, attendees)

if __name__ == "__main__":
    mcp.run()