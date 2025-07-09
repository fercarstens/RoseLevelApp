import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import pandas as pd
import streamlit as st
import datetime
import uuid

from modules.auth import get_credentials

@st.cache_resource
def get_google_sheets_client():
    """Establece conexión con Google Sheets usando credenciales del service account"""
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = get_credentials(scopes)
        if creds:
            client = gspread.authorize(creds)
            return client
        else:
            return None
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

def save_to_google_sheets(data, sheet_type):
    """Guarda datos en Google Sheets"""
    # Generar ID único
    if "id" not in data:
        data["id"] = f"{sheet_type.upper()[:3]}-{uuid.uuid4().hex[:8]}"
    
    # Añadir metadatos
    data["registrado_por"] = st.session_state["username"]
    data["fecha_registro"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # En modo producción:
    gc = get_google_sheets_client()
    if gc:
        try:
            # Abrir hoja de cálculo
            sheet_id = st.secrets["google"]["spreadsheet_id"]  # En producción
            sh = gc.open_by_key(sheet_id)
            worksheet = sh.worksheet(sheet_type)
            
            # Leer datos existentes
            existing_data = pd.DataFrame(worksheet.get_all_records())
            
            # Añadir nueva fila
            new_row = pd.DataFrame([data])
            updated_data = pd.concat([existing_data, new_row], ignore_index=True)
            
            # Actualizar hoja
            set_with_dataframe(worksheet, updated_data)
            return True, "Datos guardados correctamente en Google Sheets"
        except Exception as e:
            return False, f"Error al guardar en Google Sheets: {e}"
    else:
        # Modo demo - guardamos en datos temporales
        return False, "Solo se permite guardar en Google Sheets real."

# @st.cache_data
# def load_demo_data():
#     """Carga datos de ejemplo para modo demo"""
#     try:
#         gc = get_google_sheets_client()
#         if gc and "spreadsheet_id" in st.secrets["google"]:
#             # Intentar cargar datos reales
#             sh = gc.open_by_key(st.secrets["google"]["spreadsheet_id"])
#             ingresos_df = get_as_dataframe(sh.worksheet("ingresos")).dropna(how='all')
#             egresos_df = get_as_dataframe(sh.worksheet("egresos")).dropna(how='all')
#             return {"ingresos": ingresos_df, "egresos": egresos_df}
#     except Exception as e:
#         st.warning("Usando datos de ejemplo")
#     # Generar datos de ejemplo
#     ingresos = pd.DataFrame({
#         "id": [f"ING-{{i:04d}}" for i in range(1, 11)],
#         "fecha": pd.date_range(start="2024-07-01", periods=10, freq="M").strftime("%Y-%m-%d").tolist(),
#         "concepto": [f"Proyecto Cliente {{chr(65+i)}}" for i in range(10)],
#         "monto": [round(5000 + i * 500 + (i * i * 100), 2) for i in range(10)],
#         "fuente": [f"Cliente {{chr(65+i)}}" for i in range(10)],
#         "registrado_por": ["demo"] * 10,
#         "fecha_registro": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#     })
#     egresos = pd.DataFrame({
#         "id": [f"EGR-{{i:04d}}" for i in range(1, 16)],
#         "fecha": pd.date_range(start="2024-07-05", periods=15, freq="20D").strftime("%Y-%m-%d").tolist(),
#         "concepto": ["Alquiler", "Servicios", "Suministros", "Personal", "Software"] * 3,
#         "monto": [round(1000 + i * 200 + (i % 5) * 150, 2) for i in range(15)],
#         "proveedor": ["Proveedor " + chr(70+i%10) for i in range(15)],
#         "comprobante": [f"FACT-{{100+i}}" for i in range(15)],
#         "registrado_por": ["demo"] * 15,
#         "fecha_registro": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#     })
#     return {"ingresos": ingresos, "egresos": egresos}

def generar_id_compuesto(fecha, banco, concepto, monto):
    # Normaliza los campos para el ID
    fecha_str = str(fecha).replace(' ', '').replace('/', '-')
    banco_str = str(banco).strip().replace(' ', '').lower()
    concepto_str = str(concepto).strip().replace(' ', '').lower()
    monto_str = f"{float(monto):.2f}"
    return f"{fecha_str}_{banco_str}_{concepto_str}_{monto_str}"


def save_to_unificada(data, sheet_name="movimientos"):
    """
    Guarda un registro en la hoja unificada 'movimientos' en Google Sheets, evitando duplicados por ID compuesto.
    data: dict con los campos de la fila.
    """
    # Generar ID compuesto
    data["id"] = generar_id_compuesto(
        data.get("fecha", "NA"),
        data.get("banco", "NA"),
        data.get("concepto", "NA"),
        data.get("monto", 0)
    )
    data["registrado_por"] = st.session_state.get("username", "anon")
    data["fecha_registro"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    gc = get_google_sheets_client()
    if gc:
        try:
            sheet_id = st.secrets["google"]["spreadsheet_id"]
            sh = gc.open_by_key(sheet_id)
            worksheet = sh.worksheet(sheet_name)
            existing_data = pd.DataFrame(worksheet.get_all_records())
            if not existing_data.empty and data["id"] in existing_data["id"].values:
                return False, f"Registro duplicado: {data['id']}"
            # Añadir nueva fila
            new_row = pd.DataFrame([data])
            updated_data = pd.concat([existing_data, new_row], ignore_index=True)
            set_with_dataframe(worksheet, updated_data)
            return True, f"Registro guardado: {data['id']}"
        except Exception as e:
            return False, f"Error al guardar en Google Sheets: {e}"
    else:
        return False, "No se pudo conectar a Google Sheets"

def load_movimientos_data(sheet_name="movimientos"):
    gc = get_google_sheets_client()
    if gc:
        try:
            sheet_id = st.secrets["google"]["spreadsheet_id"]
            sh = gc.open_by_key(sheet_id)
            worksheet = sh.worksheet(sheet_name)
            df = get_as_dataframe(worksheet).dropna(how='all')
            return df
        except Exception as e:
            st.error(f"Error al cargar datos de movimientos: {e}")
            return pd.DataFrame()
    else:
        st.error("No se pudo conectar a Google Sheets")
        return pd.DataFrame()
