import streamlit as st
from modules.sheets_utils import load_movimientos_data

@st.cache_data(show_spinner="Cargando datos...")
def _fetch():
    """Obtiene todos los datos requeridos desde Google Sheets."""
    return {
        "movimientos_df": load_movimientos_data("movimientos"),
        "extractos_df": load_movimientos_data("extractos"),
    }

def load_data():
    """Carga los datos en session_state si aún no existen."""
    for k, v in _fetch().items():
        if st.session_state.get(k) is None:
            st.session_state[k] = v
    return st.session_state["movimientos_df"], st.session_state["extractos_df"]

def refresh_data():
    """Borra la caché y vuelve a cargar los datos."""
    _fetch.clear()
    load_data()
