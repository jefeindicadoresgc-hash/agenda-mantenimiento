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

# ==========================================
# 2. MOTOR DE BASE DE DATOS (BLINDADO)
# ==========================================
def init_db():
    """Crea la tabla con esquema estricto si no existe."""
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
    """Lee datos forzando nombres de columnas estandarizados (Adiós KeyError)."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            # Usamos alias (AS) para obligar a Pandas a usar mayúsculas exactas
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
            df = pd.read_sql_query(query, conn)
            return df
    except Exception as e:
        st.error(f"Error al leer registros: {e}")
        # Retorna un DataFrame vacío con la estructura correcta para evitar caídas
        return pd.DataFrame(columns=["ID", "Fecha", "Agencia", "Gerente", "Horas", "Trabajo"])

def guardar_cita_atomica(fecha, agencia, gerente, horas, trabajo):
    """
    Validación atómica: Evita condiciones de carrera si 2 personas dan clic 
    al mismo tiempo. Revisa el cupo dentro de la misma transacción SQL.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Bloqueo de lectura de seguridad: ¿Cuántas horas van realmente hoy?
            cursor.execute("SELECT SUM(horas) FROM citas WHERE fecha = ?", (fecha,))
            total_actual = cursor.fetchone()[0] or 0
            
            if (total_actual + horas) > MAX_HORAS_DIA:
                # Retorna Falso y el número de horas que realmente quedan libres
                return False, (MAX_HORAS_DIA - total_actual)
            
            # Si hay cupo, procede con la inserción
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
    """Permite liberar horas si un gerente cancela o se equivoca."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM citas WHERE id = ?", (cita_id,))
            conn.commit()
            return True
    except Exception as e:
        st.error(f"No se pudo eliminar el registro: {e}")
        return False

# Carga inicial de datos en memoria segura
df_citas = cargar_datos()

# ==========================================
# 3. BARRA LATERAL (HERRAMIENTAS DE RESPALDO)
# ==========================================
with st.sidebar:
    st.header("⚙️ Administración")
    st.write("Herramientas de control y seguridad.")
    
    # Respaldo de seguridad contra reinicios de nube
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
    st.caption("🔒 Sistema de control de capacidad máxima (8 hrs/día). Grupo Cruces.")

# ==========================================
# 4. INTERFAZ PRINCIPAL (UI RESPONSIVA)
# ==========================================
st.title("🔧 Portal de Agenda de Mantenimiento")
st.markdown(f"**Capacidad técnica estricta:** `{MAX_HORAS_DIA} horas máximas por turno diario`.")

col_form, col_tabla = st.columns([1, 1.3], gap="large")

# --- COLUMNA IZQUIERDA: FORMULARIO ---
with col_form:
    st.subheader("📅 Nueva Solicitud")
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

    # Lógica al presionar el botón
    if btn_enviar:
        if not gerente_in or not trabajo_in:
            st.warning("⚠️ Atención: Debes completar tu nombre y la descripción del trabajo.")
        else:
            fecha_str = str(fecha_in)
            
            # Intento de guardado atómico
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

# --- COLUMNA DERECHA: TABLA Y GESTIÓN ---
with col_tabla:
    st.subheader("📋 Estado Actual de la Agenda")
    
    if not df_citas.empty:
        # Pestañas para ver la tabla o cancelar citas
        tab_ver, tab_cancelar = st.tabs(["👁️ Vista de Trabajos", "🗑️ Liberar / Cancelar Cita"])
        
        with tab_ver:
            # Mostramos la tabla sin el ID interno para que se vea limpia
            st.dataframe(
                df_citas.drop(columns=["ID"]),
                use_container_width=True,
                hide_index=True,
                height=380
            )
            
        with tab_cancelar:
            st.write("Si necesitas cancelar un trabajo para liberar las horas del técnico, búscalo por su número de ID:")
            # Creamos un diccionario para que sea fácil elegir qué cita cancelar
            opciones_citas = {
                row["ID"]: f"ID {row['ID']} | {row['Fecha']} - {row['Agencia']} ({row['Horas']} hrs: {row['Trabajo'][:20]}...)"
                for _, row in df_citas.iterrows()
            }
            
            id_a_cancelar = st.selectbox("Selecciona el servicio a cancelar:", list(opciones_citas.keys()), format_func=lambda x: opciones_citas[x])
            
            if st.button("🚨 Confirmar Cancelación y Liberar Horas", type="secondary"):
                if eliminar_cita(id_a_cancelar):
                    st.success("✅ Cita eliminada correctamente. Las horas han sido liberadas.")
                    st.rerun()
    else:
        st.info("📌 No hay ningún trabajo programado actualmente. ¡La agenda está totalmente libre!")
