import streamlit as st
import pandas as pd
import datetime
from modules.sheets_utils import save_to_unificada

def render(movimientos_df):
    st.title("💸 Registro de Egresos")
    st.caption("Visualiza y filtra los egresos registrados en la base de datos unificada.")

    movimientos_df["tipo"] = movimientos_df["tipo"].astype(str).fillna("")
    egresos_df = movimientos_df[movimientos_df["tipo"].str.lower() == "egreso"].copy()

    col1, col2 = st.columns(2)
    with col1:
        fecha_desde = st.date_input("Desde", datetime.datetime.now() - datetime.timedelta(days=30))
    with col2:
        fecha_hasta = st.date_input("Hasta", datetime.datetime.now())

    egresos_df["fecha"] = pd.to_datetime(egresos_df["fecha"])
    filtered_df = egresos_df[
        (egresos_df["fecha"] >= pd.Timestamp(fecha_desde)) &
        (egresos_df["fecha"] <= pd.Timestamp(fecha_hasta))
    ]

    columnas_egreso = ["fecha", "banco", "descripción", "categoría", "monto", "archivo"]
    for col in columnas_egreso:
        if col not in filtered_df.columns:
            filtered_df[col] = ""

    display_df = filtered_df[columnas_egreso].sort_values("fecha", ascending=False)
    display_df["monto"] = display_df["monto"].astype(float).map("${:,.2f}".format)
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    st.metric(
        "Total en el período",
        f"${filtered_df['monto'].astype(float).sum():,.2f}",
        help="Total de egresos en el período seleccionado",
    )

    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Exportar a CSV",
        data=csv,
        file_name=f"egresos_{fecha_desde}_{fecha_hasta}.csv",
        mime="text/csv",
    )

    st.divider()
    st.subheader("Agregar egreso manual")
    with st.form("form_egreso_manual"):
        fecha_n = st.date_input("Fecha del egreso", datetime.datetime.now())
        banco_n = st.text_input("Banco")
        descripcion_n = st.text_input("Descripción")
        categoria_n = st.text_input("Categoría")
        monto_n = st.number_input("Monto", step=100.00)
        referencia_n = st.text_input("Referencia")
        submit_n = st.form_submit_button("Guardar egreso")

    if submit_n:
        data = {
            "fecha": fecha_n.strftime("%Y-%m-%d"),
            "banco": banco_n,
            "categoria": categoria_n,
            "descripción": descripcion_n,
            "monto": monto_n,
            "referencia": referencia_n,
            "tipo": "egreso",
        }
        ok, msg = save_to_unificada(data, "movimientos")
        if ok:
            st.success(msg)
            st.experimental_rerun()
        else:
            st.error(msg)