import streamlit as st
import pandas as pd
from datetime import date
import sqlite3

# ==========================================
# 1. CONFIGURACIÓN GENERAL Y ESTILOS
# ==========================================
st.set_page_config(page_title="Portal de Mantenimiento - Grupo Cruces", page_icon="🔧", layout="wide")

AGENCIAS = ["GAC", "JAC", "CHIREY OMODA", "HYUNDAI", "GMC", "GWM"]
MAX_HORAS_DIA = 8
DB_NAME = "agenda_mantenimiento.db"
PIN_ADMIN = "2099"  # PIN de autorización exclusivo para administración

# ==========================================
# 2. MOTOR DE BASE DE DATOS
# ==========================================
def init_db():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS citas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT NOT NULL,
                    agencia TEXT NOT NULL,
                    gerente TEXT NOT NULL,
                    horas INTEGER NOT NULL,
                    trabajo TEXT NOT NULL,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    except Exception as e:
        st.error(f"Error crítico al inicializar la base de datos: {e}")

init_db()

def cargar_datos():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            query = """
                SELECT 
                    id AS ID, 
                    fecha AS Fecha, 
                    agencia AS Agencia, 
                    gerente AS Gerente, 
                    horas AS Horas, 
                    trabajo AS Trabajo 
                FROM citas 
                ORDER BY fecha ASC
            """
            return pd.read_sql_query(query, conn)
    except Exception as e:
        st.error(f"Error al leer registros: {e}")
        return pd.DataFrame(columns=["ID", "Fecha", "Agencia", "Gerente", "Horas", "Trabajo"])

def guardar_cita_atomica(fecha, agencia, gerente, horas, trabajo):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(horas) FROM citas WHERE fecha = ?", (fecha,))
            total_actual = cursor.fetchone()[0] or 0
            
            if (total_actual + horas) > MAX_HORAS_DIA:
                return False, (MAX_HORAS_DIA - total_actual)
            
            cursor.execute('''
                INSERT INTO citas (fecha, agencia, gerente, horas, trabajo)
                VALUES (?, ?, ?, ?, ?)
            ''', (fecha, agencia, gerente, horas, trabajo))
            conn.commit()
            return True, (MAX_HORAS_DIA - (total_actual + horas))
            
    except Exception as e:
        st.error(f"Error de escritura en servidor: {e}")
        return False, 0

def eliminar_cita(cita_id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM citas WHERE id = ?", (cita_id,))
            conn.commit()
            return True
    except Exception as e:
        st.error(f"No se pudo eliminar el registro: {e}")
        return False

df_citas = cargar_datos()

# ==========================================
# 3. BARRA LATERAL (RESPALDO DE DATOS)
# ==========================================
with st.sidebar:
    st.header("⚙️ Respaldo de Sistema")
    st.write("Descarga una copia de seguridad de la agenda.")
    
    if not df_citas.empty:
        csv = df_citas.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Respaldo (Excel/CSV)",
            data=csv,
            file_name=f"Respaldo_Agenda_{date.today()}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )
    else:
        st.info("No hay datos para respaldar.")
        
    st.divider()
    st.caption("🔒 Control de capacidad (8 hrs/día) y seguridad por PIN. Grupo Cruces.")

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================
st.title("🔧 Portal de Agenda de Mantenimiento")
st.markdown(f"**Capacidad técnica diaria:** `{MAX_HORAS_DIA} horas máximas por turno` | **Acceso:** `Publico para agendar / Restringido para modificar`.")

col_form, col_tabla = st.columns([1, 1.3], gap="large")

# --- COLUMNA IZQUIERDA: FORMULARIO PÚBLICO ---
with col_form:
    st.subheader("📅 Nueva Solicitud (Acceso Libre)")
    with st.form("form_agenda", clear_on_submit=True):
        agencia_in = st.selectbox("1. Agencia Solicitante", AGENCIAS)
        gerente_in = st.text_input("2. Nombre del Gerente / Solicitante").strip()
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_in = st.date_input("3. Fecha Requerida", min_value=date.today())
        with col_f2:
            horas_in = st.number_input("4. Tiempo (Horas)", min_value=1, max_value=MAX_HORAS_DIA, step=1)
            
        trabajo_in = st.text_area("5. Descripción técnica del trabajo (Ej. Mantenimiento de rampa)").strip()
        
        btn_enviar = st.form_submit_button("Agendar y Reservar Espacio", type="primary", use_container_width=True)

    if btn_enviar:
        if not gerente_in or not trabajo_in:
            st.warning("⚠️ Atención: Debes completar tu nombre y la descripción del trabajo.")
        else:
            fecha_str = str(fecha_in)
            exito, horas_restantes = guardar_cita_atomica(
                fecha=fecha_str,
                agencia=agencia_in,
                gerente=gerente_in,
                horas=int(horas_in),
                trabajo=trabajo_in
            )
            
            if exito:
                st.success(f"✅ ¡Reserva confirmada! Se asignaron {horas_in} hrs para {agencia_in} el día {fecha_str}.")
                st.info(f"⏳ Le quedan **{horas_restantes} horas disponibles** al técnico en esa fecha.")
                st.rerun()
            else:
                st.error(f"❌ **¡Solicitud Denegada!** La fecha {fecha_str} está saturada.")
                if horas_restantes > 0:
                    st.warning(f"👉 El técnico solo cuenta con **{horas_restantes} hora(s) libre(s)** ese día. Ajusta el tiempo de tu solicitud o elige otra fecha.")
                else:
                    st.warning("👉 La agenda para este día está al 100% de su capacidad (8/8 hrs ocupadas).")

# --- COLUMNA DERECHA: VISTA Y PANEL PROTEGIDO ---
with col_tabla:
    st.subheader("📋 Estado Actual de la Agenda")
    
    if not df_citas.empty:
        tab_ver, tab_admin = st.tabs(["👁️ Vista de Trabajos", "🔒 Administración y Modificaciones"])
        
        # Pestaña 1: Vista pública para que todos consulten qué está ocupado
        with tab_ver:
            st.dataframe(
                df_citas.drop(columns=["ID"]),
                use_container_width=True,
                hide_index=True,
                height=380
            )
            
        # Pestaña 2: Control de acceso restringido con PIN 2099
        with tab_admin:
            st.markdown("### 🛡️ Panel de Control Autorizado")
            st.write("Introduce el PIN de seguridad para liberar espacios o cancelar citas agendadas.")
            
            pin_ingresado = st.text_input("Contraseña / ID de autorización:", type="password", max_chars=10)
            
            if pin_ingresado == PIN_ADMIN:
                st.success("🔓 Acceso Autorizado. Puedes modificar la agenda.")
                st.divider()
                
                # Selector para eliminar y liberar horas
                opciones_citas = {
                    row["ID"]: f"ID {row['ID']} | {row['Fecha']} - {row['Agencia']} ({row['Horas']} hrs: {row['Trabajo'][:20]}...)"
                    for _, row in df_citas.iterrows()
                }
                
                id_a_cancelar = st.selectbox("Selecciona el servicio a cancelar y liberar:", list(opciones_citas.keys()), format_func=lambda x: opciones_citas[x])
                
                if st.button("🚨 Confirmar Cancelación y Liberar Horas", type="primary"):
                    if eliminar_cita(id_a_cancelar):
                        st.success("✅ Cita eliminada correctamente. Las horas han sido liberadas para esa fecha.")
                        st.rerun()
            elif pin_ingresado != "":
                st.error("⛔ Contraseña incorrecta. No tienes autorización para realizar modificaciones.")
    else:
        st.info("📌 No hay ningún trabajo programado actualmente. ¡La agenda está totalmente libre!")
