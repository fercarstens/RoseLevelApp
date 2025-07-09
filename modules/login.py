import streamlit as st
from google_auth_oauthlib.flow import Flow
from modules.auth import google_login

def get_user_info(token):
    import requests
    resp = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {token}"}
    )
    if resp.status_code == 200:
        return resp.json()
    return None

def render():
    """Pantalla de login con Google y validación de usuarios permitidos"""
    query_params = st.query_params
    st.markdown("""
    <div style=\"display: flex; flex-direction: column; align-items: center; justify-content: center; height: 60vh;\">
        <h1 style=\"color: #c2185b;\">🌹 Panel Financiero Rose Level 🌹</h1>
        <p style=\"font-size: 1.2rem; color: #555;\">Inicia sesión con tu cuenta de Google para continuar</p>
    </div>
    """, unsafe_allow_html=True)
    if "code" in query_params and "state" in query_params:
        code = query_params["code"]
        if isinstance(code, list):
            code = code[0]
        state_url = query_params["state"]
        if isinstance(state_url, list):
            state_url = state_url[0]
        if (not st.session_state.get("oauth_state")) or (not st.session_state.get("oauth_code")):
            st.session_state["oauth_state"] = state_url
            st.session_state["oauth_code"] = code
            st.query_params.clear()
            st.rerun()
        state_session = st.session_state["oauth_state"]
        code_session = st.session_state["oauth_code"]
        if state_url != state_session or code != code_session:
            st.error("El parámetro state o code no coincide. Posible problema de seguridad o de flujo OAuth.")
        else:
            client_secrets = st.secrets["google_oauth_client"]
            scopes = ["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
            redirect_uri = client_secrets["redirect_uris"][0]
            flow = Flow.from_client_config(
                {"web": dict(client_secrets)},
                scopes=scopes,
                redirect_uri=redirect_uri
            )
            flow.fetch_token(code=code_session)
            credentials = flow.credentials
            user_info = get_user_info(credentials.token)
            if user_info:
                name = user_info.get("name", user_info.get("email"))
                username = user_info.get("email")
                ALLOWED_USERS = st.secrets.get("allowed_users", {})
                if username not in ALLOWED_USERS:
                    st.error("Acceso denegado. Tu correo no está autorizado.")
                    st.session_state["oauth_state"] = None
                    st.session_state["oauth_code"] = None
                    st.query_params.clear()
                else:
                    role = ALLOWED_USERS[username]
                    st.session_state["authentication_status"] = True
                    st.session_state["name"] = name
                    st.session_state["username"] = username
                    st.session_state["role"] = role
                    st.session_state["oauth_state"] = None
                    st.session_state["oauth_code"] = None
                    st.query_params.clear()
                    st.rerun()
            else:
                st.error("No se pudo obtener información del usuario.")
    elif st.session_state.get("oauth_code") and st.session_state.get("oauth_state"):
        code_session = st.session_state["oauth_code"]
        state_session = st.session_state["oauth_state"]
        client_secrets = st.secrets["google_oauth_client"]
        scopes = ["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
        redirect_uri = client_secrets["redirect_uris"][0]
        flow = Flow.from_client_config(
            {"web": dict(client_secrets)},
            scopes=scopes,
            redirect_uri=redirect_uri
        )
        flow.fetch_token(code=code_session)
        credentials = flow.credentials
        user_info = get_user_info(credentials.token)
        if user_info:
            name = user_info.get("name", user_info.get("email"))
            username = user_info.get("email")
            ALLOWED_USERS = st.secrets.get("allowed_users", {})
            if username not in ALLOWED_USERS:
                st.error("Acceso denegado. Correo no está autorizado.")
                st.session_state["oauth_state"] = None
                st.session_state["oauth_code"] = None
                st.query_params.clear()
            else:
                role = ALLOWED_USERS[username]
                st.session_state["authentication_status"] = True
                st.session_state["name"] = name
                st.session_state["username"] = username
                st.session_state["role"] = role
                st.session_state["oauth_state"] = None
                st.session_state["oauth_code"] = None
                st.query_params.clear()
                st.rerun()
        else:
            st.error("No se pudo obtener información del usuario.")
    else:
        auth_url = google_login()
        st.markdown(f"""
        <div style='display: flex; justify-content: center; margin-top: 2rem;'>
            <a href='{auth_url}' id='google-login-btn' style='background: #c2185b; color: white; padding: 0.8rem 2rem; border-radius: 30px; font-size: 1.1rem; text-decoration: none; box-shadow: 0 2px 8px #0001;'>
                <b>Iniciar sesión</b>
            </a>
        </div>
        """, unsafe_allow_html=True)
