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
            texto = "".join([pagina.extract_text() for pagina in pdf.pages])
            match = re.search(r"Total Neto->\s*([\d\.,]+)", texto)
            if match:
                return float(match.group(1).replace(".", "").replace(",", "."))
    except: return None
    return None

def extraer_datos_macro(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            texto = "".join([pagina.extract_text() for pagina in pdf.pages])
            # Buscamos la frase que me pasaste del Macro
            patron = r"DEBITAREMOS DE SU C\.A\..*?LA SUMA DE\s*\$\s*([\d\.,]+)"
            match = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
            if match:
                return float(match.group(1).replace(".", "").replace(",", "."))
    except: return None
    return None

# --- LÓGICA DE ESTADO (MEMORIA DE LA APP) ---
if 'ingresos' not in st.session_state: st.session_state.ingresos = 0.0
if 'gastos_tarjetas' not in st.session_state: st.session_state.gastos_tarjetas = {}

# --- SIDEBAR ---
st.sidebar.title("📅 Periodo de Consulta")
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
mes_sel = st.sidebar.selectbox("Selecciona Mes", meses, index=datetime.now().month - 1)
anio_sel = st.sidebar.selectbox("Selecciona Año", [2024, 2025, 2026], index=2)

# --- CÁLCULOS TOTALES ---
total_gastos = sum(st.session_state.gastos_tarjetas.values())
balance_neto = st.session_state.ingresos - total_gastos

# --- INTERFAZ PRINCIPAL ---
st.title(f"🏭 Panel de Control: {mes_sel} {anio_sel}")

c1, c2, c3 = st.columns(3)
c1.metric("💰 INGRESOS TOTALES", f"$ {st.session_state.ingresos:,.2f}")
c2.metric("💳 GASTOS TARJETAS", f"$ {total_gastos:,.2f}")
c3.metric("⚖️ BALANCE NETO", f"$ {balance_neto:,.2f}")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📁 Carga de Documentos")
    
    # 1. CARGA DE SUELDO
    archivo_rec = st.file_uploader("Subir Recibo ANSA", type="pdf", key="rec_ansa")
    if archivo_rec:
        res = extraer_datos_ansa(archivo_rec)
        if res:
            st.session_state.ingresos = res
            st.success("✅ Sueldo actualizado.")

    st.markdown("---")
    st.write("**Resúmenes de Tarjetas:**")
    
    # 2. CARGA DE TARJETAS (Múltiples slots)
    for i in range(1, 4): # Permite cargar hasta 3 tarjetas
        archivo_tar = st.file_uploader(f"Subir Tarjeta {i} (Macro/Otros)", type="pdf", key=f"tarjeta_{i}")
        if archivo_tar:
            monto_tar = extraer_datos_macro(archivo_tar)
            if monto_tar:
                st.session_state.gastos_tarjetas[f"tarjeta_{i}"] = monto_tar
                st.info(f"Tarjeta {i}: $ {monto_tar:,.2f} detectados.")

with col_right:
    st.subheader("📊 Distribución del Presupuesto")
    if st.session_state.ingresos > 0 or total_gastos > 0:
        # Preparamos datos para el gráfico
        nombres = list(st.session_state.gastos_tarjetas.keys()) + ['Disponible']
        valores = list(st.session_state.gastos_tarjetas.values()) + [max(0, balance_neto)]
        
        fig = px.pie(
            values=valores,
            names=nombres,
            hole=0.6,
            template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Carga archivos para ver el análisis.")
