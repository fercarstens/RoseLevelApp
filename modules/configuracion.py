import streamlit as st
import pandas as pd
import datetime

def render(movimientos_df):
        st.title("⚙️ Configuración del Sistema")
        
        tab1, tab2 = st.tabs(["Integraciones", "Backup"])
        
        with tab1:
            st.subheader("Configuración de Integraciones")
            
            # Configuración de Google Drive
            with st.expander("Google Drive API"):
                st.write("Configuración para conectar con Google Drive")
                drive_folder_id = st.text_input("ID de Carpeta en Google Drive", 
                                              value=st.secrets.get("google", {}).get("drive_folder_id", ""))
                
                if st.button("Guardar Configuración Drive"):
                    # En producción, esto se guardaría en st.secrets
                    st.success("Configuración guardada")
            
            # Configuración de Google Sheets
            with st.expander("Google Sheets API"):
                st.write("Configuración para conectar con Google Sheets")
                spreadsheet_id = st.text_input("ID de la Hoja de Cálculo",
                                             value=st.secrets.get("spreadsheet_id", ""))
                
                if st.button("Guardar Configuración Sheets"):
                    # En producción, esto se guardaría en st.secrets
                    st.success("Configuración guardada")
        
        with tab2:
            st.subheader("Copia de Seguridad y Restauración")
            
            # Exportar datos de ejemplo
            # data = load_demo_data()
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Exportar Datos**")
                csv = pd.concat([
                    # data["ingresos"].assign(tipo="ingreso"),
                    # data["egresos"].assign(tipo="egreso")  # Eliminado: solo datos reales
                ]).to_csv(index=False).encode("utf-8")
                
                st.download_button(
                    "📥 Exportar Datos",
                    data=csv,
                    file_name=f"datos_financieros_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                st.write("**Importar Datos**")
                uploaded_file = st.file_uploader("Subir archivo CSV", type="csv")
                if uploaded_file:
                    try:
                        df = pd.read_csv(uploaded_file)
                        st.success("Archivo cargado correctamente")
                        st.dataframe(df.head(), use_container_width=True)
                    except Exception as e:
                        st.error(f"Error al cargar archivo: {e}")