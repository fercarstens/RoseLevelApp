import streamlit as st
import pandas as pd

from modules.sheets_utils import save_to_unificada


def render(movimientos_df):
    st.title("💰 Registro de Ingresos")
    st.caption("Visualiza y filtra los ingresos registrados en la base de datos unificada.")

    movimientos_df["tipo"] = movimientos_df["tipo"].astype(str).fillna("")
    ingresos_df = movimientos_df[movimientos_df["tipo"].str.lower() == "ingreso"].copy()

    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        fecha_desde = st.date_input("Desde", pd.to_datetime("today") - pd.Timedelta(days=30))
    with col2:
        fecha_hasta = st.date_input("Hasta", pd.to_datetime("today"))

    ingresos_df["fecha"] = pd.to_datetime(ingresos_df["fecha"])
    filtered_df = ingresos_df[
        (ingresos_df["fecha"] >= pd.Timestamp(fecha_desde)) &
        (ingresos_df["fecha"] <= pd.Timestamp(fecha_hasta))
    ]

    columnas_ingreso = ["fecha", "concepto", "descripcion", "monto", "referencia", "comprobante", "banco", "archivo", "balance"]
    for col in columnas_ingreso:
        if col not in filtered_df.columns:
            filtered_df[col] = ""

    display_df = filtered_df[columnas_ingreso].sort_values("fecha", ascending=False)
    display_df["monto"] = display_df["monto"].astype(float).map("${:,.2f}".format)
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    st.metric(
        "Total en el período",
        f"${filtered_df['monto'].astype(float).sum():,.2f}",
        help="Total de ingresos en el período seleccionado",
    )

    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Exportar a CSV",
        data=csv,
        file_name=f"ingresos_{fecha_desde}_{fecha_hasta}.csv",
        mime="text/csv",
    )

    st.divider()
    st.subheader("Agregar ingreso manual")
    with st.form("form_ingreso_manual"):
        fecha_n = st.date_input("Fecha del ingreso", pd.to_datetime("today"))
        banco_n = st.text_input("Banco")
        concepto_n = st.text_input("Concepto")
        descripcion_n = st.text_input("Descripción")
        monto_n = st.number_input("Monto", step=0.01)
        referencia_n = st.text_input("Referencia")
        comprobante_n = st.text_input("Comprobante")
        archivo_n = st.text_input("Archivo")
        submit_n = st.form_submit_button("Guardar ingreso")

    if submit_n:
        data = {
            "fecha": fecha_n.strftime("%Y-%m-%d"),
            "banco": banco_n,
            "concepto": concepto_n,
            "descripción": descripcion_n,
            "monto": monto_n,
            "referencia": referencia_n,
            "comprobante": comprobante_n,
            "archivo": archivo_n,
            "tipo": "ingreso",
        }
        ok, msg = save_to_unificada(data, "movimientos")
        if ok:
            st.success(msg)
            st.experimental_rerun()
        else:
            st.error(msg)
