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
    </style>
    """, unsafe_allow_html=True)

# --- DETECTOR ESPECÍFICO PARA RECIBO ANSA ---
def extraer_datos_ansa(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            texto = ""
            for pagina in pdf.pages:
                texto += pagina.extract_text() + "\n"
            
            if not texto.strip():
                return "ERROR_IMAGEN"

            # Buscamos el "Total Neto->" seguido del número
            # El patrón busca la palabra, la flecha y el número con decimales
            match = re.search(r"Total Neto->\s*([\d\.,]+)", texto)
            
            if match:
                monto_str = match.group(1)
                # Limpieza de formato argentino (puntos de mil y coma decimal)
                # Si el número es 512512.14 lo detectamos directo
                if "," in monto_str and "." in monto_str:
                    monto_str = monto_str.replace(".", "").replace(",", ".")
                return float(monto_str)
    except Exception as e:
        return None
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
    st.subheader("📁 Cargar Recibo de Sueldo")
    archivo_rec = st.file_uploader("Subir PDF del Recibo", type="pdf", key="rec_ansa")
    if archivo_rec:
        res = extraer_datos_ansa(archivo_rec)
        if res == "ERROR_IMAGEN":
            st.error("⚠️ El PDF no tiene texto legible. Por favor, usa una App de escáner (OCR).")
        elif res:
            st.session_state.ingresos = res
            st.success(f"✅ Recibo procesado: $ {res:,.2f}")
        else:
            st.warning("❓ No se encontró el 'Total Neto->'. Verifica que el PDF sea nítido.")

with col_right:
    st.subheader("📊 Distribución")
    if st.session_state.ingresos > 0:
        fig = px.pie(
            values=[st.session_state.gastos, max(0, st.session_state.ingresos - st.session_state.gastos)],
            names=['Gastos', 'Sobrante'],
            hole=0.5,
            color_discrete_sequence=['#EF553B', '#00CC96'],
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)
