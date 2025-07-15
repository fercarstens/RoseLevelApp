import streamlit as st
from modules.drive_utils import listar_pdfs_en_drive
import pandas as pd


def render(movimientos_df):
    """Lista los PDFs en la carpeta 'Extractos' de Drive y muestra los movimientos asociados a cada PDF."""
    st.title("📑 Visor de PDFs en Google Drive")
    st.caption("Selecciona un PDF de la carpeta 'Extractos' en Drive para ver los movimientos asociados.")

    # Buscar el folder_id de la carpeta Extractos igual que en subir.py
    drive_service = None
    folder_id = None
    try:
        from modules.drive_utils import get_google_drive_service
        drive_service = get_google_drive_service()
        nombre_carpeta = "Extractos"
        parent_id = st.secrets["google"]["drive_folder_id"]
        query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and name='{nombre_carpeta}' and trashed=false"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get('files', [])
        if folders:
            folder_id = folders[0]['id']
    except Exception as e:
        st.warning(f"No se pudo localizar la carpeta 'Extractos' en Drive: {e}")
        return

    if not folder_id:
        st.info("No se encontró la carpeta 'Extractos' en Drive.")
        return

    pdfs = listar_pdfs_en_drive(folder_id)
    if not pdfs:
        st.info("No se encontraron archivos PDF en la carpeta 'Extractos'.")
        return

    pdf_names = [pdf['name'] for pdf in pdfs]
    selected_pdf = st.selectbox("Selecciona un PDF", pdf_names)

    # Mostrar info del PDF seleccionado
    st.write(f"**Archivo seleccionado:** {selected_pdf}")

    # Filtrar movimientos asociados a ese PDF (por columna 'archivo')
    if 'archivo' in movimientos_df.columns:
        movs_pdf = movimientos_df[movimientos_df['archivo'] == selected_pdf]
        if not movs_pdf.empty:
            st.subheader("Movimientos asociados a este PDF")
            columnas = ["fecha", "banco", "descripción", "categoría", "monto", "archivo"]
            for col in columnas:
                if col not in movs_pdf.columns:
                    movs_pdf[col] = ""
            st.dataframe(movs_pdf[columnas], use_container_width=True)
        else:
            st.info("No hay movimientos asociados a este PDF.")
    else:
        st.warning("No se encuentra la columna 'archivo' en los movimientos.")
