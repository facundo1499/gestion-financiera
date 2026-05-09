import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pdfplumber
import re

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="Gestión ANSA - Facundo", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 32px !important; }
    div[data-testid="metric-container"] {
        background-color: #1A1C24; border: 1px solid #30363D; padding: 20px; border-radius: 15px;
    }
    h1, h2, h3 { color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE EXTRACCIÓN ---

def extraer_datos_ansa(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            texto = ""
            for pagina in pdf.pages:
                texto += pagina.extract_text() + "\n"
            if not texto.strip(): return "ERROR_IMAGEN"
            match = re.search(r"Total Neto->\s*([\d\.,]+)", texto)
            if match:
                monto_str = match.group(1).replace(".", "").replace(",", ".")
                return float(monto_str)
    except: return None
    return None

def extraer_datos_macro(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            texto = ""
            for pagina in pdf.pages:
                texto += pagina.extract_text() + "\n"
            patron_macro = r"DEBITAREMOS DE SU C\.A\..*?LA SUMA DE\s*\$\s*([\d\.,]+)"
            match = re.search(patron_macro, texto, re.IGNORECASE | re.DOTALL)
            if match:
                monto_str = match.group(1).replace(".", "").replace(",", ".")
                return float(monto_str)
    except: return None
    return None

# --- LÓGICA DE ESTADO ---
if 'ingresos' not in st.session_state: st.session_state.ingresos = 0.0
if 'gastos' not in st.session_state: st.session_state.gastos = 0.0

# --- SIDEBAR (RESTURADA) ---
st.sidebar.title("📅 Periodo de Consulta")
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
mes_sel = st.sidebar.selectbox("Selecciona Mes", meses, index=datetime.now().month - 1)
anio_sel = st.sidebar.selectbox("Selecciona Año", [2024, 2025, 2026], index=2) # 2026 por defecto

# --- INTERFAZ ---
st.title(f"🏭 Panel de Control: {mes_sel} {anio_sel}")
st.write(f"Usuario: **Coria Facundo Ariel**")

c1, c2, c3 = st.columns(3)
c1.metric("💰 NETO COBRADO", f"$ {st.session_state.ingresos:,.2f}")
c2.metric("💳 GASTOS MACRO", f"$ {st.session_state.gastos:,.2f}")
c3.metric("⚖️ DISPONIBLE", f"$ {(st.session_state.ingresos - st.session_state.gastos):,.2f}")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📁 Cargar Documentos")
    
    archivo_rec = st.file_uploader("Subir Recibo ANSA", type="pdf", key="rec_ansa")
    if archivo_rec:
        res = extraer_datos_ansa(archivo_rec)
        if res == "ERROR_IMAGEN":
            st.error("⚠️ PDF sin texto legible. Usá Adobe Scan.")
        elif res:
            st.session_state.ingresos = res
            st.success(f"✅ Sueldo cargado.")

    archivo_tar = st.file_uploader("Subir Resumen Macro", type="pdf", key="tar_macro")
    if archivo_tar:
        res_tar = extraer_datos_macro(archivo_tar)
        if res_tar:
            st.session_state.gastos = res_tar
            st.success(f"✅ Tarjeta cargada.")

with col_right:
    st.subheader("📊 Análisis de Balance")
    if st.session_state.ingresos > 0 or st.session_state.gastos > 0:
        fig = px.pie(
            values=[st.session_state.gastos, max(0, st.session_state.ingresos - st.session_state.gastos)],
            names=['Tarjeta Macro', 'Sobrante'],
            hole=0.6,
            color_discrete_sequence=['#FF4B4B', '#00CC96'],
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)
