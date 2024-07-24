import os
import base64
import datetime
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class GoogleDriveUploader:
    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(self, credentials_file="credentials.json", token_file="token.pickle"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = self.authenticate_user()

    def authenticate_user(self):
        """Authenticates the user with OAuth 2.0 and returns the Drive service object."""
        creds = None
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                try:
                    creds = pickle.load(token)
                except (pickle.PickleError, EOFError, IOError) as e:
                    print(f"Error loading token file: {e}")
                    creds = None
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing credentials: {e}")
                    creds = None
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        service = build('drive', 'v3', credentials=creds)
        return service

    def find_folder(self, folder_name, parent_id='root'):
        """Finds a folder by name and returns its ID."""
        query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        if items:
            return items[0]['id']
        return None

    def create_folder(self, folder_name, parent_id='root'):
        """Creates a folder in Google Drive and returns its ID."""
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        try:
            response = self.service.files().create(body=folder_metadata, fields='id').execute()
            return response.get('id')
        except HttpError as error:
            print(f"An error occurred creating folder {folder_name}: {error}")
            return None

    def find_file_in_folder(self, folder_id, file_name):
        """Finds a file by name within a folder and returns its ID."""
        query = f"'{folder_id}' in parents and name='{file_name}' and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        if items:
            return items[0]['id']
        return None

    def upload_file(self, file_path, parent_id='root'):
        """Uploads a file to Google Drive."""
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [parent_id]
        }
        media = MediaFileUpload(file_path, resumable=True)
        try:
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return file.get('id')
        except HttpError as error:
            print(f"An error occurred uploading file {file_path}: {error}")
            return None

    def update_file(self, file_path, file_id):
        """Updates a file in Google Drive."""
        media = MediaFileUpload(file_path, resumable=True)
        try:
            file = self.service.files().update(fileId=file_id, media_body=media).execute()
            return file.get('id')
        except HttpError as error:
            print(f"An error occurred updating file {file_path}: {error}")
            return None

    def upload_folder(self, folder_path, parent_id='root'):
        """Uploads an entire folder to Google Drive."""
        folder_name = os.path.basename(folder_path)
        folder_id = self.find_folder(folder_name, parent_id)
        if not folder_id:
            folder_id = self.create_folder(folder_name, parent_id)
            if not folder_id:
                print(f"Failed to create or find folder: {folder_name}")
                return None

        for root, _, files in os.walk(folder_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                file_id = self.find_file_in_folder(folder_id, file_name)
                if file_id:
                    file_id = self.update_file(file_path, file_id)
                    if file_id:
                        print(f"File '{file_name}' updated successfully.")
                    else:
                        print(f"Failed to update file: {file_name}")
                else:
                    file_id = self.upload_file(file_path, folder_id)
                    if file_id:
                        print(f"File '{file_name}' uploaded successfully.")
                    else:
                        print(f"Failed to upload file: {file_name}")

        return folder_id


class GoogleCalendarAPI:
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly", 
              "https://www.googleapis.com/auth/calendar",
              "https://www.googleapis.com/auth/gmail.send"]

    def __init__(self, credentials_file="credentials.json", token_file="token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file

    def authenticate(self):
        """Authenticates the user and generates or loads credentials."""
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError as e:
                    print(f"Error refreshing credentials: {e}")
                    return None
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())
        return creds

    def get_busy_times(self):
        """Gets the busy times on the user's calendar for the next 24 hours."""
        creds = self.authenticate()
        if not creds:
            print("Failed to authenticate.")
            return
        
        service = build("calendar", "v3", credentials=creds)

        now = datetime.datetime.utcnow()
        start_time = now.isoformat() + "Z"  # 'Z' indicates UTC time
        end_time = (now + datetime.timedelta(days=1)).isoformat() + "Z"

        body = {
            "timeMin": start_time,
            "timeMax": end_time,
            "items": [{"id": "primary"}]
        }

        try:
            events_result = service.freebusy().query(body=body).execute()
            calendars = events_result.get("calendars", {})
            for calendar_id, info in calendars.items():
                busy_times = info.get("busy", [])
                if not busy_times:
                    print(f"No busy times found for calendar {calendar_id}.")
                else:
                    print(f"Busy times for calendar {calendar_id}:")
                    for busy_time in busy_times:
                        print(f" - Start: {busy_time['start']}, End: {busy_time['end']}")
        except HttpError as error:
            print(f"An error occurred: {error}")

    def create_event(self, email, summary, description, start_datetime, end_datetime):
        """Creates an event on the user's calendar and sends an invite via email."""
        creds = self.authenticate()
        if not creds:
            print("Failed to authenticate.")
            return

        service = build("calendar", "v3", credentials=creds)

        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': 'UTC',
            },
            'attendees': [
                {'email': email},
            ],
        }

        try:
            event = service.events().insert(calendarId='primary', body=event).execute()
            print(f"Event created: {event.get('htmlLink')}")
            self.send_event_invite(email, summary, description, start_datetime, end_datetime)
        except HttpError as error:
            print(f"An error occurred: {error}")

    def send_event_invite(self, email, summary, description, start_datetime, end_datetime):
        """Sends an event invitation to the specified email via Gmail."""
        creds = self.authenticate()
        if not creds:
            print("Failed to authenticate.")
            return

        service = build("gmail", "v1", credentials=creds)

        message = self.create_message(email, summary, description, start_datetime, end_datetime)
        
        try:
            message = service.users().messages().send(userId="me", body=message).execute()
            print(f"Invite sent. Message ID: {message['id']}")
        except HttpError as error:
            print(f"An error occurred: {error}")

    def create_message(self, email, summary, description, start_datetime, end_datetime):
        """Creates a message for sending event invite via Gmail."""
        message = MIMEMultipart('mixed')
        message['to'] = email
        message['subject'] = f"Invite: {summary}"
        message['from'] = "your-email@example.com"

        # Create MIMEText for the invitation
        invitation = MIMEMultipart('alternative')
        
        ical_body = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//Google Inc//Google Calendar 70.9054//EN\r\n"
            "BEGIN:VEVENT\r\n"
            f"SUMMARY:{summary}\r\n"
            f"DESCRIPTION:{description}\r\n"
            f"DTSTART:{start_datetime.strftime('%Y%m%dT%H%M%SZ')}\r\n"
            f"DTEND:{end_datetime.strftime('%Y%m%dT%H%M%SZ')}\r\n"
            "STATUS:CONFIRMED\r\n"
            "SEQUENCE:0\r\n"
            "BEGIN:VALARM\r\n"
            "ACTION:DISPLAY\r\n"
            "DESCRIPTION:This is an event reminder\r\n"
            "TRIGGER:-PT15M\r\n"
            "END:VALARM\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )
        
        ical_text_part = MIMEText(ical_body, 'calendar', 'utf-8')
        ical_text_part['Content-Class'] = 'urn:content-classes:calendarmessage'
        ical_text_part['Content-Type'] = 'text/calendar; method=REQUEST'
        ical_text_part['Content-Transfer-Encoding'] = '8bit'
        ical_text_part['Content-Disposition'] = 'inline; filename="invite.ics"'

        invitation.attach(ical_text_part)
        
        # Attach the invitation to the main message
        message.attach(invitation)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw}


if __name__ == "__main__":
    # Inicialize o uploader do Google Drive
    drive_uploader = GoogleDriveUploader()

    # Caminho da pasta a ser carregada
    folder_path = "folder path"

    # Carregar a pasta e obter o ID da pasta no Google Drive
    folder_id = drive_uploader.upload_folder(folder_path)
    
    if folder_id:
        folder_link = f"https://drive.google.com/drive/folders/{folder_id}"
        print(f"Folder uploaded successfully. Link: {folder_link}")

        # Inicialize a API do Google Calendar
        calendar_api = GoogleCalendarAPI()
        calendar_api.get_busy_times()

        email = "email destinatário"
        summary = os.path.basename(folder_path)  # Nome do evento será o nome da pasta
        description = f"Link para a pasta no Google Drive: {folder_link}"
        start_datetime = datetime.datetime(2024, 7, 23, 10, 0, 0)  # Ano, Mês, Dia, Hora, Minuto, Segundo
        end_datetime = datetime.datetime(2024, 7, 23, 11, 0, 0)    # Ano, Mês, Dia, Hora, Minuto, Segundo

        calendar_api.create_event(email, summary, description, start_datetime, end_datetime)
    else:
        print("Failed to upload folder.")
