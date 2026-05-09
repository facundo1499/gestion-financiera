import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pdfplumber
import re

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="Gestión Facundo - Multi-Tarjetas", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 32px !important; }
    div[data-testid="metric-container"] {
        background-color: #1A1C24; border: 1px solid #30363D; padding: 20px; border-radius: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DETECTOR MULTI-BANCO ACTUALIZADO ---
def procesar_archivo_universal(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            texto = "".join([p.extract_text() for p in pdf.pages])
            if not texto.strip(): return "ERROR_IMAGEN", 0

            # 1. RECIBO ANSA (Coria Facundo Ariel)
            if "Total Neto->" in texto:
                match = re.search(r"Total Neto->\s*([\d\.,]+)", texto)
                if match: return "RECIBO ANSA", float(match.group(1).replace(".", "").replace(",", "."))

            # 2. BANCO MACRO
            if "DEBITAREMOS DE SU C.A." in texto:
                match = re.search(r"LA SUMA DE\s*\$\s*([\d\.,]+)", texto)
                if match: return "MACRO VISA", float(match.group(1).replace(".", "").replace(",", "."))

            # 3. MERCADO PAGO
            if "Mercado Pago" in texto or "Total a pagar en pesos" in texto:
                match = re.search(r"Total a pagar\s*[\$]*\s*([\d\.,]+)", texto, re.I)
                if match: return "MERCADO PAGO", float(match.group(1).replace(".", "").replace(",", "."))

            # 4. TARJETA NARANJA (Frase: Total)
            if "NARANJA" in texto.upper():
                # Buscamos la palabra Total seguida de pesos, evitando subtotales
                match = re.search(r"Total\s*\$\s*([\d\.,]+)", texto, re.I)
                if match: return "NARANJA", float(match.group(1).replace(".", "").replace(",", "."))

            # 5. BBVA (Frase: SALDO ACTUAL)
            if "BBVA" in texto:
                match = re.search(r"SALDO ACTUAL\s*[\$]*\s*([\d\.,]+)", texto, re.I)
                if match: return "BBVA VISA", float(match.group(1).replace(".", "").replace(",", "."))

    except: return None, 0
    return "DESCONOCIDO", 0

# --- LÓGICA DE ESTADO ---
if 'historial' not in st.session_state: st.session_state.historial = []
if 'ingresos' not in st.session_state: st.session_state.ingresos = 0.0

# --- SIDEBAR ---
st.sidebar.title("📅 Filtros")
mes_sel = st.sidebar.selectbox("Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=datetime.now().month - 1)
anio_sel = st.sidebar.selectbox("Año", [2024, 2025, 2026], index=2)

# --- CÁLCULOS ---
gastos_totales = sum([item['monto'] for item in st.session_state.historial if "RECIBO" not in item['tipo']])
balance = st.session_state.ingresos - gastos_totales

# --- INTERFAZ ---
st.title(f"📊 Dashboard: {mes_sel} {anio_sel}")

c1, c2, c3 = st.columns(3)
c1.metric("💰 INGRESOS", f"$ {st.session_state.ingresos:,.2f}")
c2.metric("💳 GASTOS TARJETAS", f"$ {gastos_totales:,.2f}")
c3.metric("⚖️ DISPONIBLE", f"$ {balance:,.2f}")

st.divider()

# --- CARGA UNIVERSAL ---
st.subheader("📁 Cargar PDF (Recibo o Tarjeta)")
archivo = st.file_uploader("Subí tu archivo de ANSA, Macro, MP, Naranja o BBVA", type="pdf")

if archivo:
    tipo, monto = procesar_archivo_universal(archivo)
    
    if tipo == "ERROR_IMAGEN":
        st.error("⚠️ Recordá pasar la foto por Adobe Scan antes de subirla.")
    elif tipo == "RECIBO ANSA":
        st.session_state.ingresos = monto
        st.success(f"✅ Ingreso cargado: $ {monto:,.2f}")
    elif tipo != "DESCONOCIDO":
        if not any(d['nombre'] == archivo.name for d in st.session_state.historial):
            st.session_state.historial.append({"nombre": archivo.name, "tipo": tipo, "monto": monto})
            st.success(f"✅ {tipo} cargada: $ {monto:,.2f}")
    else:
        st.warning("❓ No pude detectar el monto automáticamente. Revisá si el PDF es el original.")

# --- TABLA Y GRÁFICO ---
col_t, col_g = st.columns([1, 1])

with col_t:
    st.write("**Detalle de consumos:**")
    if st.session_state.historial:
        df = pd.DataFrame(st.session_state.historial)
        st.dataframe(df[['tipo', 'monto']], use_container_width=True)
        if st.button("🗑️ Reiniciar Mes"):
            st.session_state.historial = []
            st.session_state.ingresos = 0.0
            st.rerun()

with col_g:
    if st.session_state.ingresos > 0 or gastos_totales > 0:
        datos_grafico = {item['tipo']: item['monto'] for item in st.session_state.historial}
        if balance > 0: datos_grafico['Disponible'] = balance
        
        fig = px.pie(
            values=list(datos_grafico.values()),
            names=list(datos_grafico.keys()),
            hole=0.6,
            template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        st.plotly_chart(fig, use_container_width=True)
