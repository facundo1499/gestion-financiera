import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pdfplumber
import re
import json
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Facundo - Pro", layout="wide")

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_gsheet():
    try:
        # Intentamos leer la hoja
        df = conn.read(ttl=0)
        datos = {}
        if df is not None and not df.empty:
            # Filtramos filas vacías por seguridad
            df = df.dropna(subset=['Periodo'])
            for _, row in df.iterrows():
                datos[str(row['Periodo'])] = {
                    "ingresos": float(row['Ingresos']),
                    "gastos": json.loads(row['Gastos_JSON']),
                    "archivos": json.loads(row['Archivos_JSON'])
                }
        return datos
    except:
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
    
    # --- SOLUCIÓN AL ERROR DE ESCRITURA ---
    # Probamos escribir en "Hoja 1" o "Sheet1" explícitamente
    try:
        conn.update(worksheet="Hoja 1", data=df_nuevo)
    except:
        try:
            conn.update(worksheet="Sheet1", data=df_nuevo)
        except Exception as e:
            st.error(f"Error crítico de conexión: {e}")
            # Si falla ambos, intentamos el método genérico
            conn.update(data=df_nuevo)
            
    st.cache_data.clear()

# --- 3. INICIALIZACIÓN DE ESTADO ---
if 'datos_mensuales' not in st.session_state:
    st.session_state.datos_mensuales = cargar_datos_gsheet()

# --- 4. SIDEBAR ---
st.sidebar.title("📅 Periodo")
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
mes_sel = st.sidebar.selectbox("Mes", meses, index=datetime.now().month - 1)
anio_sel = st.sidebar.selectbox("Año", [2024, 2025, 2026], index=2)
id_periodo = f"{mes_sel}-{anio_sel}"

if id_periodo not in st.session_state.datos_mensuales:
    st.session_state.datos_mensuales[id_periodo] = {"ingresos": 0.0, "gastos": [], "archivos": []}

periodo_actual = st.session_state.datos_mensuales[id_periodo]

# --- 5. PROCESAMIENTO PDF ---
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

# --- 6. INTERFAZ ---
st.title(f"📊 Dashboard: {mes_sel} {anio_sel}")

ingresos_totales = periodo_actual["ingresos"]
gastos_totales = sum([g['monto'] for g in periodo_actual["gastos"]])
balance = ingresos_totales - gastos_totales

c1, c2, c3 = st.columns(3)
c1.metric("💰 INGRESOS TOTALES", f"$ {ingresos_totales:,.2f}")
c2.metric("💳 GASTOS TARJETAS", f"$ {gastos_totales:,.2f}")
c3.metric("⚖️ DISPONIBLE", f"$ {balance:,.2f}")

st.divider()

archivo = st.file_uploader("Subí tus archivos aquí", type="pdf", key=f"uploader_{id_periodo}")

if archivo and archivo.name not in periodo_actual["archivos"]:
    tipo, monto = procesar_archivo_universal(archivo)
    if tipo == "RECIBO ANSA":
        periodo_actual["ingresos"] += monto
        periodo_actual["archivos"].append(archivo.name)
    elif tipo != "DESCONOCIDO":
        periodo_actual["gastos"].append({"nombre": archivo.name, "tipo": tipo, "monto": monto})
        periodo_actual["archivos"].append(archivo.name)
    
    # GUARDAR Y REFRESCAR
    guardar_datos_gsheet(st.session_state.datos_mensuales)
    st.rerun()

# Detalle y Gráficos
col_a, col_b = st.columns(2)
with col_a:
    if periodo_actual["gastos"]:
        st.write("**Consumos del mes:**")
        st.table(pd.DataFrame(periodo_actual["gastos"])[['tipo', 'monto']])
    
    if st.button("🗑️ Reiniciar este mes"):
        st.session_state.datos_mensuales[id_periodo] = {"ingresos": 0.0, "gastos": [], "archivos": []}
        guardar_datos_gsheet(st.session_state.datos_mensuales)
        st.rerun()

with col_b:
    if ingresos_totales > 0 or gastos_totales > 0:
        resumen = {g['tipo']: g['monto'] for g in periodo_actual["gastos"]}
        if balance > 0: resumen['Disponible'] = balance
        fig = px.pie(values=list(resumen.values()), names=list(resumen.keys()), hole=0.5)
        st.plotly_chart(fig, use_container_width=True)
