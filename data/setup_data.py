import time
from app.database import GestorLogisticaDB

def main():
    print("⏳ Esperando a que ArangoDB inicie por completo...")
    gestor = None
    
    # Reintentar conexión hasta 5 veces (esperando a que Docker levante el servicio DB)
    for i in range(5):
        try:
            gestor = GestorLogisticaDB()
            gestor.client.version() # Intentamos hacer "ping" al servidor
            break # Si funciona, salimos del bucle
        except Exception:
            print(f"🔄 Intento {i+1}/5: ArangoDB aún no está listo. Esperando 3 segundos...")
            time.sleep(3)
    
    if not gestor:
        print("❌ Error crítico: No se pudo conectar a ArangoDB.")
        return

    print("📦 Iniciando configuración de la base de datos ArangoDB...")
    try:
        gestor.inicializar_base_datos()
        gestor.cargar_datos_prueba()
        print("✅ ¡Base de datos lista y cargada con datos de prueba exitosamente!")
    except Exception as e:
        print(f"❌ Error durante la inicialización: {e}")

if __name__ == "__main__":
    main()