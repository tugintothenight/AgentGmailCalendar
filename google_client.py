import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar'
]

def get_google_credentials():
    """Hàm này lấy và trả về thông tin xác thực của Google."""
    creds = None
    if os.path.exists('D:/openfangAgentGS/auth/token.json'):
        creds = Credentials.from_authorized_user_file('D:/openfangAgentGS/auth/token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            try:
                if not os.path.exists('D:/openfangAgentGS/auth/credentials.json'):
                    raise FileNotFoundError("credentials.json thiếu gòi")
            except FileNotFoundError as e:
                return None
            # mở trình duyệt để cấp quyền
            flow = InstalledAppFlow.from_client_secrets_file(
                'D:/openfangAgentGS/auth/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('D:/openfangAgentGS/auth/token.json', 'w') as token:
            token.write(creds.to_json())
            
    return creds

if __name__ == "__main__":
    creds = get_google_credentials()
    if creds:
        print("Đã lấy được thông tin xác thực của Google.")
    else:
        print("Không thể lấy thông tin xác thực. Vui lòng kiểm tra lại file credentials.json và token.json.")