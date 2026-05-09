import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Mi Gestión Financiera", layout="wide")

# --- PARCHE PARA MODO OSCURO Y COLORES ---
st.markdown("""
    <style>
    /* Forzar fondo oscuro y texto claro */
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    
    /* Estilo para las tarjetas de números */
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 32px !important; }
    [data-testid="stMetricLabel"] { color: #A0A0A0 !important; }
    
    /* Fondo de las tarjetas */
    div[data-testid="metric-container"] {
        background-color: #1A1C24;
        border: 1px solid #30363D;
        padding: 20px;
        border-radius: 15px;
    }
    
    /* Ajustar títulos */
    h1, h2, h3 { color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- DATOS (Simulados hasta cargar PDF) ---
ingresos_total = 550000.0
gastos_tarjeta = 125000.0
balance = ingresos_total - gastos_tarjeta
ahorros_meta = 85000.0

# --- SIDEBAR ---
st.sidebar.title("📅 Filtros")
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
mes_sel = st.sidebar.selectbox("Selecciona Mes", meses, index=datetime.now().month - 1)
anio_sel = st.sidebar.selectbox("Selecciona Año", [2024, 2025, 2026])

# --- TITULO ---
st.title(f"📊 Resumen de {mes_sel} {anio_sel}")

# --- MÉTRICAS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 INGRESOS TOTALES", f"$ {ingresos_total:,.2f}")
col2.metric("💳 GASTOS TARJETAS", f"$ {gastos_tarjeta:,.2f}")
col3.metric("⚖️ BALANCE NETO", f"$ {balance:,.2f}")
col4.metric("🏦 AHORROS ACUM.", f"$ {ahorros_meta:,.2f}")

st.markdown("<br>", unsafe_allow_html=True)

# --- GRÁFICOS (Con tema oscuro) ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("Evolución Mensual")
    df_graf = pd.DataFrame({
        'Mes': ['Ene', 'Feb', 'Mar', 'Abr'],
        'Ingresos': [500000, 520000, 510000, 550000],
        'Gastos': [120000, 150000, 130000, 125000]
    })
    fig = px.line(df_graf, x='Mes', y=['Ingresos', 'Gastos'], markers=True, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Distribución actual")
    fig2 = px.pie(values=[gastos_tarjeta, balance], names=['Gastos', 'Disponible'], hole=0.4, template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

# --- CARGA ---
st.divider()
st.header("📂 Cargar Documentos")
archivo = st.file_uploader("Sube tu PDF aquí", type="pdf")
