import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import streamlit as st

from modules.auth import get_credentials

@st.cache_resource
def get_google_drive_service():
    try:
        scopes = ["https://www.googleapis.com/auth/drive"]
        creds = get_credentials(scopes)
        if creds:
            service = build("drive", "v3", credentials=creds)
            return service
        else:
            return None
    except Exception as e:
        st.error(f"Error al conectar con Google Drive: {e}")
        return None

def crear_carpeta_en_drive(nombre_carpeta, parent_id=None):
    """Crea una carpeta en Google Drive y retorna su ID."""
    try:
        drive_service = get_google_drive_service()
        if not drive_service:
            return False, "Servicio de Drive no disponible"
        file_metadata = {
            'name': nombre_carpeta,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        else:
            file_metadata['parents'] = [st.secrets["google"]["drive_folder_id"]]
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        return True, folder.get('id')
    except Exception as e:
        return False, str(e)


def subir_a_drive(nombre_archivo, contenido_bytes, mimetype, folder_id=None):
    try:
        drive_service = get_google_drive_service()
        if not drive_service:
            return False, "Servicio de Drive no disponible"

        file_metadata = {
            "name": nombre_archivo,
            "parents": [folder_id or st.secrets["google"]["drive_folder_id"]]
        }
        media = MediaIoBaseUpload(io.BytesIO(contenido_bytes), mimetype=mimetype)
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        return True, file.get("id")
    except Exception as e:
        return False, str(e)
