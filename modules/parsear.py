
import pandas as pd
import re
from datetime import datetime


def normalizar_campo(valor):
    if valor is None:
        return "null"
    return str(valor).strip().lower().replace(" ", "_").replace("/", "-").replace("__", "_")

def generar_id_compuesto(fecha, banco, descripcion, monto):
    fecha_n = normalizar_campo(fecha)
    banco_n = normalizar_campo(banco)
    descripcion_n = normalizar_campo(descripcion)
    monto_n = normalizar_campo(abs(monto) if monto is not None else "null")
    return f"{fecha_n}_{banco_n}_{descripcion_n}_{monto_n}"

def generar_extracto_id(banco, fecha_inicio, fecha_fin, saldo_inicial, saldo_final, archivo_fuente):
    banco_n = normalizar_campo(banco)
    fecha_inicio_n = normalizar_campo(fecha_inicio)
    fecha_fin_n = normalizar_campo(fecha_fin)
    saldo_inicial_n = normalizar_campo(saldo_inicial)
    saldo_final_n = normalizar_campo(saldo_final)
    archivo_fuente_n = normalizar_campo(archivo_fuente)
    return f"{banco_n}_{fecha_inicio_n}_{fecha_fin_n}_{saldo_inicial_n}_{saldo_final_n}_{archivo_fuente_n}"

def categorizar_movimiento(descripcion):
    desc = descripcion.lower()
    # Aliases/Marcas propias, amplía si tienes más bancos internos
    mis_alias = ["roselevel", "rose level", "rl digit", "digital mar"]

    # 1. Transferencias internas: 
    if "rose level" in desc:
        return "Internal Transfer"
    if sum(alias in desc for alias in mis_alias) >= 2:
        return "Internal Transfer"

    # 2. Wise y patrones típicos
    if "received money from" in desc or desc.startswith("incoming"):
        return "Deposit"
    if "sent money to" in desc or desc.startswith("outgoing"):
        return "Transfers"
    if "converted usd to eur" in desc or desc.startswith("converted usd"):
        return "Conversion"
    if "wise charges" in desc or "fee" in desc or "charge" in desc:
        return "Fees"

    # 3. Otros patrones globales 
    if any(word in desc for word in ["payroll", "paychex", "salary", "deposit", "paycheck"]):
        return "Payroll"
    if any(word in desc for word in ["converted usd to eur", "converted usd", "usd to", "converted"]):
        return "Conversion"
    if any(word in desc for word in ["amazon", "walmart", "target", "market", "mercado"]):
        return "Shopping"
    if any(word in desc for word in ["zelle", "venmo", "paypal","transfer", "external transfer", "online transfer", "auto routing", "wise", "truist", "chase", "mercuryach"]):
        return "Transfers"
    if any(word in desc for word in ["irs", "tax", "federal", "state", "impuesto"]):
        return "Taxes"
    if any(word in desc for word in ["utility", "electric", "water", "internet", "phone", "spectrum", "comcast"]):
        return "Utilities"
    if any(word in desc for word in ["restaurant", "grill", "starbucks", "mcdonald", "coffee", "food", "bbq", "carrabba"]):
        return "Food & Restaurants"
    if any(word in desc for word in ["atm withdrawal", "atm", "cash withdrawal"]):
        return "Cash"
    if any(word in desc for word in ["insurance", "premium"]):
        return "Insurance"
    if any(word in desc for word in ["rent", "lease", "apartment", "uber"]):
        return "Rent"
    if any(word in desc for word in ["youtube", "slack", "linkedin", "bluehost", "blaze.ai", "perplexity", "canva", "lastpass", "workspace", "hushed.com", "turboscribe"]):
        return "Subscriptions/Services"
    if any(word in desc for word in ["fee", "intl. transaction", "service charge", "charge"]):
        return "Fees"
    if any(word in desc for word in ["verify", "acctverify"]):
        return "Verification"
    if "customer id" in desc:
        return "Transfers"
    return "Uncategorized"

def parsear_chase(texto, nombre_archivo):
    periodo_pat = re.search(
    r'([A-Za-z]{3,9} \d{2}, \d{4})\s*through\s*([A-Za-z]{3,9} \d{2}, \d{4})',
    texto.replace('\n', '').replace('\r', '')
)
    if periodo_pat:
        try:
            fecha_inicio = datetime.strptime(periodo_pat.group(1), "%b %d, %Y").date()
            fecha_fin = datetime.strptime(periodo_pat.group(2), "%b %d, %Y").date()
        except Exception as e:
            fecha_inicio = None
            fecha_fin = None

    saldo_inicial_pat = re.search(r'Beginning Balance \$?([0-9,]+\.\d{2})', texto)
    saldo_inicial = float(saldo_inicial_pat.group(1).replace(",", "")) if saldo_inicial_pat else None
    saldo_final_pat = re.search(r'Ending Balance \d* \$?([0-9,]+\.\d{2})', texto)
    saldo_final = float(saldo_final_pat.group(1).replace(",", "")) if saldo_final_pat else None

    banco = "Chase"
    extracto_id = generar_extracto_id(banco, fecha_inicio, fecha_fin, saldo_inicial, saldo_final, nombre_archivo)
    movimientos = []

    mov_pat = re.compile(r'(\d{2}/\d{2})(.+?)\$(\d{1,3}(?:,\d{3})*\.\d{2})', re.DOTALL)
    for match in mov_pat.finditer(texto):
        # Si no hay fecha_inicio, no se puede armar la fecha completa
        if fecha_inicio is not None:
            try:
                fecha_raw = match.group(1) + f"/{fecha_inicio.year}"
                fecha = datetime.strptime(fecha_raw, "%m/%d/%Y").date()
            except Exception:
                fecha = None
        else:
            fecha = None
        linea_completa = match.group(2).strip()
        try:
            monto = float(match.group(3).replace(",", ""))
        except Exception:
            monto = None
        tipo = "ingreso" if (monto is not None and monto > 0) else "egreso"

        descripcion = linea_completa

        categoria = categorizar_movimiento(descripcion)

        movimiento_id = generar_id_compuesto(fecha, banco, descripcion, monto)
        movimientos.append({
            "id": movimiento_id,
            "fecha": fecha,
            "banco": banco,
            "monto": monto,
            "tipo": tipo,
            "descripción": descripcion,
            "categoría": categoria,
            "extracto_id": extracto_id,
            "origen_dato": nombre_archivo
        })

    df_movimientos = pd.DataFrame(movimientos)

    total_ingresos = df_movimientos[df_movimientos["tipo"]=="ingreso"]["monto"].sum() if not df_movimientos.empty else 0
    total_egresos = df_movimientos[df_movimientos["tipo"]=="egreso"]["monto"].sum() if not df_movimientos.empty else 0

    df_extractos = pd.DataFrame([{
        "extracto_id": extracto_id,
        "banco": banco,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "saldo_inicial": saldo_inicial,
        "saldo_final": saldo_final,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "archivo_fuente": nombre_archivo
    }])

    return df_movimientos, df_extractos

def parsear_mercury(texto, nombre_archivo):
    # --------- EXTRAER FECHAS DEL PERÍODO ---------
    periodo_pat = re.search(r'([A-Za-z]+) (\d{4}) statement', texto)
    fecha_inicio = None
    fecha_fin = None
    anio = None
    if periodo_pat:
        mes = periodo_pat.group(1)
        anio = int(periodo_pat.group(2))
        fecha_inicio = datetime.strptime(f"{mes} 01, {anio}", "%B %d, %Y").date()
        # Buscar último día del mes en el encabezado del extracto
        last_day_pat = re.search(rf'{mes} {anio}-{mes} (\d{{1,2}}), {anio}', texto)
        if last_day_pat:
            last_day = int(last_day_pat.group(1))
            fecha_fin = datetime.strptime(f"{mes} {last_day}, {anio}", "%B %d, %Y").date()
        else:
            # fallback por si el patrón del último día no aparece
            if mes in ["January", "March", "May", "July", "August", "October", "December"]:
                fecha_fin = datetime.strptime(f"{mes} 31, {anio}", "%B %d, %Y").date()
            elif mes == "February":
                fecha_fin = datetime.strptime(f"{mes} 28, {anio}", "%B %d, %Y").date()
            else:
                fecha_fin = datetime.strptime(f"{mes} 30, {anio}", "%B %d, %Y").date()

    # --------- EXTRAER SALDOS ---------
    saldo_inicial_pat = re.search(r'Beginning Balance \$([0-9,]+\.\d{2})', texto)
    saldo_inicial = float(saldo_inicial_pat.group(1).replace(",", "")) if saldo_inicial_pat else None
    saldo_final_pat = re.search(r'Statement balance \$([0-9,]+\.\d{2})', texto)
    saldo_final = float(saldo_final_pat.group(1).replace(",", "")) if saldo_final_pat else None

    banco = "Mercury"
    extracto_id = generar_extracto_id(banco, fecha_inicio, fecha_fin, saldo_inicial, saldo_final, nombre_archivo)
    movimientos = []

    # --------- EXTRAER MOVIMIENTOS ---------
    mov_pat = re.compile(
        r'(?:(?P<fecha>[A-Za-z]{3} \d{2})\s+)?'    # Fecha opcional (grupo 'fecha')
        r'(.+?)\s+'                                # Descripción (todo hasta monto)
        r'((?:–|-)?\$[0-9,]+\.\d{2})'              # Monto, puede ser negativo unicode o ASCII
        r'(?:\s+\$[0-9,]+\.\d{2})?'                # Balance final (opcional)
        r'(?:\n|$)', re.MULTILINE)

    anio_mov = anio if anio else (fecha_inicio.year if fecha_inicio else 2025)
    last_fecha = None

    for match in mov_pat.finditer(texto):
        fecha_encontrada = match.group('fecha')
        if fecha_encontrada:
            last_fecha = fecha_encontrada
        if not last_fecha:
            continue
        fecha_str = f"{last_fecha}, {anio_mov}"
        try:
            fecha = datetime.strptime(fecha_str, "%b %d, %Y").date()
        except ValueError:
            fecha = None
        descripcion = match.group(2).strip()
        # Limpiar símbolos de iconos unicode visuales (no útiles para categorización)
        descripcion = re.sub(r'[]', '', descripcion)
        monto_raw = match.group(3).replace("–", "-").replace("$", "").replace(",", "")
        try:
            monto = float(monto_raw)
        except ValueError:
            monto = None
        tipo = "egreso" if monto is not None and monto < 0 else "ingreso"
        categoria = categorizar_movimiento(descripcion)
        movimiento_id = generar_id_compuesto(fecha, banco, descripcion, monto)
        movimientos.append({
            "id": movimiento_id,
            "fecha": fecha,
            "banco": banco,
            "monto": abs(monto) if monto is not None else None,
            "tipo": tipo,
            "descripción": descripcion,
            "categoría": categoria,
            "extracto_id": extracto_id,
            "origen_dato": nombre_archivo
        })

    # --------- FILTRAR FILAS COMO "Total" O "Statement Total" -----------
    movimientos = [
        m for m in movimientos
        if m["descripción"].strip().lower() not in ["total", "statement total", "balance"]
    ]

    df_movimientos = pd.DataFrame(movimientos)
    total_ingresos = df_movimientos[df_movimientos["tipo"]=="ingreso"]["monto"].sum() if not df_movimientos.empty else 0
    total_egresos = df_movimientos[df_movimientos["tipo"]=="egreso"]["monto"].sum() if not df_movimientos.empty else 0

    df_extractos = pd.DataFrame([{
        "extracto_id": extracto_id,
        "banco": banco,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "saldo_inicial": saldo_inicial,
        "saldo_final": saldo_final,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "archivo_fuente": nombre_archivo
    }])

    return df_movimientos, df_extractos

def parsear_truist(texto, nombre_archivo):
    saldo_inicial_pat = re.search(r'Yourpreviousbalanceasof(\d{2}/\d{2}/\d{4}) \$([0-9,]+\.\d{2})', texto)
    saldo_final_pat = re.search(r'Yournewbalanceasof(\d{2}/\d{2}/\d{4}) =\$([0-9,]+\.\d{2})', texto)

    fecha_inicio = datetime.strptime(saldo_inicial_pat.group(1), "%m/%d/%Y").date() if saldo_inicial_pat else None
    fecha_fin = datetime.strptime(saldo_final_pat.group(1), "%m/%d/%Y").date() if saldo_final_pat else None
    saldo_inicial = float(saldo_inicial_pat.group(2).replace(",", "")) if saldo_inicial_pat else None
    saldo_final = float(saldo_final_pat.group(2).replace(",", "")) if saldo_final_pat else None

    banco = "Truist"
    extracto_id = nombre_archivo
    movimientos = []

    header_egresos = "Otherwithdrawals,debitsandservicecharges\nDATE DESCRIPTION AMOUNT($)\n"
    header_ingresos = "Deposits,creditsandinterest\nDATE DESCRIPTION AMOUNT($)\n"
    total_egresos = "Totalotherwithdrawals,debitsandservicecharges ="
    total_ingresos = "Totaldeposits,creditsandinterest ="

    ini_egresos = texto.find(header_egresos)
    fin_egresos = texto.find(total_egresos)
    ini_ingresos = texto.find(header_ingresos)
    fin_ingresos = texto.find(total_ingresos)

    bloque_egresos = texto[ini_egresos+len(header_egresos):fin_egresos] if ini_egresos!=-1 and fin_egresos!=-1 else ""
    bloque_ingresos = texto[ini_ingresos+len(header_ingresos):fin_ingresos] if ini_ingresos!=-1 and fin_ingresos!=-1 else ""

    # Procesar EGRESOS
    for linea in bloque_egresos.strip().split('\n'):
        match = re.match(r'(\d{2}/\d{2}) (.+) ([0-9,]+\.\d{2})', linea.strip())
        if match:
            fecha_str = f"{fecha_inicio.year}/{match.group(1)}" if fecha_inicio else f"2025/{match.group(1)}"
            fecha = datetime.strptime(fecha_str, "%Y/%m/%d").date()
            descripcion = match.group(2).strip()
            monto = float(match.group(3).replace(",", ""))
            categoria = categorizar_movimiento(descripcion)
            movimiento_id = f"{fecha}-{banco}-{descripcion}-{monto}"
            movimientos.append({
                "id": movimiento_id,
                "fecha": fecha,
                "banco": banco,
                "monto": monto,
                "tipo": "egreso",
                "descripción": descripcion,
                "categoría": categoria,
                "extracto_id": extracto_id,
                "origen_dato": nombre_archivo
            })

    # Procesar INGRESOS
    for linea in bloque_ingresos.strip().split('\n'):
        match = re.match(r'(\d{2}/\d{2}) (.+) ([0-9,]+\.\d{2})', linea.strip())
        if match:
            fecha_str = f"{fecha_inicio.year}/{match.group(1)}" if fecha_inicio else f"2025/{match.group(1)}"
            fecha = datetime.strptime(fecha_str, "%Y/%m/%d").date()
            descripcion = match.group(2).strip()
            monto = float(match.group(3).replace(",", ""))
            categoria = categorizar_movimiento(descripcion)
            movimiento_id = f"{fecha}-{banco}-{descripcion}-{monto}"
            movimientos.append({
                "id": movimiento_id,
                "fecha": fecha,
                "banco": banco,
                "monto": monto,
                "tipo": "ingreso",
                "descripción": descripcion,
                "categoría": categoria,
                "extracto_id": extracto_id,
                "origen_dato": nombre_archivo
            })

    df_movimientos = pd.DataFrame(movimientos)
    total_ingresos = df_movimientos[df_movimientos["tipo"] == "ingreso"]["monto"].sum() if not df_movimientos.empty else 0
    total_egresos = df_movimientos[df_movimientos["tipo"] == "egreso"]["monto"].sum() if not df_movimientos.empty else 0

    df_extractos = pd.DataFrame([{
        "extracto_id": extracto_id,
        "banco": banco,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "saldo_inicial": saldo_inicial,
        "saldo_final": saldo_final,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "archivo_fuente": nombre_archivo
    }])

    return df_movimientos, df_extractos

def parsear_wise_usd(texto, nombre_archivo):
    periodo_pat = re.search(r'USD statement\n(\d{1,2} [A-Za-z]+ \d{4}) \[GMT.*?\] - (\d{1,2} [A-Za-z]+ \d{4}) \[GMT', texto, re.IGNORECASE)
    fecha_inicio = datetime.strptime(periodo_pat.group(1), "%d %B %Y").date() if periodo_pat else None
    fecha_fin = datetime.strptime(periodo_pat.group(2), "%d %B %Y").date() if periodo_pat else None

    saldo_final_pat = re.search(r'USD balance on [\d ]+[A-Za-z]+ \d{4} \[GMT.*?\] ([0-9,]+\.\d{2}) USD', texto)
    saldo_final = float(saldo_final_pat.group(1).replace(",", "")) if saldo_final_pat else None

    banco = "Wise USD"
    extracto_id = nombre_archivo
    movimientos = []

    # --------- RECORRIDO LÍNEA A LÍNEA ---------
    lines = texto.split('\n')
    i = 0
    while i < len(lines) - 1:
        mov_line = lines[i].strip()
        next_line = lines[i+1].strip()

        # ¿Esta línea es movimiento y la siguiente es fecha?
        mov_pat = re.compile(r'^(.+?)\s+(-?[0-9,]+\.\d{2})\s+([0-9,]+\.\d{2})$')
        fecha_pat = re.match(r'(\d{1,2} [A-Za-z]+ \d{4}) Transaction:', next_line)
        match = mov_pat.match(mov_line)
        if match and fecha_pat:
            descripcion = match.group(1).strip()
            monto = float(match.group(2).replace(",", ""))
            balance = float(match.group(3).replace(",", ""))
            try:
                fecha = datetime.strptime(fecha_pat.group(1), "%d %B %Y").date()
            except Exception:
                fecha = None
            # Mejor tipo usando descripción
            if "received money from" in descripcion.lower() or monto > 0:
                tipo = "ingreso"
            elif "sent money to" in descripcion.lower() or "converted usd" in descripcion.lower() or monto < 0:
                tipo = "egreso"
            elif "wise charges" in descripcion.lower() or "fee" in descripcion.lower():
                tipo = "egreso"
            else:
                tipo = "egreso" if monto < 0 else "ingreso"

            categoria = categorizar_movimiento(descripcion)
            movimiento_id = f"{fecha}-{banco}-{descripcion}-{monto}"
            movimientos.append({
                "id": movimiento_id,
                "fecha": fecha,
                "banco": banco,
                "monto": abs(monto),
                "tipo": tipo,
                "descripción": descripcion,
                "categoría": categoria,
                "extracto_id": extracto_id,
                "origen_dato": nombre_archivo,
                "balance": balance
            })
            i += 2  # Salta ambas líneas
        else:
            i += 1  # Avanza solo una línea

    df_movimientos = pd.DataFrame(movimientos)
    saldo_inicial = df_movimientos["balance"].iloc[-1] if (not df_movimientos.empty and "balance" in df_movimientos.columns) else None
    if "balance" in df_movimientos.columns:
        df_movimientos = df_movimientos.drop(columns=["balance"])

    total_ingresos = df_movimientos[df_movimientos["tipo"]=="ingreso"]["monto"].sum() if not df_movimientos.empty else 0
    total_egresos = df_movimientos[df_movimientos["tipo"]=="egreso"]["monto"].sum() if not df_movimientos.empty else 0

    df_extractos = pd.DataFrame([{
        "extracto_id": extracto_id,
        "banco": banco,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "saldo_inicial": saldo_inicial,
        "saldo_final": saldo_final,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "archivo_fuente": nombre_archivo
    }])

    return df_movimientos, df_extractos

def parsear_wise_eur(texto, nombre_archivo):
    # --------- EXTRAER PERIODO Y SALDO FINAL ---------
    # Regex robusto para periodo (tolera saltos de línea y cualquier zona horaria)
    periodo_pat = re.search(
        r"EUR statement\s*\n\s*(\d{1,2} [A-Za-z]+ \d{4}) \[GMT[^\]]*\] - (\d{1,2} [A-Za-z]+ \d{4}) \[GMT[^\]]*\]",
        texto, 
        re.IGNORECASE
    )
    fecha_inicio = datetime.strptime(periodo_pat.group(1), "%d %B %Y").date() if periodo_pat else None
    fecha_fin = datetime.strptime(periodo_pat.group(2), "%d %B %Y").date() if periodo_pat else None

    saldo_final_pat = re.search(
        r"EUR balance on [\d ]+[A-Za-z]+ \d{4} \[GMT[^\]]*\] ([0-9,]+\.\d{2}) EUR", 
        texto
    )
    saldo_final = float(saldo_final_pat.group(1).replace(",", "")) if saldo_final_pat else None

    banco = "Wise EUR"
    extracto_id = nombre_archivo
    movimientos = []

    # --------- RECORRIDO LÍNEA A LÍNEA (igual que Wise USD) ---------
    lines = texto.split('\n')
    i = 0
    while i < len(lines) - 1:
        mov_line = lines[i].strip()
        next_line = lines[i+1].strip()

        mov_pat = re.compile(r'^(.+?)\s+(-?[0-9,]+\.\d{2})\s+([0-9,]+\.\d{2})$')
        fecha_pat = re.match(r'(\d{1,2} [A-Za-z]+ \d{4}) Transaction:', next_line)
        match = mov_pat.match(mov_line)
        if match and fecha_pat:
            descripcion = match.group(1).strip()
            monto = float(match.group(2).replace(",", ""))
            balance = float(match.group(3).replace(",", ""))
            try:
                fecha = datetime.strptime(fecha_pat.group(1), "%d %B %Y").date()
            except Exception:
                fecha = None

            # Mejor lógica de tipo usando descripción y monto
            desc_lower = descripcion.lower()
            if "received money from" in desc_lower or monto > 0:
                tipo = "ingreso"
            elif "sent money to" in desc_lower or "converted usd" in desc_lower or monto < 0:
                tipo = "egreso"
            elif "wise charges" in desc_lower or "fee" in desc_lower:
                tipo = "egreso"
            else:
                tipo = "egreso" if monto < 0 else "ingreso"

            categoria = categorizar_movimiento(descripcion)
            movimiento_id = f"{fecha}-{banco}-{descripcion}-{monto}"
            movimientos.append({
                "id": movimiento_id,
                "fecha": fecha,
                "banco": banco,
                "monto": abs(monto),
                "tipo": tipo,
                "descripción": descripcion,
                "categoría": categoria,
                "extracto_id": extracto_id,
                "origen_dato": nombre_archivo,
                "balance": balance
            })
            i += 2  # Salta ambas líneas
        else:
            i += 1  # Avanza solo una línea

    df_movimientos = pd.DataFrame(movimientos)
    saldo_inicial = df_movimientos["balance"].iloc[-1] if (not df_movimientos.empty and "balance" in df_movimientos.columns) else None
    if "balance" in df_movimientos.columns:
        df_movimientos = df_movimientos.drop(columns=["balance"])

    total_ingresos = df_movimientos[df_movimientos["tipo"]=="ingreso"]["monto"].sum() if not df_movimientos.empty else 0
    total_egresos = df_movimientos[df_movimientos["tipo"]=="egreso"]["monto"].sum() if not df_movimientos.empty else 0

    df_extractos = pd.DataFrame([{
        "extracto_id": extracto_id,
        "banco": banco,  # <<--- Ahora siempre será "Wise EUR"
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "saldo_inicial": saldo_inicial,
        "saldo_final": saldo_final,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "archivo_fuente": nombre_archivo
    }])

    return df_movimientos, df_extractos
