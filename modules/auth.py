import streamlit as st
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import Flow
import os
import pickle

@st.cache_resource
def get_credentials(scopes):
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes
        )
        return creds
    except Exception as e:
        st.error(f"Error al cargar credenciales: {e}")
        return None

def hash_password(password):
    """Codifica la contraseña usando SHA-256"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

# --- Google OAuth2 Login ---
def google_login():
    """Inicia sesión con Google OAuth2"""
    client_secrets = st.secrets["google_oauth_client"]
    scopes = ["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
    redirect_uri = client_secrets["redirect_uris"][0]

    flow = Flow.from_client_config(
        {"web": dict(client_secrets)},
        scopes=scopes,
        redirect_uri=redirect_uri
    )

    auth_url, state = flow.authorization_url(prompt='consent', include_granted_scopes='true')
    st.session_state["oauth_state"] = state
    # Solo retorna la URL, no renderiza ningún botón
    return auth_url


def init_session_state():
    """Inicializa variables de estado de la sesión"""
    if "authentication_status" not in st.session_state:
        st.session_state["authentication_status"] = False
    if "name" not in st.session_state:
        st.session_state["name"] = None
    if "username" not in st.session_state:
        st.session_state["username"] = None
    if "role" not in st.session_state:
        st.session_state["role"] = None
    if "temp_data" not in st.session_state:
        st.session_state["temp_data"] = None
    if "oauth_state" not in st.session_state:
        st.session_state["oauth_state"] = None
    if "movimientos_df" not in st.session_state:
        st.session_state["movimientos_df"] = None
    if "extractos_df" not in st.session_state:
        st.session_state["extractos_df"] = None
    if "processed_files" not in st.session_state:
        st.session_state["processed_files"] = {}

def logout():
    """Cierra la sesión del usuario"""
    st.session_state["authentication_status"] = False
    st.session_state["name"] = None
    st.session_state["username"] = None
    st.session_state["role"] = None
    st.rerun()
