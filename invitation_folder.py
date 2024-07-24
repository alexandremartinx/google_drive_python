""" Aplicação utilizando tinker e apis do google para integrar google calendar, gmail e google drive.
Cria uma interface gráfica para inserir os dados a serem integrados, cria uma pasta no google drive com um link,
cria um evento com o link da pasta na descrição e envia um invite para o email selecionado """

import os
import base64
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pickle

class GoogleDriveUploader:
    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(self, credentials_file="credentials.json", token_file="token.pickle"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = self.authenticate_user()

    def authenticate_user(self):
        creds = None
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        return build('drive', 'v3', credentials=creds)

    def create_folder(self, folder_name, parent_id):
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        try:
            folder = self.service.files().create(body=folder_metadata, fields='id, webViewLink').execute()
            return folder.get('id'), folder.get('webViewLink')
        except Exception as error:
            print(f"Erro ao criar pasta: {error}")
            return None, None

    def upload_file(self, file_path, parent_id):
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [parent_id]
        }
        media = MediaFileUpload(file_path, resumable=True)
        try:
            return self.service.files().create(body=file_metadata, media_body=media, fields='id').execute().get('id')
        except Exception as error:
            print(f"Erro ao enviar arquivo: {error}")
            return None

    def upload_folder(self, folder_path, parent_id='root'):
        folder_name = os.path.basename(folder_path)
        folder_id, folder_link = self.create_folder(folder_name, parent_id)
        if not folder_id:
            return None, None

        for root, _, files in os.walk(folder_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                self.upload_file(file_path, folder_id)

        return folder_id, folder_link

class GoogleCalendarAPI:
    SCOPES = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/gmail.send"]

    def __init__(self, credentials_file="credentials.json", token_file="token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file

    def authenticate(self):
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())
        return creds

    def create_event(self, email, summary, description, start_datetime, end_datetime):
        creds = self.authenticate()
        if not creds:
            print("Falha na autenticação.")
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
            'attendees': [{'email': email}],
        }

        try:
            event = service.events().insert(calendarId='primary', body=event).execute()
            print(f"Evento criado: {event.get('htmlLink')}")
            self.send_event_invite(email, summary, description, start_datetime, end_datetime)
        except Exception as error:
            print(f"Erro ao criar evento: {error}")

    def send_event_invite(self, email, summary, description, start_datetime, end_datetime):
        creds = self.authenticate()
        if not creds:
            print("Falha na autenticação.")
            return

        service = build("gmail", "v1", credentials=creds)
        message = self.create_message(email, summary, description, start_datetime, end_datetime)
        try:
            message = service.users().messages().send(userId="me", body=message).execute()
            print(f"Convite enviado. ID da mensagem: {message['id']}")
        except Exception as error:
            print(f"Erro ao enviar convite: {error}")

    def create_message(self, email, summary, description, start_datetime, end_datetime):
        message = MIMEMultipart('mixed')
        message['to'] = email
        message['subject'] = f"Invite: {summary}"
        message['from'] = "alexandremartinx@gmail.com"
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
        message.attach(invitation)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw}

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Integração Google Drive e Calendar")
        self.geometry("400x500")
        self.configure(bg="#f0f0f0")
        self.create_widgets()

    def create_widgets(self):
        self.style = ttk.Style(self)
        self.style.configure("TLabel", background="#f0f0f0", font=("Arial", 12))
        self.style.configure("TEntry", font=("Arial", 10))
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("TCombobox", font=("Arial", 10))

        self.event_name_label = ttk.Label(self, text="Nome do Evento:")
        self.event_name_label.pack(pady=5)
        self.event_name_entry = ttk.Entry(self)
        self.event_name_entry.pack(pady=5)

        self.email_label = ttk.Label(self, text="Email do Destinatário:")
        self.email_label.pack(pady=5)
        self.email_entry = ttk.Entry(self)
        self.email_entry.pack(pady=5)

        self.start_date_label = ttk.Label(self, text="Data de Início:")
        self.start_date_label.pack(pady=5)
        self.start_date_entry = DateEntry(self, date_pattern='dd/mm/yyyy')
        self.start_date_entry.pack(pady=5)

        self.start_time_label = ttk.Label(self, text="Hora de Início:")
        self.start_time_label.pack(pady=5)
        self.start_time_entry = ttk.Combobox(self, values=[f"{h:02d}:00" for h in range(24)])
        self.start_time_entry.pack(pady=5)

        self.end_date_label = ttk.Label(self, text="Data de Término:")
        self.end_date_label.pack(pady=5)
        self.end_date_entry = DateEntry(self, date_pattern='dd/mm/yyyy')
        self.end_date_entry.pack(pady=5)

        self.end_time_label = ttk.Label(self, text="Hora de Término:")
        self.end_time_label.pack(pady=5)
        self.end_time_entry = ttk.Combobox(self, values=[f"{h:02d}:00" for h in range(24)])
        self.end_time_entry.pack(pady=5)

        self.folder_button = ttk.Button(self, text="Escolher Pasta", command=self.choose_folder)
        self.folder_button.pack(pady=10)

        self.submit_button = ttk.Button(self, text="Enviar", command=self.submit)
        self.submit_button.pack(pady=10)

    def choose_folder(self):
        self.folder_path = filedialog.askdirectory()
        if self.folder_path:
            messagebox.showinfo("Pasta Selecionada", f"Pasta selecionada: {self.folder_path}")

    def submit(self):
        if not hasattr(self, 'folder_path') or not self.folder_path:
            messagebox.showerror("Erro", "Selecione uma pasta antes de prosseguir.")
            return
        
        event_name = self.event_name_entry.get()
        recipient_email = self.email_entry.get()
        start_date = self.start_date_entry.get_date()
        end_date = self.end_date_entry.get_date()
        start_time = self.start_time_entry.get()
        end_time = self.end_time_entry.get()

        if not event_name or not recipient_email or not start_time or not end_time:
            messagebox.showerror("Erro", "Por favor, preencha todos os campos.")
            return
        
        start_datetime = datetime.datetime.combine(start_date, datetime.datetime.strptime(start_time, "%H:%M").time())
        end_datetime = datetime.datetime.combine(end_date, datetime.datetime.strptime(end_time, "%H:%M").time())

        drive_uploader = GoogleDriveUploader()
        folder_id, folder_link = drive_uploader.upload_folder(self.folder_path)
        if folder_id:
            messagebox.showinfo("Upload Completo", f"Pasta carregada com ID: {folder_id}")

        calendar_api = GoogleCalendarAPI()
        calendar_api.create_event(recipient_email, event_name, f"Descrição do Evento\n\nLink para a pasta: {folder_link}", start_datetime, end_datetime)
        messagebox.showinfo("Evento Criado", "O evento foi criado e o convite enviado.")

if __name__ == "__main__":
    app = Application()
    app.mainloop()
