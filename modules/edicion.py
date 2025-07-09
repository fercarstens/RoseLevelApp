import streamlit as st
import pandas as pd
import datetime

from gspread_dataframe import set_with_dataframe
from modules.sheets_utils import get_google_sheets_client

def render(movimientos_df):
    st.title("📝 Edición Manual de Movimientos")
    st.caption("Corrige tipo, monto, descripción, categoría, etc. de los movimientos importados.")

    if movimientos_df.empty:
        st.info("No hay movimientos para editar.")
        return

    # Filtros: por tipo y categoría
    tipos = ["todos"] + sorted(movimientos_df["tipo"].dropna().unique())
    filtro_tipo = st.selectbox("Filtrar por tipo", tipos, index=0)
    categorias = ["todas"] + sorted(movimientos_df["categoría"].dropna().unique())
    filtro_categoria = st.selectbox("Filtrar por categoría", categorias, index=0)

    df_edit = movimientos_df.copy()
    if filtro_tipo != "todos":
        df_edit = df_edit[df_edit["tipo"].str.lower() == filtro_tipo.lower()]
    if filtro_categoria != "todas":
        df_edit = df_edit[df_edit["categoría"].str.lower() == filtro_categoria.lower()]

    st.dataframe(df_edit, use_container_width=True)
    st.markdown("---")
    st.write("Selecciona un movimiento para editar:")

    if df_edit.empty:
        st.info("No hay movimientos para editar con estos filtros.")
        return

    selected = st.selectbox("ID de movimiento", df_edit["id"].tolist())
    if selected:
        row = df_edit[df_edit["id"] == selected].iloc[0]
        with st.form("form_edicion_manual"):
            fecha = st.date_input("Fecha", pd.to_datetime(row["fecha"]))
            banco = st.text_input("Banco", row["banco"])
            monto = st.number_input("Monto", value=float(row["monto"]), step=0.01)
            tipo = st.selectbox("Tipo", ["ingreso", "egreso"], index=["ingreso", "egreso"].index(row["tipo"]))
            descripcion = st.text_input("Descripción", row["descripción"])
            categoria = st.text_input("Categoría", row["categoría"])
            extracto_id = st.text_input("Extracto ID", row["extracto_id"])
            origen_dato = st.text_input("Origen Dato", row["origen_dato"])
            submit = st.form_submit_button("Guardar cambios")

        if submit:
            data_edit = {
                "id": row["id"],
                "fecha": fecha.strftime("%Y-%m-%d"),
                "banco": banco,
                "monto": monto,
                "tipo": tipo,
                "descripción": descripcion,
                "categoría": categoria,
                "extracto_id": extracto_id,
                "origen_dato": origen_dato,
                "editado_por": st.session_state.get("username", "anon"),
                "fecha_edicion": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Actualizar en Google Sheets (nombre de hoja: "movimientos")
            gc = get_google_sheets_client()
            sheet_id = st.secrets["google"]["spreadsheet_id"]
            sh = gc.open_by_key(sheet_id)
            worksheet = sh.worksheet("movimientos")
            df_all = pd.DataFrame(worksheet.get_all_records())
            idx = df_all[df_all["id"] == row["id"]].index
            if not idx.empty:
                for col in data_edit:
                    df_all.at[idx[0], col] = data_edit[col]
                set_with_dataframe(worksheet, df_all)
                st.success("¡Movimiento actualizado!")
            else:
                st.error("No se encontró el movimiento para actualizar.")

