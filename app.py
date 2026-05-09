import streamlit as st
import pandas as pd
import json
from datetime import datetime
import re

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestión Financiera Pro", layout="wide")

# --- 1. CONEXIÓN SIMPLIFICADA A GOOGLE SHEETS ---
# Esta versión usa GSpread que es más estable con las llaves privadas
import gspread
from google.oauth2.service_account import Credentials

def conectar_google():
    try:
        # Extraemos la llave de los secrets
        llave_cruda = st.secrets["connections"]["gsheets"]["private_key"]
        
        # LIMPIEZA AUTOMÁTICA: 
        # 1. Quitamos espacios vacíos al inicio y final
        # 2. Convertimos los saltos de línea literales (\n) en saltos reales
        llave_limpia = llave_cruda.strip().replace("\\n", "\n")
        
        # Si por alguna razón faltan los encabezados, los agregamos
        if "-----BEGIN PRIVATE KEY-----" not in llave_limpia:
            llave_limpia = "-----BEGIN PRIVATE KEY-----\n" + llave_limpia + "\n-----END PRIVATE KEY-----"

        info_dict = {
            "type": "service_account",
            "project_id": st.secrets["connections"]["gsheets"]["project_id"],
            "private_key": llave_limpia,
            "client_email": st.secrets["connections"]["gsheets"]["client_email"],
            "client_id": st.secrets["connections"]["gsheets"]["client_id"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"],
        }
        
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Conexión directa por URL
        sheet = client.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])
        return sheet.get_worksheet(0)
    except Exception as e:
        st.error(f"Error de conexión (Llave): {e}")
        return None
# --- 2. FUNCIONES DE CARGA Y GUARDADO ---
def cargar_datos():
    ws = conectar_google()
    if ws:
        data = ws.get_all_records()
        if not data:
            return {}
        
        df = pd.DataFrame(data)
        datos_dict = {}
        for _, row in df.iterrows():
            datos_dict[str(row['Periodo'])] = {
                "ingresos": float(row['Ingresos']),
                "gastos": json.loads(row['Gastos_JSON']),
                "archivos": json.loads(row['Archivos_JSON'])
            }
        return datos_dict
    return {}

def guardar_datos(datos_dict):
    ws = conectar_google()
    if ws and datos_dict:
        # Preparar encabezados
        filas = [["Periodo", "Ingresos", "Gastos_JSON", "Archivos_JSON"]]
        for periodo, info in datos_dict.items():
            filas.append([
                periodo,
                info["ingresos"],
                json.dumps(info["gastos"]),
                json.dumps(info["archivos"])
            ])
        
        ws.clear()
        ws.update('A1', filas)
        st.sidebar.success("✅ Guardado en Google Sheets")

# --- 3. INICIALIZACIÓN ---
if 'datos_mensuales' not in st.session_state:
    with st.spinner("Cargando base de datos..."):
        st.session_state.datos_mensuales = cargar_datos()

# --- 4. SIDEBAR (FILTROS) ---
st.sidebar.title("📅 Periodo")
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
mes_sel = st.sidebar.selectbox("Mes", meses, index=datetime.now().month - 1)
anio_sel = st.sidebar.selectbox("Año", [2024, 2025, 2026], index=2)
id_periodo = f"{mes_sel}-{anio_sel}"

if st.sidebar.button("🔄 Forzar Sincronización"):
    st.session_state.datos_mensuales = cargar_datos()
    st.rerun()

# Inicializar periodo si no existe
if id_periodo not in st.session_state.datos_mensuales:
    st.session_state.datos_mensuales[id_periodo] = {"ingresos": 0.0, "gastos": [], "archivos": []}

periodo_actual = st.session_state.datos_mensuales[id_periodo]

# --- 5. LÓGICA DE PROCESAMIENTO ---
st.title(f"📊 Gestión Financiera: {id_periodo}")

archivo_subido = st.file_uploader("Subir comprobante (PDF)", type=["pdf"])

if archivo_subido:
    # EL BOTÓN AHORA ESTÁ AFUERA PARA QUE SEA VISIBLE
    if st.button("🚀 Procesar Datos y Guardar"):
        with st.spinner("Extrayendo información..."):
            # --- AQUÍ VA TU LÓGICA REAL DE EXTRACCIÓN ---
            # Por ahora, simulamos que encontró un gasto para probar la conexión
            nombre_archivo = archivo_subido.name
            nuevo_gasto = {"item": nombre_archivo, "monto": 1000.0} # Monto de prueba
            
            # Actualizamos el estado
            st.session_state.datos_mensuales[id_periodo]["gastos"].append(nuevo_gasto)
            
            # Guardamos en Google Sheets
            guardar_datos(st.session_state.datos_mensuales)
            
            st.success(f"Archivo {nombre_archivo} procesado con éxito.")
            st.rerun()
# --- 6. DASHBOARD ---
col1, col2 = st.columns(2)
with col1:
    st.metric("Total Ingresos", f"$ {periodo_actual['ingresos']:,.2f}")
with col2:
    total_gastos = sum(g['monto'] for g in periodo_actual['gastos'])
    st.metric("Total Gastos", f"$ {total_gastos:,.2f}")

st.write("### Detalle de Gastos")
if periodo_actual["gastos"]:
    st.table(pd.DataFrame(periodo_actual["gastos"]))
else:
    st.info("No hay gastos registrados en este periodo.")
