import datetime
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd

from modules.drive_utils import subir_a_drive, crear_carpeta_en_drive
from modules.sheets_utils import (
    get_google_sheets_client, save_to_google_sheets, save_to_unificada, load_movimientos_data
)
from modules.pdf_parser import extract_data_from_pdf
from gspread_dataframe import set_with_dataframe



def render(movimientos_df):
        st.title("📄 Subida de Extractos Bancarios")
        st.caption("Sube uno o varios extractos bancarios en PDF para identificar automáticamente los gastos y clasificarlos por categoría")

        uploaded_files = st.file_uploader(
            "Selecciona uno o varios archivos PDF de extractos bancarios", 
            type="pdf", 
            accept_multiple_files=True
        )

        guardar_en_drive = st.checkbox("¿Guardar los archivos en Google Drive?", value=False)
        folder_id = None
        # Guardar en Drive (resumen)
        drive_success = 0
        drive_errors = []
        if guardar_en_drive and uploaded_files:
            nombre_carpeta = f"Extractos_{datetime.datetime.now().strftime('%Y-%m-%d')}"
            st.info(f"Se creará una carpeta en Drive llamada: {nombre_carpeta}")
            ok, folder_id_or_msg = crear_carpeta_en_drive(nombre_carpeta)
            if ok:
                folder_id = folder_id_or_msg
                st.success(f"Carpeta creada en Drive.")
            else:
                st.warning(f"No se pudo crear la carpeta en Drive: {folder_id_or_msg}")
                guardar_en_drive = False


        if uploaded_files:
            movimientos_list = []
            extractos_list = []
            errores_archivos = []
            for uploaded_file in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getbuffer())
                    tmp_path = tmp_file.name

                if guardar_en_drive and folder_id:
                    file_name = f"Extracto_{uploaded_file.name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    success, result = subir_a_drive(file_name, uploaded_file.getvalue(), 'application/pdf', folder_id=folder_id)
                    if success:
                        drive_success += 1
                    else:
                        drive_errors.append(f"{uploaded_file.name}: {result}")

                # Procesar el PDF
                with st.spinner(f"Procesando {uploaded_file.name} para detectar movimientos..."):
                    df_movimientos, df_extractos, banco, _ = extract_data_from_pdf(tmp_path, filename=uploaded_file.name)
                    if df_movimientos is None or df_extractos is None:
                        errores_archivos.append(uploaded_file.name)
                    else:
                        df_movimientos["archivo"] = uploaded_file.name
                        movimientos_list.append(df_movimientos)
                        extractos_list.append(df_extractos)

                Path(tmp_path).unlink()

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
                st.subheader("Anexar movimientos a la base de datos principal")
                if st.button("Anexar a base de datos"):
                    movimientos_df = load_movimientos_data()
                    ids_existentes = set(movimientos_df["id"]) if not movimientos_df.empty else set()
                    from modules.sheets_utils import generar_id_compuesto, get_google_sheets_client
                    nuevos = []
                    for _, row in df_total_mov.iterrows():
                        id_mov = row.get("id")
                        if id_mov not in ids_existentes:
                            data = row.to_dict()
                            nuevos.append(data)
                    if nuevos:
                        gc = get_google_sheets_client()
                        sheet_id = st.secrets["google"]["spreadsheet_id"]
                        sh = gc.open_by_key(sheet_id)
                        worksheet = sh.worksheet("movimientos")
                        df_actual = pd.DataFrame(worksheet.get_all_records())
                        df_final = pd.concat([df_actual, pd.DataFrame(nuevos)], ignore_index=True)
                        set_with_dataframe(worksheet, df_final)
                        st.success(f"Guardados: {len(nuevos)} | Duplicados: {len(df_total_mov)-len(nuevos)} de {len(df_total_mov)} movimientos.")
                    else:
                        st.info("No hay movimientos nuevos para guardar.")
                # --- Botón para anexar extractos a la base de datos de extractos (opcional) ---
                st.subheader("Anexar extractos a la base de datos de extractos")
                if st.button("Anexar extractos a base de datos"):
                    from modules.sheets_utils import get_google_sheets_client
                    gc = get_google_sheets_client()
                    sheet_id = st.secrets["google"]["spreadsheet_id"]
                    sh = gc.open_by_key(sheet_id)
                    worksheet = sh.worksheet("extractos")
                    df_actual = pd.DataFrame(worksheet.get_all_records())
                    nuevos_ext = []
                    # Manejar si la hoja está vacía o no tiene la columna 'extracto_id'
                    extracto_ids_existentes = set(df_actual["extracto_id"]) if "extracto_id" in df_actual.columns else set()
                    for _, row in df_total_ext.iterrows():
                        if row.get("extracto_id") not in extracto_ids_existentes:
                            nuevos_ext.append(row.to_dict())
                    if nuevos_ext:
                        df_final = pd.concat([df_actual, pd.DataFrame(nuevos_ext)], ignore_index=True)
                        set_with_dataframe(worksheet, df_final)
                        st.success(f"Extractos guardados: {len(nuevos_ext)} | Duplicados: {len(df_total_ext)-len(nuevos_ext)} de {len(df_total_ext)} extractos.")
                    else:
                        st.info("No hay extractos nuevos para guardar.")
            else:
                st.warning("No se pudo extraer información de ningún archivo.")
        else:
            st.info("Sube uno o varios PDFs de extractos bancarios para comenzar.")

