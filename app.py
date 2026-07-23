import streamlit as st
import pandas as pd
from datetime import date
import sqlite3

# Configuración de la página
st.set_page_config(page_title="Agenda de Mantenimiento", page_icon="⏱️", layout="centered")

AGENCIAS = ["GAC", "JAC", "CHIREY OMODA", "HYUNDAI", "GMC", "GWM"]
MAX_HORAS_DIA = 8

st.title("⏱️ Agenda de Mantenimiento Técnico")
st.write(f"Turno máximo del técnico: **{MAX_HORAS_DIA} horas diarias**.")

# ----------------------------------------------------
# BASE DE DATOS AUTOMÁTICA EN LA NUBE
# ----------------------------------------------------
DB_NAME = "agenda.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            agencia TEXT,
            gerente TEXT,
            horas INTEGER,
            trabajo TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def cargar_datos():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM citas", conn)
    conn.close()
    return df

def guardar_cita(fecha, agencia, gerente, horas, trabajo):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO citas (fecha, agencia, gerente, horas, trabajo)
        VALUES (?, ?, ?, ?, ?)
    ''', (fecha, agencia, gerente, horas, trabajo))
    conn.commit()
    conn.close()

df = cargar_datos()

# ----------------------------------------------------
# FORMULARIO PARA LOS GERENTES
# ----------------------------------------------------
with st.form("agenda_form"):
    col1, col2 = st.columns(2)
    with col1:
        agencia = st.selectbox("1. Agencia Solicitante", AGENCIAS)
        gerente = st.text_input("2. Nombre del Gerente")
    with col2:
        fecha = st.date_input("3. Fecha del Servicio", min_value=date.today())
        horas = st.number_input("4. Tiempo estimado (Horas)", min_value=1, max_value=8, step=1)
        
    trabajo = st.text_area("5. Descripción del Trabajo (Ej. Mantenimiento de rampa)")
    submit = st.form_submit_button("📅 Solicitar Espacio", type="primary")

# ----------------------------------------------------
# LÓGICA DE VALIDACIÓN (LÍMITE DE 8 HORAS)
# ----------------------------------------------------
if submit:
    if not gerente or not trabajo:
        st.warning("⚠️ Por favor llena todos los campos.")
    else:
        fecha_str = str(fecha)
        
        # Calcular cuántas horas ya están ocupadas en esa fecha
        df_fecha = df[df['Fecha'] == fecha_str] if not df.empty else pd.DataFrame()
        horas_ocupadas_hoy = df_fecha['Horas'].sum() if not df_fecha.empty else 0
        horas_disponibles = MAX_HORAS_DIA - horas_ocupadas_hoy
        
        if horas > horas_disponibles:
            st.error(f"❌ ¡Día saturado! El {fecha_str} solo cuenta con **{horas_disponibles} horas libres** (Máximo {MAX_HORAS_DIA} hrs).")
        else:
            guardar_cita(fecha_str, agencia, gerente, horas, trabajo)
            st.success(f"✅ ¡Cita guardada con éxito! Se reservaron {horas} hrs para {agencia}.")
            st.rerun()

# ----------------------------------------------------
# TABLA DE CONTROL VISUAL
# ----------------------------------------------------
st.divider()
st.subheader("📋 Resumen General de Trabajos")
if not df.empty:
    st.dataframe(df.drop(columns=['id']), width='stretch', hide_index=True)
else:
    st.info("No hay trabajos agendados todavía.")
