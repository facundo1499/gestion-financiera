import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pdfplumber
import re

# Configuración de la página
st.set_page_config(page_title="Mi Gestión Financiera", layout="wide")

# --- ESTILOS MODO OSCURO FORZADO ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 32px !important; }
    [data-testid="stMetricLabel"] { color: #A0A0A0 !important; }
    div[data-testid="metric-container"] {
        background-color: #1A1C24;
        border: 1px solid #30363D;
        padding: 20px;
        border-radius: 15px;
    }
    h1, h2, h3 { color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE EXTRACCIÓN ---
def extraer_monto_recibo(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        texto_completo = ""
        for pagina in pdf.pages:
            texto_completo += pagina.extract_text()
        
        # Busca "Total Neto" seguido de números, puntos o comas
        match = re.search(r"Total Neto[:\s]*([\d\.,]+)", texto_completo, re.IGNORECASE)
        if match:
            monto_str = match.group(1).replace(".", "").replace(",", ".")
            return float(monto_str)
    return None

# --- ESTADO DE LA APP (Base de datos temporal) ---
if 'ingresos' not in st.session_state:
    st.session_state.ingresos = 0.0
if 'gastos' not in st.session_state:
    st.session_state.gastos = 0.0

# --- SIDEBAR ---
st.sidebar.title("📅 Filtros")
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
mes_sel = st.sidebar.selectbox("Selecciona Mes", meses, index=datetime.now().month - 1)
anio_sel = st.sidebar.selectbox("Selecciona Año", [2024, 2025, 2026])

# --- DASHBOARD ---
st.title(f"📊 Resumen de {mes_sel} {anio_sel}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 INGRESOS TOTALES", f"$ {st.session_state.ingresos:,.2f}")
col2.metric("💳 GASTOS TARJETAS", f"$ {st.session_state.gastos:,.2f}")
col3.metric("⚖️ BALANCE NETO", f"$ {(st.session_state.ingresos - st.session_state.gastos):,.2f}")
col4.metric("🏦 AHORROS ACUM.", f"$ 0.00")

st.divider()

# --- CARGA DE ARCHIVOS ---
st.header("📂 Importar Datos desde PDF")
c1, c2 = st.columns(2)

with c1:
    st.subheader("Recibo de Sueldo")
    archivo_recibo = st.file_uploader("Sube tu recibo (Busca 'Total Neto')", type="pdf", key="recibo")
    if archivo_recibo:
        monto = extraer_monto_recibo(archivo_recibo)
        if monto:
            st.session_state.ingresos = monto
            st.success(f"✅ ¡Sueldo detectado: $ {monto:,.2f}!")
        else:
            st.error("❌ No se encontró la frase 'Total Neto' en el PDF.")

with c2:
    st.subheader("Resumen de Tarjeta")
    archivo_tarjeta = st.file_uploader("Sube tu resumen de tarjeta", type="pdf", key="tarjeta")
    # Aquí agregaremos la lógica específica de tu banco cuando me digas cuál es
    if archivo_tarjeta:
        st.info("Lector de tarjeta en desarrollo... (Necesito saber el nombre de tu banco)")

# --- GRÁFICOS ---
st.divider()
if st.session_state.ingresos > 0 or st.session_state.gastos > 0:
    fig = px.pie(
        values=[st.session_state.gastos, max(0, st.session_state.ingresos - st.session_state.gastos)],
        names=['Gastos', 'Disponible'],
        hole=0.5,
        template="plotly_dark",
        color_discrete_sequence=['#FF4B4B', '#00CC96']
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sube un archivo para ver los gráficos.")
