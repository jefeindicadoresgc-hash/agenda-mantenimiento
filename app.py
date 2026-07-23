import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(page_title="Agenda de Mantenimiento", page_icon="⏱️", layout="centered")

AGENCIAS = ["GAC", "JAC", "CHIREY OMODA", "HYUNDAI", "GMC", "GWM"]
MAX_HORAS_DIA = 8

st.title("⏱️ Agenda de Mantenimiento Técnico")
st.write(f"Turno máximo del técnico: **{MAX_HORAS_DIA} horas diarias**.")

# ----------------------------------------------------
# CONEXIÓN A GOOGLE SHEETS (Nube / GitHub Ready)
# ----------------------------------------------------
# Esto lee los datos de tu Google Sheet configurado en Streamlit Secrets o URL pública
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Leemos la hoja de cálculo
    df = conn.read(ttl=0)
    if df.empty or "Fecha" not in df.columns:
        df = pd.DataFrame(columns=["Fecha", "Agencia", "Gerente", "Horas", "Trabajo"])
except Exception as e:
    st.error("Error al conectar con la base de datos en la nube. Verifica la configuración.")
    df = pd.DataFrame(columns=["Fecha", "Agencia", "Gerente", "Horas", "Trabajo"])

# Limpieza de datos
if not df.empty:
    df['Horas'] = pd.to_numeric(df['Horas'], errors='coerce').fillna(0)
    df['Fecha'] = df['Fecha'].astype(str)

# ----------------------------------------------------
# FORMULARIO DE INTERFAZ
# ----------------------------------------------------
with st.form("agenda_form"):
    col1, col2 = st.columns(2)
    with col1:
        agencia = st.selectbox("1. Agencia Solicitante", AGENCIAS)
        gerente = st.text_input("2. Nombre del Gerente")
    with col2:
        fecha = st.date_input("3. Fecha del Servicio", min_value=date.today())
        horas = st.number_input("4. Tiempo estimado (Horas)", min_value=1, max_value=8, step=1)
        
    trabajo = st.text_area("5. Descripción del Trabajo (Ej. Revisión de rampa, climas)")
    submit = st.form_submit_button("📅 Solicitar Espacio", type="primary")

# ----------------------------------------------------
# LÓGICA DE VALIDACIÓN Y ESCRITURA EN LÍNEA
# ----------------------------------------------------
if submit:
    if not gerente or not trabajo:
        st.warning("⚠️ Por favor llena todos los campos.")
    else:
        fecha_str = str(fecha)
        
        # Calcular horas ocupadas en esa fecha según la base de datos en la nube
        df_fecha = df[df['Fecha'] == fecha_str] if not df.empty else pd.DataFrame()
        horas_ocupadas_hoy = df_fecha['Horas'].sum() if not df_fecha.empty else 0
        horas_disponibles = MAX_HORAS_DIA - horas_ocupadas_hoy
        
        if horas > horas_disponibles:
            st.error(f"❌ ¡Día saturado! El {fecha_str} solo cuenta con **{horas_disponibles} horas libres** (Máximo {MAX_HORAS_DIA} hrs).")
        else:
            # Crear nuevo registro
            nuevo_registro = pd.DataFrame([{
                "Fecha": fecha_str,
                "Agencia": agencia,
                "Gerente": gerente,
                "Horas": horas,
                "Trabajo": trabajo
            }])
            
            # Concatenar y actualizar en la nube
            df_actualizado = pd.concat([df, nuevo_registro], ignore_index=True)
            conn.update(data=df_actualizado)
            
            st.success(f"✅ ¡Cita guardada en línea! Se reservaron {horas} hrs para {agencia}.")
            st.rerun()

# ----------------------------------------------------
# TABLA DE CONTROL VISUAL
# ----------------------------------------------------
st.divider()
st.subheader("📋 Resumen General de Trabajos")
if not df.empty:
    st.dataframe(df, width='stretch', hide_index=True)
else:
    st.info("No hay trabajos agendados todavía.")