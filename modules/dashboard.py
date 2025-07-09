import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from wordcloud import WordCloud, STOPWORDS

def render(movimientos_df, extractos_df):
    st.title("📊 Dashboard Financiero")

    # --- Limpieza y preparación ---
    movimientos_df = movimientos_df.copy()
    movimientos_df['tipo'] = movimientos_df['tipo'].astype(str).fillna('')
    movimientos_df['banco'] = movimientos_df['banco'].astype(str).fillna('')
    movimientos_df['fecha'] = pd.to_datetime(movimientos_df['fecha'], errors='coerce')
    movimientos_df['monto'] = pd.to_numeric(movimientos_df['monto'], errors='coerce')
    movimientos_df['categoría'] = movimientos_df['categoría'].fillna('Sin Categoría')

    extractos_df = extractos_df.copy()
    extractos_df['saldo_final'] = pd.to_numeric(extractos_df['saldo_final'], errors='coerce')
    extractos_df['saldo_inicial'] = pd.to_numeric(extractos_df['saldo_inicial'], errors='coerce')
    extractos_df['fecha_fin'] = pd.to_datetime(extractos_df['fecha_fin'], errors='coerce')
    extractos_df['fecha_inicio'] = pd.to_datetime(extractos_df['fecha_inicio'], errors='coerce')

    # --- Filtros interactivos ---
    st.sidebar.header("Filtros")
    bancos = movimientos_df['banco'].unique().tolist()
    bancos = [b for b in bancos if b]
    bancos = sorted(bancos)
    bancos.insert(0, "Todos")
    banco_sel = st.sidebar.selectbox("Banco", bancos)

    # Filtro de fechas
    fecha_min = movimientos_df['fecha'].min()
    fecha_max = movimientos_df['fecha'].max()
    fecha_ini, fecha_fin = st.sidebar.date_input(
        "Rango de fechas",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max
    )

    # Filtro de categoría
    categorias = sorted(movimientos_df['categoría'].unique())
    categorias.insert(0, "Todas")
    categoria_sel = st.sidebar.selectbox("Categoría", categorias)

    # --- Aplicar filtros ---
    df = movimientos_df.copy()
    if banco_sel != "Todos":
        df = df[df['banco'] == banco_sel]
        ext_df = extractos_df[extractos_df['banco'] == banco_sel]
    else:
        ext_df = extractos_df

    df = df[(df['fecha'] >= pd.to_datetime(fecha_ini)) & (df['fecha'] <= pd.to_datetime(fecha_fin))]
    if categoria_sel != "Todas":
        df = df[df['categoría'] == categoria_sel]

    # --- KPIs ---
    total_ingresos = df[df['tipo'].str.lower() == 'ingreso']['monto'].sum()
    total_egresos = df[df['tipo'].str.lower() == 'egreso']['monto'].sum()
    balance = total_ingresos - total_egresos
    saldo_final_total = ext_df.sort_values('fecha_fin').groupby('banco')['saldo_final'].last().dropna().sum()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Ingresos", f"${total_ingresos:,.2f}")
    with col2:
        st.metric("Total Egresos", f"${total_egresos:,.2f}")
    with col3:
        st.metric("Balance Neto", f"${balance:,.2f}")
    with col4:
        st.metric("Saldo Bancos (actual)", f"${saldo_final_total:,.2f}")

    st.caption("El saldo bancario se calcula usando el último extracto disponible de cada banco.")

    st.divider()
    st.subheader("Distribución de Ingresos y Egresos por Banco")

    resumen = df.groupby(['banco', 'tipo'])['monto'].sum().unstack(fill_value=0)
    if not resumen.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        resumen.plot(kind='bar', ax=ax)
        ax.set_ylabel("Monto ($)")
        ax.set_title("Ingresos y Egresos por Banco")
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        ax.legend(title="Tipo de movimiento")
        st.pyplot(fig)
    else:
        st.info("No hay datos para mostrar en esta sección.")

    st.divider()
    st.subheader("Resumen por mes (Ingresos vs Egresos)")

    df["mes"] = df["fecha"].dt.strftime("%Y-%m")
    ingresos_mes = df[df['tipo'].str.lower() == 'ingreso'].groupby('mes')['monto'].sum()
    egresos_mes = df[df['tipo'].str.lower() == 'egreso'].groupby('mes')['monto'].sum()
    resumen_mes = pd.DataFrame({
        "Ingresos": ingresos_mes,
        "Egresos": egresos_mes
    }).fillna(0)
    if not resumen_mes.empty:
        st.line_chart(resumen_mes)
    else:
        st.info("No hay movimientos para mostrar tendencias mensuales.")

    st.divider()
    st.subheader("Saldos bancarios actuales (por banco)")
    tabla_saldos = ext_df.sort_values('fecha_fin').groupby('banco').last()[['saldo_final', 'fecha_fin']].dropna()
    tabla_saldos['saldo_final'] = tabla_saldos['saldo_final'].map("${:,.2f}".format)
    tabla_saldos = tabla_saldos.rename(columns={"saldo_final": "Saldo Final", "fecha_fin": "Fecha Corte"})
    st.dataframe(tabla_saldos, use_container_width=True)

    st.divider()
    st.subheader("Categorías donde más gastas (Egresos)")

    egresos = df[df['tipo'].str.lower() == 'egreso']

    if categoria_sel == "Todas":
        # ---- Gráfico de torta agrupando en "Otros" ---
        top_cats = (
            egresos
            .groupby('categoría')['monto']
            .sum()
            .sort_values(ascending=False)
        )
        total = top_cats.sum()
        porcentajes = (top_cats / total) * 100
        mask_otro = porcentajes < 1.5
        data_torta = top_cats.copy()
        if mask_otro.sum() > 1:  # Solo agrupa si hay al menos 2 'pequeñas'
            otros = data_torta[mask_otro].sum()
            data_torta = data_torta[~mask_otro]
            data_torta["Otros"] = otros

        if not data_torta.empty:
            fig2, ax2 = plt.subplots()
            ax2.pie(
                data_torta,
                labels=data_torta.index,
                autopct='%1.1f%%',
                startangle=140,
                counterclock=False
            )
            ax2.set_title("Distribución de egresos por categoría")
            st.pyplot(fig2)
        # --- Treemap de egresos por categoría ---
        egresos_all_cats = (
            egresos
            .groupby('categoría')['monto']
            .sum()
            .reset_index()
            .sort_values("monto", ascending=False)
        )
        if not egresos_all_cats.empty and egresos_all_cats['monto'].sum() > 0:
            fig_tree = px.treemap(
                egresos_all_cats,
                path=['categoría'],
                values='monto',
                title="Treemap de Egresos por Categoría",
                color='monto',
                color_continuous_scale='RdBu'
            )
            st.plotly_chart(fig_tree, use_container_width=True)
        else:
            st.info("No hay suficientes egresos para mostrar el treemap.")
    else:
        # --- Mostrar resumen relevante para la categoría seleccionada ---
        egresos_cat = df[(df['tipo'].str.lower() == 'egreso') & (df['categoría'] == categoria_sel)]
        total_cat = egresos_cat['monto'].sum()
        count_cat = egresos_cat.shape[0]
        avg_cat = egresos_cat['monto'].mean() if count_cat > 0 else 0

        st.markdown(f"**Total gastado en '{categoria_sel}':** ${total_cat:,.2f}")
        st.markdown(f"**Cantidad de movimientos:** {count_cat}")
        st.markdown(f"**Gasto promedio por transacción:** ${avg_cat:,.2f}")

        # Top 3 descripciones/proveedores frecuentes
        if not egresos_cat.empty:
            if "proveedor" in egresos_cat.columns:
                top_desc = egresos_cat['proveedor'].value_counts().head(3)
                st.markdown("**Top 3 proveedores frecuentes:**")
            else:
                top_desc = egresos_cat['descripción'].value_counts().head(3)
                st.markdown("**Top 3 descripciones frecuentes:**")
            for i, (desc, cnt) in enumerate(top_desc.items(), 1):
                st.write(f"{i}. {desc} ({cnt} veces)")

    # --- Wordcloud (Nube de palabras) de descripciones ---
    st.divider()
    st.subheader("Nube de palabras de descripciones (Wordcloud)")

    desc_text = " ".join(
        df[df['descripción'].notna() & (df['descripción'] != '')]['descripción'].astype(str).tolist()
    )
    if desc_text.strip():
        stopwords = set(STOPWORDS)
        wc = WordCloud(
            background_color='white',
            max_words=50,
            stopwords=stopwords,
            width=800,
            height=400,
            colormap='tab20c'
        ).generate(desc_text)
        fig_wc, ax_wc = plt.subplots(figsize=(10, 5))
        ax_wc.imshow(wc, interpolation='bilinear')
        ax_wc.axis('off')
        st.pyplot(fig_wc)
    else:
        st.info("No hay descripciones suficientes para generar una nube de palabras.")

    # --- Últimos movimientos ---
    st.divider()
    st.subheader("Movimientos")
    ultimos = df.sort_values("fecha", ascending=False)
    ultimos['monto'] = ultimos['monto'].map("${:,.2f}".format)
    st.dataframe(ultimos[["fecha", "banco", "tipo", "descripción", "monto", "categoría"]], use_container_width=True)
