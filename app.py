import streamlit as st

from modules.auth import (
    init_session_state, logout
)
from modules.sheets_utils import load_movimientos_data
from modules import dashboard, ingresos, egresos, subir, reportes, configuracion, edicion, login


st.set_page_config(
    page_title="Panel Financiero - Rose Level",
    page_icon="🌹",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_session_state()

if not st.session_state["authentication_status"]:
    login.render()
else:
    st.sidebar.title(f"👋 Bienvenido, {st.session_state['name']}")
    st.sidebar.info(f"🔑 Usuario: {st.session_state['username']}")
    st.sidebar.divider()
    menu_options = ["📊 Dashboard", "💰 Ingresos", "💸 Egresos", "📄 Subida de Extractos", "📈 Reportes", "📝 Edición Manual"]
    menu = st.sidebar.radio("Navegación", menu_options)
    st.sidebar.divider()
    if st.sidebar.button("🚪 Cerrar sesión"):
        logout()
    movimientos_df = load_movimientos_data("movimientos")
    extractos_df = load_movimientos_data("extractos")
    if menu == "📊 Dashboard":
        dashboard.render(movimientos_df, extractos_df)
    elif menu == "💰 Ingresos":
        ingresos.render(movimientos_df)
    elif menu == "💸 Egresos":
        egresos.render(movimientos_df)
    elif menu == "📄 Subida de Extractos":
        subir.render(movimientos_df)
    elif menu == "📈 Reportes":
        reportes.render(movimientos_df, extractos_df)
    elif menu == "📝 Edición Manual":
        edicion.render(movimientos_df)
