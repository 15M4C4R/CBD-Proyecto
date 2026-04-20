import streamlit as st
from app.database import GestorLogisticaDB

# Configuración de la página
st.set_page_config(page_title="Sistema de Logística ArangoDB", layout="wide")

# --- INTEGRACIÓN DE BASE DE DATOS (YA COMPLETADA) ---
@st.cache_resource
def inicializar_sistema():
    """Instancia el gestor y establece la conexión con los repositorios CRUD."""
    try:
        gestor = GestorLogisticaDB()
        gestor.conectar() # Inicializa los módulos db.almacenes, db.productos, etc.
        return gestor
    except Exception as e:
        st.error(f"Error crítico de conexión: {e}")
        return None

# Objeto global listo para usar en la interfaz
db = inicializar_sistema()

# --- INTERFAZ DE USUARIO (PARA EL INTEGRANTE B) ---
if db:
    st.title("📦 Panel de Gestión Logística")
    st.sidebar.header("Opciones de Navegación")
    
    # Ejemplo de uso para el compañero:
    # menu = st.sidebar.radio("Selecciona una sección", ["Rutas", "Inventario", "Administración"])
    
    st.info("El sistema está conectado y los repositorios CRUD están listos para ser utilizados.")
else:
    st.stop() # Detiene la ejecución si no hay base de datos