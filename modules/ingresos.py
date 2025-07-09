import streamlit as st
import pandas as pd

def render(movimientos_df):
    st.title("💰 Registro de Ingresos")
    st.caption("Visualiza y filtra los ingresos registrados en la base de datos unificada.")
    movimientos_df['tipo'] = movimientos_df['tipo'].astype(str).fillna('')
    ingresos_df = movimientos_df[movimientos_df['tipo'].str.lower() == 'ingreso'].copy()
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        fecha_desde = st.date_input("Desde", pd.to_datetime('today') - pd.Timedelta(days=30))
    with col2:
        fecha_hasta = st.date_input("Hasta", pd.to_datetime('today'))
    # Aplicar filtros
    ingresos_df["fecha"] = pd.to_datetime(ingresos_df["fecha"])
    filtered_df = ingresos_df[
        (ingresos_df["fecha"] >= pd.Timestamp(fecha_desde)) & 
        (ingresos_df["fecha"] <= pd.Timestamp(fecha_hasta))
    ]
    # Mostrar tabla adaptable a columnas existentes
    columnas_ingreso = ["fecha", "concepto", "descripcion", "monto", "referencia", "comprobante", "banco", "archivo", "balance"]
    for col in columnas_ingreso:
        if col not in filtered_df.columns:
            filtered_df[col] = ""
    display_df = filtered_df[columnas_ingreso].sort_values("fecha", ascending=False)
    display_df["monto"] = display_df["monto"].astype(float).map("${:,.2f}".format)
    st.dataframe(display_df, hide_index=True, use_container_width=True)
    # Resumen
    st.metric(
        "Total en el período", 
        f"${filtered_df['monto'].astype(float).sum():,.2f}", 
        help="Total de ingresos en el período seleccionado"
    )
    # Opción para exportar
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Exportar a CSV",
        data=csv,
        file_name=f"ingresos_{fecha_desde}_{fecha_hasta}.csv",
        mime="text/csv",
    )
