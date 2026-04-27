import base64
import re
from googleapiclient.discovery import build
from .google_client import get_google_credentials

class GmailService:
    """Dịch vụ này sẽ kết nối Gmail và lấy nội dung email thô."""
    def __init__(self):
        self.creds = get_google_credentials()
        self.service = build('gmail', 'v1', credentials=self.creds)

    def decode_email_body(self, payload):
        body_text = ""
        if 'parts' in payload:
            for part in payload['parts']:
                body_text += self.decode_email_body(part)
        else:
            mime_type = payload.get('mimeType')
            if mime_type in ['text/plain', 'text/html']:
                data = payload.get('body', {}).get('data')
                if data:
                    data += "=" * ((4 - len(data) % 4) % 4)
                    decoded_bytes = base64.urlsafe_b64decode(data)
                    text = decoded_bytes.decode('utf-8', errors='ignore')
                    if mime_type == 'text/html':
                        text = re.sub('<[^<]+?>', ' ', text)
                        text = re.sub(r'\s+', ' ', text).strip()
                    body_text += text + " "
        return body_text

    def get_new_emails(self, n: int = 5) -> str:
        """Chỉ lấy email thô"""
        results = self.service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=n).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return "Không có email mới nào."

        output = "Dữ liệu email thô:\n---\n"
        for i, msg in enumerate(messages):
            msg_detail = self.service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = msg_detail['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Không tiêu đề')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Không rõ')
            content = self.decode_email_body(msg_detail['payload'])
            output += f"Email {i+1}:\n- Người gửi: {sender}\n- Tiêu đề: {subject}\n- Nội dung: {content}\n- yêu cầu: Tóm tắt raw email, đưa ra đề xuất, lời khuyên nếu cần--\n"
            self.service.users().messages().modify(userId='me', id=msg['id'], body={'removeLabelIds': ['UNREAD']}).execute()
        return output

    def get_email_by_keyword(self, keyword: str, n: int = 5) -> str:
        """Tìm email theo từ khóa trong tiêu đề hoặc nội dung."""
        results = self.service.users().messages().list(userId='me', labelIds=['INBOX'], q=keyword, maxResults=n).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return f"Không tìm thấy email nào chứa từ khóa '{keyword}'."

        output = f"Dữ liệu email chứa từ khóa '{keyword}':\n---\n"
        for i, msg in enumerate(messages):
            msg_detail = self.service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = msg_detail['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Không tiêu đề')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Không rõ')
            content = self.decode_email_body(msg_detail['payload'])
            output += f"Email {i+1}:\n- Người gửi: {sender}\n- Tiêu đề: {subject}\n- Nội dung: {content}\n---\n"
        return output

GMAIL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_raw_emails",
            "description": "Lấy nội dung các email chưa đọc mới nhất hoặc tìm kiếm email theo từ khóa.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string", 
                        "description": "Từ khóa tìm kiếm email (Ví dụ: tên người gửi, chủ đề). Bỏ trống nếu muốn lấy email mới nhất."
                    },
                    "num_emails": {
                        "type": "integer", 
                        "description": "Số lượng email tối đa cần lấy. Mặc định là 5."
                    }
                }
            }
        }
    }
]
