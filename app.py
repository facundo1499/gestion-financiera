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
            # Busca el monto después de la flecha en tu recibo de ANSA
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
            
            # Patrón específico para Banco Macro: "DEBITAREMOS DE SU C.A.[...] LA SUMA DE $ XXX"
            patron_macro = r"DEBITAREMOS DE SU C\.A\..*?LA SUMA DE\s*\$\s*([\d\.,]+)"
            match = re.search(patron_macro, texto, re.IGNORECASE | re.DOTALL)
            
            if match:
                monto_str = match.group(1).replace(".", "").replace(",", ".")
                return float(monto_str)
            
            # Patrón secundario por si acaso
            match_alt = re.search(r"TOTAL A PAGAR\s*\$\s*([\d\.,]+)", texto, re.IGNORECASE)
            if match_alt:
                return float(match_alt.group(1).replace(".", "").replace(",", "."))
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
    archivo_rec = st.file_uploader("Subir Recibo ANSA (PDF con OCR)", type="pdf", key="rec_ansa")
    if archivo_rec:
        res = extraer_datos_ansa(archivo_rec)
        if res == "ERROR_IMAGEN":
            st.error("⚠️ El PDF del recibo no tiene texto. Escanéalo con Adobe Scan.")
        elif res:
            st.session_state.ingresos = res
            st.success(f"✅ Sueldo detectado: $ {res:,.2f}")

    # Cargador de Tarjeta Macro
    archivo_tar = st.file_uploader("Subir Resumen Banco Macro (PDF)", type="pdf", key="tar_macro")
    if archivo_tar:
        res_tar = extraer_datos_macro(archivo_tar)
        if res_tar:
            st.session_state.gastos = res_tar
            st.success(f"✅ Gasto de tarjeta detectado: $ {res_tar:,.2f}")
        else:
            st.warning("❓ No se encontró la frase de débito. Verifica que sea el PDF del Banco Macro.")

with col_right:
    st.subheader("📊 Análisis de Gastos")
    if st.session_state.ingresos > 0 or st.session_state.gastos > 0:
        fig = px.pie(
            values=[st.session_state.gastos, max(0, st.session_state.ingresos - st.session_state.gastos)],
            names=['Tarjeta Macro', 'Sobrante'],
            hole=0.6,
            color_discrete_sequence=['#FF4B4B', '#00CC96'],
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)
