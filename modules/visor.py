import streamlit as st
import tempfile
from pathlib import Path
import base64
from modules.pdf_parser import extract_data_from_pdf


def render(movimientos_df):
    """Visualiza un archivo PDF y muestra los movimientos detectados."""
    st.title("📑 Visor de PDFs")
    st.caption("Carga un PDF para ver el archivo junto con los movimientos extraídos.")

    uploaded_file = st.file_uploader("Selecciona un archivo PDF", type="pdf")
    if not uploaded_file:
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        tmp_path = tmp_file.name

    df_mov, df_ext, banco, _ = extract_data_from_pdf(tmp_path, filename=uploaded_file.name)

    with open(tmp_path, "rb") as f:
        b64_pdf = base64.b64encode(f.read()).decode("utf-8")
    pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

    st.subheader("Movimientos Detectados")
    st.dataframe(df_mov, use_container_width=True)

    if not df_ext.empty:
        st.subheader("Resumen de Extracto")
        st.dataframe(df_ext, use_container_width=True)

    Path(tmp_path).unlink()

