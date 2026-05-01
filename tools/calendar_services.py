from googleapiclient.discovery import build
from .google_client import get_google_credentials

class CalendarService:
    """Dịch vụ này sẽ kết nối Google Calendar và tạo sự kiện."""
    def __init__(self):
        creds = get_google_credentials()
        self.service = build('calendar', 'v3', credentials=creds)

    def create_calendar_event(self, title, start_time, end_time):
        """Tạo sự kiện trên Google Calendar."""
        event = {
            'summary': title,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Asia/Ho_Chi_Minh',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Asia/Ho_Chi_Minh',
            }
        }

        try:
            event_result = self.service.events().insert(calendarId='primary', body=event).execute()
            event_link = event_result.get('htmlLink')
            return f"Đã lên lịch thành công: {title}. Xem chi tiết tại: {event_link}"
        except Exception as e:
            return f"Đã xảy ra lỗi khi tạo lịch: {e}"
        
CALENDAR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "schedule_event",
            "description": "Tạo sự kiện trên Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "tiêu đề bằng tiếng anh"},
                    "start_time": {"type": "string", "description": "Thời gian bắt đầu, không được tự đoán mò. BẮT BUỘC định dạng ISO 8601 (VD: 2026-08-14T09:00:00)."},
                    "end_time": {"type": "string", "description": "Thời gian kết thúc, không được tự đoán mò. BẮT BUỘC định dạng ISO 8601 (VD: 2026-08-14T12:00:00)."}
                },
                "required": ["title"]
            }
        }
    }
]