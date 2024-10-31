import time
import io
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2 import service_account
from googleapiclient.discovery import build
from util.commands import db_path

credentials = service_account.Credentials.from_service_account_file('service-account.json')
drive_service = build('drive', 'v3', credentials=credentials)


    # Function to download the database file from Google Drive
def download_database():
    file_id = 'YOUR_FILE_ID'  # Replace 'YOUR_FILE_ID' with the ID of your database file on Google Drive
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download database from Google Drive: %d%%." % int(status.progress() * 100))
    with open(db_path, 'wb') as f:
        f.write(fh.getbuffer())
      
        
    #
def replace_list_db_on_google_drive():
    while True:    
        SCOPES = ['https://www.googleapis.com/auth/drive']
        SERVICE_ACCOUNT_FILE = 'service-account.json' 

        credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        drive_service = build('drive', 'v3', credentials=credentials)

        # Replace 'YOUR_FILE_ID' with the ID of the existing list.db file on Google Drive
        file_id = 'YOUR_FILE_ID'

        media = MediaFileUpload(db_path, resumable=True)

        drive_service.files().update(fileId=file_id, media_body=media).execute()

        print('Database file on Google Drive has been updated.')
        
        n = 60 * 10  # Sleep for n seconds before the next update

        time.sleep(n)
          
