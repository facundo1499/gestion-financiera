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

# 1. Lector ANSA
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

# 2. Lector Banco Macro (Tarjeta)
def extraer_datos_macro(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            texto = ""
            for pagina in pdf.pages:
                texto += pagina.extract_text() + "\n"
            
            # Buscamos frases típicas de resúmenes de tarjeta
            patrones = [r"SALDO AL CIERRE\s*[\$]*\s*([\d\.,]+)", r"TOTAL A PAGAR\s*[\$]*\s*([\d\.,]+)"]
            for p in patrones:
                match = re.search(p, texto, re.IGNORECASE)
                if match:
                    monto_str = match.group(1).replace(".", "").replace(",", ".")
                    return float(monto_str)
    except: return None
    return None

# --- LÓGICA DE ESTADO ---
if 'ingresos' not in st.session_state: st.session_state.ingresos = 0.0
if 'gastos' not in st.session_state: st.session_state.gastos = 0.0

# --- INTERFAZ ---
st.title("🏭 Panel de Control - ANSA S.A.")
st.write(f"Usuario: **Coria Facundo Ariel**")

c1, c2, c3 = st.columns(3)
c1.metric("💰 NETO COBRADO", f"$ {st.session_state.ingresos:,.2f}")
c2.metric("💳 GASTOS MACRO", f"$ {st.session_state.gastos:,.2f}")
c3.metric("⚖️ DISPONIBLE", f"$ {(st.session_state.ingresos - st.session_state.gastos):,.2f}")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📁 Cargar Documentos")
    
    # Cargador de Recibo
    archivo_rec = st.file_uploader("Subir Recibo ANSA", type="pdf", key="rec_ansa")
    if archivo_rec:
        res = extraer_datos_ansa(archivo_rec)
        if res == "ERROR_IMAGEN":
            st.error("⚠️ El PDF del recibo es una foto sin OCR. Usa Adobe Scan.")
        elif res:
            st.session_state.ingresos = res
            st.success(f"✅ Sueldo actualizado: $ {res:,.2f}")

    # Cargador de Tarjeta (RESTAURADO)
    archivo_tar = st.file_uploader("Subir Resumen Banco Macro", type="pdf", key="tar_macro")
    if archivo_tar:
        res_tar = extraer_datos_macro(archivo_tar)
        if res_tar:
            st.session_state.gastos = res_tar
            st.success(f"✅ Gastos de tarjeta cargados: $ {res_tar:,.2f}")
        else:
            st.warning("❓ No se detectó el 'Total a Pagar'. ¿Es el PDF original del banco?")

with col_right:
    st.subheader("📊 Gráfico de Balance")
    if st.session_state.ingresos > 0 or st.session_state.gastos > 0:
        fig = px.pie(
            values=[st.session_state.gastos, max(0, st.session_state.ingresos - st.session_state.gastos)],
            names=['Gastos Tarjeta', 'Dinero Disponible'],
            hole=0.5,
            color_discrete_sequence=['#FF4B4B', '#00CC96'],
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sube tus archivos para ver el gráfico de distribución.")
