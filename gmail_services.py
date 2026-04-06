import base64
import re
from googleapiclient.discovery import build
from google_client import get_google_credentials

class GmailService:
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
            output += f"Email {i+1}:\n- Người gửi: {sender}\n- Tiêu đề: {subject}\n- Nội dung: {content}\n---\n"
            self.service.users().messages().modify(userId='me', id=msg['id'], body={'removeLabelIds': ['UNREAD']}).execute()
        return output

    
if __name__ == "__main__":
    gmail_service = GmailService()
    print(gmail_service.get_new_emails(3))