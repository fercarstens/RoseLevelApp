import datetime
import tempfile
import io

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from reportlab.pdfgen import canvas

from modules.drive_utils import subir_a_drive

def render(movimientos_df, extractos_df):
    st.title("📈 Reportes Avanzados")
    st.caption("Genera reportes personalizados, análisis financieros y conciliaciones bancarias.")

    # --- Procesamiento de DataFrames
    movimientos_df['tipo'] = movimientos_df['tipo'].astype(str).fillna('')
    movimientos_df['fecha'] = pd.to_datetime(movimientos_df['fecha'], errors="coerce")
    ingresos_df = movimientos_df[movimientos_df['tipo'].str.lower() == 'ingreso'].copy()
    egresos_df = movimientos_df[movimientos_df['tipo'].str.lower() == 'egreso'].copy()

    # --- Extractos: procesar fechas y validar
    if extractos_df is not None and not extractos_df.empty:
        extractos_df['fecha_inicio'] = pd.to_datetime(extractos_df['fecha_inicio'], errors="coerce")
        extractos_df['fecha_fin'] = pd.to_datetime(extractos_df['fecha_fin'], errors="coerce")
        extractos_df['saldo_inicial'] = pd.to_numeric(extractos_df['saldo_inicial'], errors="coerce")
        extractos_df['saldo_final'] = pd.to_numeric(extractos_df['saldo_final'], errors="coerce")

    # --- Filtros
    st.sidebar.subheader("Filtros de Reporte")
    fecha_min = movimientos_df["fecha"].min() if not movimientos_df.empty else datetime.date.today() - datetime.timedelta(days=180)
    fecha_max = movimientos_df["fecha"].max() if not movimientos_df.empty else datetime.date.today()
    fecha_desde = st.sidebar.date_input("Desde", value=fecha_min.date(), key="report_fecha_desde")
    fecha_hasta = st.sidebar.date_input("Hasta", value=fecha_max.date(), key="report_fecha_hasta")
    bancos_disp = movimientos_df['banco'].dropna().unique()
    banco_sel = st.sidebar.multiselect("Banco", bancos_disp, default=list(bancos_disp))
    categorias_disp = movimientos_df['categoría'].dropna().unique()
    categoria_sel = st.sidebar.multiselect("Categoría", categorias_disp, default=list(categorias_disp))

    # --- Aplicar filtros
    mov_filtrados = movimientos_df[
        (movimientos_df["fecha"] >= pd.Timestamp(fecha_desde)) &
        (movimientos_df["fecha"] <= pd.Timestamp(fecha_hasta)) &
        (movimientos_df["banco"].isin(banco_sel)) &
        (movimientos_df["categoría"].isin(categoria_sel))
    ]
    ingresos_filtrados = mov_filtrados[mov_filtrados['tipo'].str.lower() == 'ingreso']
    egresos_filtrados = mov_filtrados[mov_filtrados['tipo'].str.lower() == 'egreso']

    # --- Tabs de reporte
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📅 Resumen Mensual", 
        "📊 Análisis por Categoría", 
        "🏦 Conciliación Extractos", 
        "👥 Cliente/Proveedor", 
        "📤 Exportar"
    ])

    # === Tab 1: Resumen Mensual
    with tab1:
        st.subheader("Resumen Financiero Mensual")
        if not mov_filtrados.empty:
            resumen_mensual = mov_filtrados.pivot_table(
                index=mov_filtrados['fecha'].dt.to_period('M').astype(str),
                columns='tipo',
                values='monto',
                aggfunc='sum'
            ).fillna(0)
            resumen_mensual['Balance'] = resumen_mensual.get('ingreso', 0) - resumen_mensual.get('egreso', 0)
            resumen_mensual['Margen (%)'] = np.where(
                resumen_mensual.get('ingreso', 0) > 0,
                (resumen_mensual['Balance'] / resumen_mensual['ingreso']) * 100,
                0
            )
            st.dataframe(
                resumen_mensual.style.format({
                    'ingreso': '${:,.2f}',
                    'egreso': '${:,.2f}',
                    'Balance': '${:,.2f}',
                    'Margen (%)': '{:.1f}%'
                }), use_container_width=True
            )
            fig, ax = plt.subplots(figsize=(10, 6))
            resumen_mensual[['ingreso', 'egreso']].plot(kind="bar", ax=ax)
            ax.set_title("Evolución Mensual de Ingresos y Egresos")
            ax.set_ylabel("Monto ($)")
            ax.grid(True, linestyle="--", alpha=0.7)
            st.pyplot(fig)
        else:
            st.warning("No hay movimientos financieros para el período y filtros seleccionados.")

    # === Tab 2: Análisis por Categoría
    with tab2:
        st.subheader("Análisis por Categoría")

        tipo_analisis = st.radio("¿Qué analizar?", ["Egresos", "Ingresos"], horizontal=True)

        if tipo_analisis == "Egresos":
            df_tipo = egresos_filtrados
            color = 'red'
            kpi_label = "Total Egresos"
        else:
            df_tipo = ingresos_filtrados
            color = 'green'
            kpi_label = "Total Ingresos"

        if df_tipo.empty:
            st.warning(f"No hay {tipo_analisis.lower()} para analizar.")
        else:
            total = df_tipo["monto"].sum()
            cat_summary = df_tipo.groupby("categoría").agg(
                Total=("monto", "sum"),
                Cantidad=("monto", "count")
            ).sort_values("Total", ascending=False)
            cat_summary["Porcentaje"] = (cat_summary["Total"] / total) * 100

            top_cat = cat_summary.index[0] if not cat_summary.empty else "N/A"
            top_cat_val = cat_summary["Total"].iloc[0] if not cat_summary.empty else 0

            colK1, colK2 = st.columns(2)
            colK1.metric(kpi_label, f"${total:,.2f}")
            colK2.metric("Top Categoría", f"{top_cat} (${top_cat_val:,.2f})")

            st.dataframe(
                cat_summary.style.format({
                    "Total": "${:,.2f}",
                    "Porcentaje": "{:.1f}%"
                }), use_container_width=True
            )

            # Pie con “Otros”
            pie_data = cat_summary.copy()
            otros = pie_data[pie_data["Porcentaje"] < 4]["Total"].sum()
            pie_data = pie_data[pie_data["Porcentaje"] >= 4]
            if otros > 0:
                pie_data.loc["Otros"] = [otros, pie_data["Cantidad"].sum(), 100 * otros / total]
            fig, ax = plt.subplots(figsize=(5,5))
            pie_data["Total"].plot.pie(
                labels=pie_data.index,
                autopct="%1.1f%%",
                ax=ax,
                startangle=140,
                counterclock=False
            )
            ax.set_ylabel("")
            st.pyplot(fig)

            # Barras horizontal
            fig2, ax2 = plt.subplots(figsize=(6,5))
            cat_summary["Total"].plot.barh(ax=ax2)
            ax2.set_xlabel("Monto ($)")
            ax2.set_ylabel("Categoría")
            st.pyplot(fig2)

            # Detalle interactivo
            st.markdown("---")
            categoria_selec = st.selectbox("Selecciona una categoría para ver detalle", cat_summary.index)
            df_detalle = df_tipo[df_tipo["categoría"] == categoria_selec]
            st.markdown(f"**Detalle de '{categoria_selec}':**")
            st.markdown(f"- Total: **${df_detalle['monto'].sum():,.2f}**")
            st.markdown(f"- N° transacciones: **{df_detalle.shape[0]}**")
            st.markdown(f"- Promedio por transacción: **${df_detalle['monto'].mean():,.2f}**")

            # Top 5 fuente/cliente/proveedor/desc
            if tipo_analisis == "Ingresos" and "fuente" in df_detalle.columns:
                top5 = df_detalle["fuente"].value_counts().head(5)
                st.markdown("**Top 5 fuentes:**")
            elif tipo_analisis == "Egresos" and "proveedor" in df_detalle.columns:
                top5 = df_detalle["proveedor"].value_counts().head(5)
                st.markdown("**Top 5 proveedores:**")
            else:
                top5 = df_detalle["descripción"].value_counts().head(5)
                st.markdown("**Top 5 descripciones:**")
            for i, (desc, cnt) in enumerate(top5.items(), 1):
                st.write(f"{i}. {desc} ({cnt} veces)")

            # Evolución mensual
            st.write("**Evolución mensual de la categoría seleccionada:**")
            df_mes = df_detalle.copy()
            df_mes["mes"] = df_mes["fecha"].dt.strftime("%Y-%m")
            df_mensual = df_mes.groupby("mes")["monto"].sum()
            st.bar_chart(df_mensual)

            # Exportar
            st.download_button(
                f"📥 Descargar {tipo_analisis.lower()} '{categoria_selec}' (CSV)",
                data=df_detalle.to_csv(index=False).encode('utf-8'),
                file_name=f"{tipo_analisis.lower()}_{categoria_selec}.csv",
                mime="text/csv"
            )

    # === Tab 3: Conciliación Extractos
    with tab3:
        st.subheader("Conciliación de Extractos Bancarios")
        if extractos_df is not None and not extractos_df.empty:
            cols = ["banco", "fecha_inicio", "fecha_fin", "saldo_inicial", "saldo_final", "total_ingresos", "total_egresos", "archivo_fuente"]
            st.dataframe(extractos_df[cols], use_container_width=True)
            # Conciliación rápida
            for _, row in extractos_df.iterrows():
                movs_periodo = movimientos_df[
                    (movimientos_df["banco"] == row["banco"]) &
                    (movimientos_df["fecha"] >= row["fecha_inicio"]) &
                    (movimientos_df["fecha"] <= row["fecha_fin"])
                ]
                ingresos = movs_periodo[movs_periodo["tipo"].str.lower() == "ingreso"]["monto"].sum()
                egresos = movs_periodo[movs_periodo["tipo"].str.lower() == "egreso"]["monto"].sum()
                calculado = row["saldo_inicial"] + ingresos - egresos if not pd.isna(row["saldo_inicial"]) else None
                if not pd.isna(row["saldo_final"]) and calculado is not None:
                    diff = row["saldo_final"] - calculado
                    if abs(diff) < 0.01:
                        st.success(f"✅ Extracto '{row['archivo_fuente']}' **CONCILIADO**.")
                    else:
                        st.warning(f"⚠️ Extracto '{row['archivo_fuente']}': Diferencia detectada de ${diff:,.2f}.")
        else:
            st.info("No hay extractos disponibles para conciliación.")

    # === Tab 4: Cliente/Proveedor
    with tab4:
        st.subheader("Análisis por Cliente/Proveedor")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Top 5 Clientes (Ingresos)**")
            if "fuente" in ingresos_filtrados.columns and not ingresos_filtrados.empty:
                top_clientes = ingresos_filtrados.groupby("fuente")["monto"].sum().sort_values(ascending=False).head(5)
                st.dataframe(
                    top_clientes.reset_index().rename(columns={"fuente": "Cliente", "monto": "Total"}).style.format({"Total": "${:,.2f}"}),
                    use_container_width=True
                )
                fig, ax = plt.subplots(figsize=(6, 4))
                top_clientes.plot(kind="barh", ax=ax)
                ax.set_title("Principales Clientes")
                ax.set_xlabel("Monto ($)")
                st.pyplot(fig)
            else:
                st.info("No hay datos de fuente en ingresos.")
        with col2:
            st.markdown("**Top 5 Proveedores (Egresos)**")
            if "proveedor" in egresos_filtrados.columns and not egresos_filtrados.empty:
                top_proveedores = egresos_filtrados.groupby("proveedor")["monto"].sum().sort_values(ascending=False).head(5)
                st.dataframe(
                    top_proveedores.reset_index().rename(columns={"proveedor": "Proveedor", "monto": "Total"}).style.format({"Total": "${:,.2f}"}),
                    use_container_width=True
                )
                fig, ax = plt.subplots(figsize=(6, 4))
                top_proveedores.plot(kind="barh", ax=ax, color="orange")
                ax.set_title("Principales Proveedores")
                ax.set_xlabel("Monto ($)")
                st.pyplot(fig)
            else:
                st.info("No hay datos de proveedor en egresos.")


    # === Tab 5: Exportar Datos
    with tab5:
        st.subheader("Exportar Datos Filtrados")

        # Subset para exportar (con los mismos filtros aplicados)
        ingresos_export = mov_filtrados[mov_filtrados["tipo"].str.lower() == "ingreso"]
        egresos_export = mov_filtrados[mov_filtrados["tipo"].str.lower() == "egreso"]
        extractos_filtrados = extractos_df[
            (extractos_df["fecha_inicio"] >= pd.Timestamp(fecha_desde)) &
            (extractos_df["fecha_fin"] <= pd.Timestamp(fecha_hasta)) &
            (extractos_df["banco"].isin(banco_sel))
        ].copy()

        # KPIs rápidos
        col1, col2, col3 = st.columns(3)
        col1.metric("Ingresos", f"${ingresos_export['monto'].sum():,.2f}")
        col2.metric("Egresos", f"${egresos_export['monto'].sum():,.2f}")
        col3.metric("Extractos", f"{extractos_filtrados.shape[0]}")
        st.caption(
            f"Bancos filtrados: {', '.join(map(str, banco_sel))} | "
            f"Categorías: {', '.join(map(str, categoria_sel))}"
        )

        st.divider()
        st.markdown("### Ingresos filtrados")
        if not ingresos_export.empty:
            st.dataframe(ingresos_export.head(), use_container_width=True)
            st.download_button(
                "📥 Descargar Ingresos (CSV)",
                ingresos_export.to_csv(index=False).encode("utf-8"),
                "ingresos_export.csv"
            )
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                ingresos_export.to_excel(writer, index=False)
            st.download_button(
                "📊 Descargar Ingresos (Excel)",
                output.getvalue(),
                "ingresos_export.xlsx"
            )
        else:
            st.info("No hay ingresos filtrados para exportar.")

        st.divider()
        st.markdown("### Egresos filtrados")
        if not egresos_export.empty:
            st.dataframe(egresos_export.head(), use_container_width=True)
            st.download_button(
                "📥 Descargar Egresos (CSV)",
                egresos_export.to_csv(index=False).encode("utf-8"),
                "egresos_export.csv"
            )
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                egresos_export.to_excel(writer, index=False)
            st.download_button(
                "📊 Descargar Egresos (Excel)",
                output.getvalue(),
                "egresos_export.xlsx"
            )
        else:
            st.info("No hay egresos filtrados para exportar.")

        st.divider()
        st.markdown("### Extractos filtrados")
        if not extractos_filtrados.empty:
            st.dataframe(extractos_filtrados.head(), use_container_width=True)
            st.download_button(
                "📥 Descargar Extractos (CSV)",
                extractos_filtrados.to_csv(index=False).encode("utf-8"),
                "extractos_export.csv"
            )
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                extractos_filtrados.to_excel(writer, index=False)
            st.download_button(
                "📊 Descargar Extractos (Excel)",
                output.getvalue(),
                "extractos_export.xlsx"
            )
        else:
            st.info("No hay extractos filtrados para exportar.")


"""
    with tab5:
        st.subheader("Exportar Datos Completos")
        col1, col2 = st.columns(2)
        # Exportar ingresos
        with col1:
            st.write("**Exportar Ingresos**")
            if not ingresos_filtrados.empty:
                csv_data = ingresos_filtrados.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar CSV", data=csv_data, file_name=f"ingresos_{fecha_desde}_{fecha_hasta}.csv", mime="text/csv")
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    ingresos_filtrados.to_excel(writer, index=False)
                st.download_button("📊 Descargar Excel", data=output.getvalue(), file_name=f"ingresos_{fecha_desde}_{fecha_hasta}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("No hay ingresos para exportar.")
        # Exportar egresos
        with col2:
            st.write("**Exportar Egresos**")
            if not egresos_filtrados.empty:
                csv_data = egresos_filtrados.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar CSV", data=csv_data, file_name=f"egresos_{fecha_desde}_{fecha_hasta}.csv", mime="text/csv")
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    egresos_filtrados.to_excel(writer, index=False)
                st.download_button("📊 Descargar Excel", data=output.getvalue(), file_name=f"egresos_{fecha_desde}_{fecha_hasta}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("No hay egresos para exportar.")

        st.divider()
        st.write("**Resumen Financiero PDF**")
        if not ingresos_filtrados.empty or not egresos_filtrados.empty:
            resumen = f'''Resumen Financiero
Período: {fecha_desde} a {fecha_hasta}
Ingresos totales: ${ingresos_filtrados['monto'].sum():,.2f}
Egresos totales: ${egresos_filtrados['monto'].sum():,.2f}
Balance: ${ingresos_filtrados['monto'].sum() - egresos_filtrados['monto'].sum():,.2f}
'''
            st.download_button(
                "📄 Descargar Resumen (TXT)",
                data=resumen.encode(),
                file_name="resumen_financiero.txt",
                mime="text/plain"
            )
            if st.button("📤 Subir Resumen PDF a Drive"):
                try:
                    buffer = io.BytesIO()
                    p = canvas.Canvas(buffer)
                    p.drawString(100, 800, "Resumen Financiero")
                    p.drawString(100, 780, f"Período: {fecha_desde} a {fecha_hasta}")
                    p.drawString(100, 760, f"Ingresos totales: ${ingresos_filtrados['monto'].sum():,.2f}")
                    p.drawString(100, 740, f"Egresos totales: ${egresos_filtrados['monto'].sum():,.2f}")
                    p.drawString(100, 720, f"Balance: ${ingresos_filtrados['monto'].sum() - egresos_filtrados['monto'].sum():,.2f}")
                    # Puedes agregar detalles de extractos aquí si lo deseas
                    p.save()
                    pdf_data = buffer.getvalue()
                    success, file_id = subir_a_drive(f"resumen_financiero_{fecha_desde}_{fecha_hasta}.pdf", pdf_data, "application/pdf")
                    if success:
                        st.success(f"Resumen PDF subido: [Abrir](https://drive.google.com/file/d/{file_id}/view)")
                    else:
                        st.error("Error al subir el archivo a Drive")
                except Exception as e:
                    st.error(f"Error al generar o subir el PDF: {str(e)}")
        else:
            st.info("No hay datos suficientes para generar resumen en PDF")
"""