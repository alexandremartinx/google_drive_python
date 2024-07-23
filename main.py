from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import os
import pickle

SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveUploader:
    def __init__(self):
        self.service = self.authenticate_user()

    def authenticate_user(self):
        """Authenticates the user with OAuth 2.0 and returns the Drive service object."""
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
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

def main():
    """Main function to authenticate, create a folder and upload files."""
    uploader = GoogleDriveUploader()
    folder_path = "folder path"
    folder_id = uploader.upload_folder(folder_path)
    if folder_id:
        print(f"Folder '{folder_path}' uploaded successfully.")
    else:
        print("Failed to upload the folder.")

if __name__ == "__main__":
    main()