import streamlit as st
from modules.sheets_utils import load_movimientos_data

@st.cache_data(show_spinner="Cargando datos...")
def _fetch(sheet_name: str):
    return load_movimientos_data(sheet_name)

def load_data():
    """Carga movimientos y extractos si no existen en session_state."""
    if st.session_state.get("movimientos_df") is None:
        st.session_state["movimientos_df"] = _fetch("movimientos")
    if st.session_state.get("extractos_df") is None:
        st.session_state["extractos_df"] = _fetch("extractos")
    return st.session_state["movimientos_df"], st.session_state["extractos_df"]

def refresh_data():
    """Recarga los datos desde Google Sheets y actualiza session_state."""
    st.session_state["movimientos_df"] = _fetch("movimientos")
    st.session_state["extractos_df"] = _fetch("extractos")
