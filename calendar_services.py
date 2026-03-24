from googleapiclient.discovery import build
from google_client import get_google_credentials

class CalendarService:
    """Dịch vụ này sẽ kết nối Google Calendar và tạo sự kiện."""
    def __init__(self):
        creds = get_google_credentials()
        self.service = build('calendar', 'v3', credentials=creds)

    def create_calendar_event(self, title, start_time, end_time, attendees=None):
        """Tạo sự kiện trên Google Calendar."""
        attendees_list = []
        if attendees:
            for email in attendees:
                attendees_list.append({'email': email})
        event = {
            'summary': title,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Asia/Ho_Chi_Minh',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Asia/Ho_Chi_Minh',
            },
            'attendees': attendees_list,
        }

        try:
            event_result = self.service.events().insert(calendarId='primary', body=event).execute()
            event_link = event_result.get('htmlLink')
            return f"Đã lên lịch thành công: {title}. Xem chi tiết tại: {event_link}"
        except Exception as e:
            return f"Đã xảy ra lỗi khi tạo lịch: {e}"
        
if __name__ == "__main__":
    print("calendar")