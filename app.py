import streamlit as st

from modules.auth import (
    init_session_state, logout
)
from modules import dashboard, ingresos, egresos, subir, reportes, configuracion, edicion, login, visor, subir_gemini
from modules.data_loader import load_data, refresh_data


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
    menu_options = [
        "📊 Dashboard",
        "💰 Ingresos",
        "💸 Egresos",
        "📄 Subida de Extractos",
        "📄 Subida de Extractos Gemini",
        "📑 Visor de PDFs",
        "📈 Reportes",
        "📝 Edición Manual",
    ]
    menu = st.sidebar.radio("Navegación", menu_options)
    st.sidebar.divider()
    if st.sidebar.button("🚪 Cerrar sesión"):
        logout()
    if st.sidebar.button("🔁 Recargar datos"):
        refresh_data()
    movimientos_df, extractos_df = load_data()
    if movimientos_df.empty:
        st.info("No hay movimientos registrados en la base de datos.")
    else:
        if menu == "📊 Dashboard":
            dashboard.render(st.session_state["movimientos_df"], st.session_state["extractos_df"])
        elif menu == "💰 Ingresos":
            ingresos.render(st.session_state["movimientos_df"])
        elif menu == "💸 Egresos":
            egresos.render(st.session_state["movimientos_df"])
        elif menu == "📄 Subida de Extractos":
            subir.render(st.session_state["movimientos_df"])
        elif menu == "📄 Subida de Extractos Gemini":
            subir_gemini.render(st.session_state["movimientos_df"])
        elif menu == "📑 Visor de PDFs":
            visor.render(st.session_state["movimientos_df"])
        elif menu == "📈 Reportes":
            reportes.render(st.session_state["movimientos_df"], st.session_state["extractos_df"])
        elif menu == "📝 Edición Manual":
            edicion.render(st.session_state["movimientos_df"])
