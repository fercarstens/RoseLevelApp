import pdfplumber
import re
import streamlit as st

import pandas as pd

def extraer_texto(pdf_path):
    texto = ""
    with pdfplumber.open(pdf_path) as pdf:
        for pagina in pdf.pages:
            texto_pagina = pagina.extract_text()
            if texto_pagina:
                texto += texto_pagina + "\n"
    return texto

def detectar_banco(texto, filename=None):
    if filename:
        filename_lower = filename.lower()
        patrones = [
            (r"trui[\w\s]*|truist", "Truist"),
            (r"wise", "Wise"),
            (r"mercury", "Mercury"),
            (r"chase|jpmorgan|jp morgan|j.p. morgan|jpmorgan chase", "Chase"),
        ]
        for patron, nombre in patrones:
            if re.search(patron, filename_lower):
                return nombre
    # Si no se detecta por filename, usar el texto como antes
    texto_lower = texto.lower()
    patrones = [
        (r"trui[\w\s]*|truist", "Truist"),
        (r"wise", "Wise"),
        (r"mercury", "Mercury"),
        (r"chase|jpmorgan|jp morgan|j.p. morgan|jpmorgan chase", "Chase"),
    ]
    coincidencias = []
    for patron, nombre in patrones:
        if re.search(patron, texto_lower):
            coincidencias.append(nombre)
    if len(coincidencias) == 1:
        return coincidencias[0]
    elif len(coincidencias) > 1:
        st.info(f"Se detectaron varios bancos posibles: {', '.join(coincidencias)}. Usando el primero: {coincidencias[0]}")
        return coincidencias[0]
    else:
        for linea in texto_lower.splitlines():
            for patron, nombre in patrones:
                if re.search(patron, linea):
                    return nombre
        return "Desconocido"

def extract_data_from_pdf(pdf_path, filename=None):
    """
    Extrae y estandariza los datos de un PDF bancario.
    Devuelve: df_movimientos, df_extractos, banco, texto
    """
    banco = None
    try:
        texto = extraer_texto(pdf_path)
        banco = detectar_banco(texto, filename=filename)
        from modules.parsear import (parsear_chase, parsear_mercury, parsear_truist, parsear_wise_usd, parsear_wise_eur)


        # Usa siempre el nombre del archivo para trazabilidad
        nombre_archivo = filename if filename else str(pdf_path)

        df_movimientos, df_extractos = None, None
        if banco == "Chase":
            try:
                df_movimientos, df_extractos = parsear_chase(texto, nombre_archivo)
            except Exception as e:
                st.error(f"❌ Error al parsear Chase: {e}")
        elif banco == "Mercury":
            try:
                df_movimientos, df_extractos = parsear_mercury(texto, nombre_archivo)
            except Exception as e:
                st.error(f"❌ Error al parsear Mercury: {e}")
        elif banco == "Truist":
            try:
                df_movimientos, df_extractos = parsear_truist(texto, nombre_archivo)
            except Exception as e:
                st.error(f"❌ Error al parsear Truist: {e}")
        elif banco == "Wise":
            try:
                if "eur statement" in texto.lower():
                    df_movimientos, df_extractos = parsear_wise_eur(texto, nombre_archivo)
                elif "usd statement" in texto.lower():
                    df_movimientos, df_extractos = parsear_wise_usd(texto, nombre_archivo)
                else:
                    try:
                        df_movimientos, df_extractos = parsear_wise_usd(texto, nombre_archivo)
                    except Exception:
                        df_movimientos, df_extractos = parsear_wise_eur(texto, nombre_archivo)
            except Exception as e:
                st.error(f"❌ Error al parsear Wise: {e}")
        else:
            st.warning("No se reconoce el banco en el PDF.")
            return None, None, banco, texto

        # Si el DataFrame no tiene las columnas estándar, devolver vacíos con columnas estándar
        columnas_mov = ["id", "fecha", "banco", "monto", "tipo", "descripción", "categoría", "extracto_id", "origen_dato"]
        columnas_ext = ["extracto_id", "banco", "fecha_inicio", "fecha_fin", "saldo_inicial", "saldo_final", "total_ingresos", "total_egresos", "archivo_fuente"]
        if df_movimientos is None or not isinstance(df_movimientos, pd.DataFrame) or df_movimientos.empty:
            df_movimientos = pd.DataFrame(columns=columnas_mov)
        if df_extractos is None or not isinstance(df_extractos, pd.DataFrame) or df_extractos.empty:
            df_extractos = pd.DataFrame(columns=columnas_ext)

        return df_movimientos, df_extractos, banco, texto

    except Exception as e:
        st.error(f"❌ Error al procesar el PDF ({banco or 'desconocido'}): {e}")
        columnas_mov = ["id", "fecha", "banco", "monto", "tipo", "descripción", "categoría", "extracto_id", "origen_dato"]
        columnas_ext = ["extracto_id", "banco", "fecha_inicio", "fecha_fin", "saldo_inicial", "saldo_final", "total_ingresos", "total_egresos", "archivo_fuente"]
        return pd.DataFrame(columns=columnas_mov), pd.DataFrame(columns=columnas_ext), banco, None