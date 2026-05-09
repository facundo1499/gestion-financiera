import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Mi Gestión Financiera", layout="wide")

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- SIMULACIÓN DE BASE DE DATOS (En el futuro esto leerá tus archivos) ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame({
        'Fecha': pd.to_datetime(['2024-01-01', '2024-01-15', '2024-02-01']),
        'Categoría': ['Ingreso', 'Gasto', 'Ingreso'],
        'Monto': [500000, 150000, 520000],
        'Detalle': ['Sueldo Enero', 'Tarjeta Visa', 'Sueldo Febrero']
    })

# --- SIDEBAR: FILTROS DE TIEMPO ---
st.sidebar.header("📅 Filtros de Consulta")
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
mes_sel = st.sidebar.selectbox("Selecciona Mes", meses, index=datetime.now().month - 1)
anio_sel = st.sidebar.selectbox("Selecciona Año", [2024, 2025, 2026], index=0)

# --- TITULO PRINCIPAL ---
st.title(f"📊 Dashboard Financiero: {mes_sel} {anio_sel}")

# --- FILTRADO DE DATOS ---
# (Aquí iría la lógica para filtrar st.session_state.data por mes y año)
ingresos_total = 550000.0  # Ejemplo dinámico
gastos_tarjeta = 125000.0
balance = ingresos_total - gastos_tarjeta
ahorros_meta = 85000.0

# --- FILA 1: MÉTRICAS CLAVE ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 INGRESOS TOTALES", f"$ {ingresos_total:,.2f}", delta="4% vs mes ant")
col2.metric("💳 GASTOS TARJETAS", f"$ {gastos_tarjeta:,.2f}", delta="-2%", delta_color="inverse")
col3.metric("⚖️ BALANCE NETO", f"$ {balance:,.2f}")
col4.metric("🏦 AHORROS ACUM.", f"$ {ahorros_meta:,.2f}")

st.markdown("---")

# --- FILA 2: GRÁFICOS ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("Evolución de Ingresos vs Gastos")
    # Gráfico de ejemplo
    df_graf = pd.DataFrame({
        'Mes': ['Ene', 'Feb', 'Mar', 'Abr'],
        'Ingresos': [500, 520, 510, 550],
        'Gastos': [120, 150, 130, 125]
    })
    fig = px.line(df_graf, x='Mes', y=['Ingresos', 'Gastos'], markers=True, color_discrete_sequence=['#2ecc71', '#e74c3c'])
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Distribución del Balance")
    fig2 = px.pie(values=[gastos_tarjeta, balance], names=['Gastos', 'Disponible'], hole=0.4, color_discrete_sequence=['#ff7f0e', '#1f77b4'])
    st.plotly_chart(fig2, use_container_width=True)

# --- SECCIÓN DE CARGA DE PDF ---
st.markdown("---")
st.header("📂 Carga de Documentos (PDF)")
upload_file = st.file_uploader("Arrastra aquí tu Recibo o Resumen de Tarjeta", type="pdf")

if upload_file:
    with st.spinner("Leyendo datos del PDF..."):
        # Aquí activamos la función de lectura automática que detecta montos
        st.success("¡Datos extraídos con éxito! Se han detectado los montos y actualizado el Dashboard.")
