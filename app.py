import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pdfplumber
import re
import json
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión Facundo - Total Seguro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 32px !important; }
    div[data-testid="metric-container"] {
        background-color: #1A1C24; border: 1px solid #30363D; padding: 20px; border-radius: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y FUNCIONES DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_gsheet():
    try:
        # Leemos la planilla. ttl=0 evita que Streamlit use datos viejos guardados en cache
        df = conn.read(ttl=0)
        datos = {}
        if not df.empty:
            for _, row in df.iterrows():
                # Reconvertimos los textos JSON a listas/diccionarios de Python
                datos[str(row['Periodo'])] = {
                    "ingresos": float(row['Ingresos']),
                    "gastos": json.loads(row['Gastos_JSON']),
                    "archivos": json.loads(row['Archivos_JSON'])
                }
        return datos
    except Exception as e:
        # Si la planilla está vacía o no existe, devolvemos un dict vacío
        return {}

def guardar_datos_gsheet(datos_dict):
    if not datos_dict:
        return
    
    filas = []
    for periodo, info in datos_dict.items():
        filas.append({
            "Periodo": periodo,
            "Ingresos": info["ingresos"],
            "Gastos_JSON": json.dumps(info["gastos"]),
            "Archivos_JSON": json.dumps(info["archivos"])
        })
    
    df_nuevo = pd.DataFrame(filas)
    # Actualizamos la planilla completa
    conn.update(data=df_nuevo)
    # Limpiamos el cache para que la próxima lectura sea inmediata
    st.cache_data.clear()

# --- 3. INICIALIZACIÓN ---
if 'datos_mensuales' not in st.session_state:
    st.session_state.datos_mensuales = cargar_datos_gsheet()

# --- 4. SIDEBAR ---
st.sidebar.title("📅 Periodo")
mes_sel = st.sidebar.selectbox("Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=datetime.now().month - 1)
anio_sel = st.sidebar.selectbox("Año", [2024, 2025, 2026], index=2)
id_periodo = f"{mes_sel}-{anio_sel}"

# Si el mes seleccionado no existe en nuestros datos, lo creamos
if id_periodo not in st.session_state.datos_mensuales:
    st.session_state.datos_mensuales[id_periodo] = {"ingresos": 0.0, "gastos": [], "archivos": []}

periodo_actual = st.session_state.datos_mensuales[id_periodo]

# --- 5. FUNCIONES PDF ---
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
            texto = "".join([p.extract_text() for p in pdf.pages]).upper()
            if "BBVA" in texto:
                m = re.search(r"SALDO ACTUAL\s*[\$]*\s*([\d\.,]+)", texto)
                return "BBVA VISA", limpiar_monto(m.group(1)) if m else 0
            if "TOTAL NETO->" in texto:
                m = re.search(r"TOTAL NETO->\s*([\d\.,]+)", texto)
                return "RECIBO ANSA", limpiar_monto(m.group(1)) if m else 0
            if "DEBITAREMOS DE SU C.A." in texto:
                m = re.search(r"LA SUMA DE\s*\$\s*([\d\.,]+)", texto)
                return "MACRO VISA", limpiar_monto(m.group(1)) if m else 0
            if "MERCADO PAGO" in texto or "TOTAL A PAGAR" in texto:
                m = re.search(r"TOTAL A PAGAR\s*[\$]*\s*([\d\.,]+)", texto)
                return "MERCADO PAGO", limpiar_monto(m.group(1)) if m else 0
            if "NARANJA" in texto:
                m = re.search(r"TOTAL\s*\$\s*([\d\.,]+)", texto)
                return "NARANJA", limpiar_monto(m.group(1)) if m else 0
    except: pass
    return "DESCONOCIDO", 0

# --- 6. INTERFAZ Y LÓGICA ---
ingresos_totales = periodo_actual["ingresos"]
gastos_totales = sum([g['monto'] for g in periodo_actual["gastos"]])
balance = ingresos_totales - gastos_totales

st.title(f"📊 Dashboard: {mes_sel} {anio_sel}")

col1, col2, col3 = st.columns(3)
col1.metric("💰 INGRESOS TOTALES", f"$ {ingresos_totales:,.2f}")
col2.metric("💳 GASTOS TARJETAS", f"$ {gastos_totales:,.2f}")
col3.metric("⚖️ DISPONIBLE", f"$ {balance:,.2f}")

st.divider()

st.subheader("📁 Cargar PDF (Recibo o Tarjeta)")
# Key dinámica para resetear el uploader al cambiar de mes
archivo = st.file_uploader("Subí tus archivos aquí", type="pdf", key=f"uploader_{id_periodo}")

if archivo and archivo.name not in periodo_actual["archivos"]:
    tipo, monto = procesar_archivo_universal(archivo)
    
    if tipo == "RECIBO ANSA":
        periodo_actual["ingresos"] += monto
        periodo_actual["archivos"].append(archivo.name)
    elif tipo != "DESCONOCIDO":
        periodo_actual["gastos"].append({"nombre": archivo.name, "tipo": tipo, "monto": monto})
        periodo_actual["archivos"].append(archivo.name)
    
    # GUARDADO AUTOMÁTICO EN GOOGLE SHEETS
    guardar_datos_gsheet(st.session_state.datos_mensuales)
    st.rerun()

# Listado de archivos cargados
if periodo_actual["archivos"]:
    with st.expander(f"📄 Archivos cargados en {mes_sel}"):
        for f in periodo_actual["archivos"]:
            st.write(f"- {f}")

# --- 7. TABLA Y GRÁFICO ---
c_tabla, c_grafico = st.columns([1, 1])

with c_tabla:
    if periodo_actual["gastos"]:
        st.write("**Detalle de consumos:**")
        df_vis = pd.DataFrame(periodo_actual["gastos"])
        st.dataframe(df_vis[['tipo', 'monto']], use_container_width=True)
    
    if st.button("🗑️ Borrar datos de este mes"):
        st.session_state.datos_mensuales[id_periodo] = {"ingresos": 0.0, "gastos": [], "archivos": []}
        guardar_datos_gsheet(st.session_state.datos_mensuales)
        st.rerun()

with c_grafico:
    if ingresos_totales > 0 or gastos_totales > 0:
        resumen = {}
        for g in periodo_actual["gastos"]:
            resumen[g['tipo']] = resumen.get(g['tipo'], 0) + g['monto']
        if balance > 0:
            resumen['Disponible'] = balance
        
        fig = px.pie(values=list(resumen.values()), names=list(resumen.keys()), hole=0.5, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
