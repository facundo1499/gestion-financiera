import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pdfplumber
import re
import json
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión Facundo - Pro", layout="wide")

# --- 2. TRUCO PARA LA LLAVE PRIVADA (SOLUCIONA EL ERROR PEM) ---
# Este bloque corrige el formato de la llave antes de que la conexión la use
if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
    pk = st.secrets["connections"]["gsheets"]["private_key"]
    if "\\n" in pk:
        st.secrets["connections"]["gsheets"]["private_key"] = pk.replace("\\n", "\n")

# --- 3. CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)
def cargar_datos_gsheet():
    try:
        # Forzamos lectura de la pestaña específica
        df = conn.read(worksheet="Hoja 1", ttl=0)
        datos = {}
        if df is not None and not df.empty:
            columnas = ['Periodo', 'Ingresos', 'Gastos_JSON', 'Archivos_JSON']
            if all(col in df.columns for col in columnas):
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
    
    try:
        # Forzamos la actualización en la Hoja 1
        conn.update(worksheet="Hoja 1", data=df_nuevo)
        st.cache_data.clear()
        # Usamos st.toast para que el aviso sea más visible
        st.toast("✅ ¡Datos guardados en Drive!", icon="💾")
        st.sidebar.success("✅ Guardado en Drive")
    except Exception as e:
        # Esto nos dirá si es un problema de permisos o de nombre de hoja
        st.error(f"Falla al guardar: {e}")
        # Guardamos específicamente en Hoja 1
        conn.update(worksheet="Hoja 1", data=df_nuevo)
        st.cache_data.clear()
        st.sidebar.success("✅ Guardado en Drive")
    except Exception as e:
        st.error(f"Error al guardar: {e}")
# --- 4. INICIALIZACIÓN DE DATOS ---
if 'datos_mensuales' not in st.session_state or st.sidebar.button("🔄 Forzar Sincronización"):
    st.cache_data.clear()  # <-- Esto limpia la memoria vieja
    with st.spinner("Buscando datos en la nube..."):
        st.session_state.datos_mensuales = cargar_datos_gsheet()
# --- 5. SIDEBAR (FILTROS) ---
st.sidebar.title("📅 Periodo")
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
mes_sel = st.sidebar.selectbox("Mes", meses, index=datetime.now().month - 1)
anio_sel = st.sidebar.selectbox("Año", [2024, 2025, 2026], index=2)
id_periodo = f"{mes_sel}-{anio_sel}"

if id_periodo not in st.session_state.datos_mensuales:
    st.session_state.datos_mensuales[id_periodo] = {"ingresos": 0.0, "gastos": [], "archivos": []}

periodo_actual = st.session_state.datos_mensuales[id_periodo]

# --- 6. PROCESAMIENTO DE PDF ---
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

# --- 7. INTERFAZ VISUAL ---
st.title(f"📊 Dashboard: {mes_sel} {anio_sel}")

ingresos_totales = periodo_actual["ingresos"]
gastos_totales = sum([g['monto'] for g in periodo_actual["gastos"]])
balance = ingresos_totales - gastos_totales

c1, c2, c3 = st.columns(3)
c1.metric("💰 INGRESOS TOTALES", f"$ {ingresos_totales:,.2f}")
c2.metric("💳 GASTOS TARJETAS", f"$ {gastos_totales:,.2f}")
c3.metric("⚖️ DISPONIBLE", f"$ {balance:,.2f}")

st.divider()

# Subida de archivos
archivo = st.file_uploader("Subí tus archivos aquí (PDF)", type="pdf", key=f"up_{id_periodo}")

if archivo and archivo.name not in periodo_actual["archivos"]:
    tipo, monto = procesar_archivo_universal(archivo)
    if tipo == "RECIBO ANSA":
        periodo_actual["ingresos"] += monto
        periodo_actual["archivos"].append(archivo.name)
    elif tipo != "DESCONOCIDO":
        periodo_actual["gastos"].append({"nombre": archivo.name, "tipo": tipo, "monto": monto})
        periodo_actual["archivos"].append(archivo.name)
    
    # GUARDAR CAMBIOS
    guardar_datos_gsheet(st.session_state.datos_mensuales)
    st.success(f"Cargado: {tipo} por $ {monto}")
    st.rerun()

# --- 8. TABLAS Y GRÁFICOS ---
col_izq, col_der = st.columns(2)

with col_izq:
    if periodo_actual["gastos"]:
        st.write("### Detalle de Gastos")
        df_gastos = pd.DataFrame(periodo_actual["gastos"])
        st.table(df_gastos[['tipo', 'monto']])
    
    if st.button("🗑️ Reiniciar Datos del Mes"):
        st.session_state.datos_mensuales[id_periodo] = {"ingresos": 0.0, "gastos": [], "archivos": []}
        guardar_datos_gsheet(st.session_state.datos_mensuales)
        st.rerun()

with col_der:
    if ingresos_totales > 0 or gastos_totales > 0:
        st.write("### Distribución")
        # Agrupamos gastos por tipo para el gráfico
        resumen = {}
        for g in periodo_actual["gastos"]:
            resumen[g['tipo']] = resumen.get(g['tipo'], 0) + g['monto']
        if balance > 0:
            resumen['Disponible'] = balance
        
        fig = px.pie(values=list(resumen.values()), names=list(resumen.keys()), hole=0.5, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
