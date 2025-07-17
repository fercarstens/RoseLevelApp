import datetime
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd

from modules.drive_utils import get_google_drive_service, subir_a_drive, crear_carpeta_en_drive
from modules.sheets_utils import (
    get_google_sheets_client, save_to_google_sheets, save_to_unificada, load_movimientos_data
)
from modules.pdf_parser import extract_data_from_pdf
from gspread_dataframe import set_with_dataframe
import hashlib


def get_file_hash(file):
    return hashlib.md5(file.getvalue()).hexdigest()



def render(movimientos_df):
        st.title("📄 Subida de Extractos Bancarios")
        st.caption("Sube uno o varios extractos bancarios en PDF para identificar automáticamente los gastos y clasificarlos por categoría")

        uploaded_files = st.file_uploader(
            "Selecciona uno o varios archivos PDF de extractos bancarios",
            type="pdf",
            accept_multiple_files=True
        )

        if "processed_files" not in st.session_state:
            st.session_state["processed_files"] = set()

        guardar_en_drive = True
        drive_success = 0
        drive_errors = []
        folder_id = None
        # Usar siempre la misma carpeta llamada "Extractos"
        nombre_carpeta = "Extractos"
        from modules.drive_utils import listar_pdfs_en_drive
        # Buscar si ya existe la carpeta "Extractos" en la raíz/unidad compartida
        drive_service = get_google_drive_service()
        folder_id = None
        if drive_service:
            # Buscar carpeta con ese nombre
            parent_id = st.secrets["google"]["drive_folder_id"]
            query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and name='{nombre_carpeta}' and trashed=false"
            results = drive_service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
            else:
                ok, folder_id_or_msg = crear_carpeta_en_drive(nombre_carpeta)
                if ok:
                    folder_id = folder_id_or_msg
                else:
                    st.warning(f"No se pudo crear la carpeta en Drive: {folder_id_or_msg}")
                    guardar_en_drive = False
        else:
            st.warning("No se pudo conectar con Google Drive.")
            guardar_en_drive = False



        if uploaded_files:
            movimientos_list = []
            extractos_list = []
            errores_archivos = []
            # Obtener lista de PDFs ya existentes en la carpeta
            pdfs_en_drive = listar_pdfs_en_drive(folder_id)
            nombres_pdfs_drive = set(pdf['name'] for pdf in pdfs_en_drive)
            for uploaded_file in uploaded_files:
                file_name = uploaded_file.name
                file_hash = get_file_hash(uploaded_file)
                if file_name in nombres_pdfs_drive:
                    st.info(f"El archivo '{file_name}' ya existe en la carpeta de Drive y no será procesado para evitar duplicados.")
                    continue

                if file_hash in st.session_state["processed_files"]:
                    st.info(f"{file_name} ya fue procesado.")
                    continue

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getbuffer())
                    tmp_path = tmp_file.name

                if guardar_en_drive and folder_id:
                    success, result = subir_a_drive(file_name, uploaded_file.getvalue(), 'application/pdf', folder_id=folder_id)
                    if success:
                        drive_success += 1
                    else:
                        drive_errors.append(f"{uploaded_file.name}: {result}")

                with st.spinner(f"Procesando {uploaded_file.name} para detectar movimientos..."):
                    df_movimientos, df_extractos, banco, _ = extract_data_from_pdf(tmp_path, filename=file_name)
                Path(tmp_path).unlink()
                if df_movimientos is not None and df_extractos is not None:
                    st.session_state["processed_files"].add(file_hash)

                if df_movimientos is None or df_extractos is None:
                    errores_archivos.append(uploaded_file.name)
                    continue
                df_movimientos["archivo"] = file_name
                movimientos_list.append(df_movimientos)
                extractos_list.append(df_extractos)

            # Mostrar resumen de subida a Drive
            if guardar_en_drive:
                st.info(f"Archivos subidos a Drive: {drive_success}/{len(uploaded_files)}")
                if drive_errors:
                    st.warning("Errores al subir a Drive:\n" + "\n".join(drive_errors))
            # Mostrar errores de extracción
            if errores_archivos:
                st.warning("No se pudieron extraer datos de los siguientes archivos:\n" + "\n".join(errores_archivos))

            if movimientos_list:
                df_total_mov = pd.concat(movimientos_list, ignore_index=True)
                df_total_ext = pd.concat(extractos_list, ignore_index=True)
                st.success(f"✅ Archivos procesados: {len(movimientos_list)}. Total de movimientos: {len(df_total_mov)}")
                st.subheader("Movimientos detectados")
                st.dataframe(df_total_mov)
                csv_mov = df_total_mov.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="Descargar movimientos en CSV",
                    data=csv_mov,
                    file_name="movimientos_combinados.csv",
                    mime="text/csv"
                )
                st.subheader("Extractos detectados (resúmenes)")
                st.dataframe(df_total_ext)
                csv_ext = df_total_ext.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="Descargar extractos en CSV",
                    data=csv_ext,
                    file_name="extractos_combinados.csv",
                    mime="text/csv"
                )

                # --- Botón para anexar movimientos a la base de datos principal ---
                st.subheader("Anexar movimientos y extractos a la base de datos")
                if st.button("Subir"):
                    # Guardar movimientos
                    movimientos_df = load_movimientos_data()
                    ids_existentes = set(movimientos_df["id"]) if not movimientos_df.empty else set()
                    from modules.sheets_utils import generar_id_compuesto, get_google_sheets_client
                    nuevos = []
                    for _, row in df_total_mov.iterrows():
                        id_mov = row.get("id")
                        if id_mov not in ids_existentes:
                            data = row.to_dict()
                            nuevos.append(data)
                    gc = get_google_sheets_client()
                    sheet_id = st.secrets["google"]["spreadsheet_id"]
                    sh = gc.open_by_key(sheet_id)
                    # Guardar movimientos
                    mov_guardados = 0
                    mov_duplicados = 0
                    if nuevos:
                        worksheet_mov = sh.worksheet("movimientos")
                        df_actual_mov = pd.DataFrame(worksheet_mov.get_all_records())
                        df_final_mov = pd.concat([df_actual_mov, pd.DataFrame(nuevos)], ignore_index=True)
                        set_with_dataframe(worksheet_mov, df_final_mov)
                        mov_guardados = len(nuevos)
                        mov_duplicados = len(df_total_mov) - mov_guardados
                        st.success(f"Movimientos guardados: {mov_guardados} | Duplicados: {mov_duplicados} de {len(df_total_mov)} movimientos.")
                    else:
                        st.info("No hay movimientos nuevos para guardar.")

                    # Guardar extractos
                    worksheet_ext = sh.worksheet("extractos")
                    df_actual_ext = pd.DataFrame(worksheet_ext.get_all_records())
                    nuevos_ext = []
                    extracto_ids_existentes = set(df_actual_ext["extracto_id"]) if "extracto_id" in df_actual_ext.columns else set()
                    for _, row in df_total_ext.iterrows():
                        if row.get("extracto_id") not in extracto_ids_existentes:
                            nuevos_ext.append(row.to_dict())
                    ext_guardados = 0
                    ext_duplicados = 0
                    if nuevos_ext:
                        df_final_ext = pd.concat([df_actual_ext, pd.DataFrame(nuevos_ext)], ignore_index=True)
                        set_with_dataframe(worksheet_ext, df_final_ext)
                        ext_guardados = len(nuevos_ext)
                        ext_duplicados = len(df_total_ext) - ext_guardados
                        st.success(f"Extractos guardados: {ext_guardados} | Duplicados: {ext_duplicados} de {len(df_total_ext)} extractos.")
                    else:
                        st.info("No hay extractos nuevos para guardar.")
            else:
                st.warning("No se pudo extraer información de ningún archivo.")
        else:
            st.info("Sube uno o varios PDFs de extractos bancarios para comenzar.")

