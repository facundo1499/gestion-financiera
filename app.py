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

# --- FUNCIONES DE PROCESAMIENTO ---
def limpiar_monto(monto_str):
    monto_str = monto_str.replace("$", "").strip()
    if "." in monto_str and "," in monto_str:
        monto_str = monto_str.replace(".", "").replace(",", ".")
    elif "." in monto_str and len(monto_str.split(".")[-1]) == 3:
        monto_str = monto_str.replace(".", "")
    elif "," in monto_str:
        monto_str = monto_str.replace(",", ".")
    try: return float(monto_str)
    except: return 0.0

def procesar_archivo_universal(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            texto = "".join([p.extract_text() for p in pdf.pages])
            if not texto.strip(): return "ERROR_IMAGEN", 0
            texto_upper = texto.upper()

            if "BBVA" in texto_upper:
                match = re.search(r"SALDO ACTUAL\s*[\$]*\s*([\d\.,]+)", texto_upper)
                if match: return "BBVA VISA", limpiar_monto(match.group(1))
            if "TOTAL NETO->" in texto_upper:
                match = re.search(r"TOTAL NETO->\s*([\d\.,]+)", texto_upper)
                if match: return "RECIBO ANSA", limpiar_monto(match.group(1))
            if "DEBITAREMOS DE SU C.A." in texto_upper:
                match = re.search(r"LA SUMA DE\s*\$\s*([\d\.,]+)", texto_upper)
                if match: return "MACRO VISA", limpiar_monto(match.group(1))
            if "MERCADO PAGO" in texto_upper or "TOTAL A PAGAR" in texto_upper:
                match = re.search(r"TOTAL A PAGAR\s*[\$]*\s*([\d\.,]+)", texto_upper)
                if match: return "MERCADO PAGO", limpiar_monto(match.group(1))
            if "NARANJA" in texto_upper:
                match = re.search(r"TOTAL\s*\$\s*([\d\.,]+)", texto_upper)
                if match: return "NARANJA", limpiar_monto(match.group(1))
    except: return None, 0
    return "DESCONOCIDO", 0

# --- LÓGICA DE ALMACENAMIENTO POR MES ---
# Estructura: st.session_state.datos_mensuales = {"Mayo-2026": {"ingresos": 0, "gastos": [], "archivos": []}}
if 'datos_mensuales' not in st.session_state:
    st.session_state.datos_mensuales = {}

# --- SIDEBAR ---
st.sidebar.title("📅 Periodo")
mes_sel = st.sidebar.selectbox("Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=datetime.now().month - 1)
anio_sel = st.sidebar.selectbox("Año", [2024, 2025, 2026], index=2)

# Crear la "llave" del periodo actual
id_periodo = f"{mes_sel}-{anio_sel}"

# Inicializar el periodo si no existe
if id_periodo not in st.session_state.datos_mensuales:
    st.session_state.datos_mensuales[id_periodo] = {"ingresos": 0.0, "gastos": [], "archivos": []}

# Referencias directas al periodo actual para simplificar el código
periodo_actual = st.session_state.datos_mensuales[id_periodo]

# --- CÁLCULOS ---
ingresos_totales = periodo_actual["ingresos"]
gastos_totales = sum([g['monto'] for g in periodo_actual["gastos"]])
balance = ingresos_totales - gastos_totales

# --- INTERFAZ ---
st.title(f"📊 Dashboard: {mes_sel} {anio_sel}")

c1, c2, c3 = st.columns(3)
c1.metric("💰 INGRESOS TOTALES", f"$ {ingresos_totales:,.2f}")
c2.metric("💳 GASTOS TARJETAS", f"$ {gastos_totales:,.2f}")
c3.metric("⚖️ DISPONIBLE", f"$ {balance:,.2f}")

st.divider()

st.subheader("📁 Cargar PDF (Recibo o Tarjeta)")
archivo = st.file_uploader("Subí tus archivos aquí", type="pdf")

# --- PROCESAMIENTO ---
if archivo and archivo.name not in periodo_actual["archivos"]:
    tipo, monto = procesar_archivo_universal(archivo)
    
    if tipo == "RECIBO ANSA":
        periodo_actual["ingresos"] += monto
        periodo_actual["archivos"].append(archivo.name)
        st.rerun()
    elif tipo != "DESCONOCIDO" and tipo != "ERROR_IMAGEN":
        periodo_actual["gastos"].append({"nombre": archivo.name, "tipo": tipo, "monto": monto})
        periodo_actual["archivos"].append(archivo.name)
        st.rerun()

# Mostrar archivos del mes seleccionado
if periodo_actual["archivos"]:
    with st.expander(f"📄 Archivos cargados en {mes_sel}"):
        for f in periodo_actual["archivos"]:
            st.write(f"- {f}")

# --- TABLA Y GRÁFICO ---
col_t, col_g = st.columns([1, 1])

with col_t:
    if periodo_actual["gastos"]:
        st.write("**Detalle de tarjetas:**")
        df = pd.DataFrame(periodo_actual["gastos"])
        st.dataframe(df[['tipo', 'monto']], use_container_width=True)
        
    # Botón para borrar SOLO el mes actual en caso de error
    if st.button("🗑️ Borrar datos de este mes"):
        st.session_state.datos_mensuales[id_periodo] = {"ingresos": 0.0, "gastos": [], "archivos": []}
        st.rerun()

with col_g:
    if ingresos_totales > 0 or gastos_totales > 0:
        # Agrupar gastos por tipo para el gráfico
        datos_dict = {}
        for g in periodo_actual["gastos"]:
            datos_dict[g['tipo']] = datos_dict.get(g['tipo'], 0) + g['monto']
        
        if balance > 0: datos_dict['Disponible'] = balance
        
        fig = px.pie(values=list(datos_dict.values()), names=list(datos_dict.keys()), hole=0.6, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
