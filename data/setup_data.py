import time
import os
from app.database import GestorLogisticaDB

def main():
    gestor = GestorLogisticaDB()
    max_retries = 10
    retry_delay = 5

    for i in range(max_retries):
        try:
            gestor.conectar()
            print("Conectado a ArangoDB.")
            break
        except Exception:
            print(f"Esperando a ArangoDB... ({i+1}/{max_retries})")
            time.sleep(retry_delay)
    else:
        print("No se pudo conectar a ArangoDB.")
        return

    gestor.inicializar_base_datos()
    gestor.cargar_datos_prueba()
    print("Sistema listo.")

if __name__ == "__main__":
    main()
