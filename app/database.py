import os
from dotenv import load_dotenv
from arango import ArangoClient

# Cargar las variables del archivo .env
load_dotenv()

class GestorLogisticaDB:
    def __init__(self):
        # 1. CONFIGURACIÓN Y CONEXIÓN
        self.url = os.getenv("ARANGO_URL", "http://localhost:8529")
        self.username = os.getenv("ARANGO_USER", "root")
        self.password = os.getenv("ARANGO_PWD", "password_seguro")
        self.db_name = os.getenv("ARANGO_DB", "LogisticaDB")
        
        # Conectar al cliente de ArangoDB
        self.client = ArangoClient(hosts=self.url)
        self.sys_db = self.client.db('_system', username=self.username, password=self.password)
        
        # Conectar a la base de datos específica (se creará si no existe en inicializar_base_datos)
        self.db = None

    def inicializar_base_datos(self):
        """Borra la base de datos si existe, la recrea y monta el esquema de grafos."""
        print(f"Inicializando base de datos '{self.db_name}'...")
        
        # Crear base de datos si no existe
        if self.sys_db.has_database(self.db_name):
            self.sys_db.delete_database(self.db_name)
        self.sys_db.create_database(self.db_name)
        
        # Conectar a la nueva base de datos
        self.db = self.client.db(self.db_name, username=self.username, password=self.password)

        # 2. ESQUEMA DE DATOS (GRAFOS)
        # Crear colecciones de vértices (Documentos)
        almacenes = self.db.create_collection('Almacenes')
        productos = self.db.create_collection('Productos')

        # Crear colecciones de aristas (Edges)
        rutas = self.db.create_collection('Rutas', edge=True)
        stock_en = self.db.create_collection('Stock_en', edge=True)

        # Crear el Grafo
        grafo = self.db.create_graph('RedLogistica')
        
        # Vincular las aristas con sus vértices permitidos
        grafo.create_edge_definition(
            edge_collection='Rutas',
            from_vertex_collections=['Almacenes'],
            to_vertex_collections=['Almacenes']
        )
        grafo.create_edge_definition(
            edge_collection='Stock_en',
            from_vertex_collections=['Productos'],
            to_vertex_collections=['Almacenes']
        )
        print("Esqueleto de la base de datos y grafos creado con éxito.")

    def cargar_datos_prueba(self):
        """Inserta datos ficticios para poder probar la aplicación."""
        if not self.db:
            self.db = self.client.db(self.db_name, username=self.username, password=self.password)

        print("Cargando datos de prueba...")
        almacenes = self.db.collection('Almacenes')
        productos = self.db.collection('Productos')
        rutas = self.db.collection('Rutas')
        stock_en = self.db.collection('Stock_en')

        # 3. DATOS DE PRUEBA (MOCK DATA)
        # Insertar Almacenes
        ciudades = ["Madrid", "Barcelona", "Sevilla", "Valencia", "Bilbao"]
        for ciudad in ciudades:
            almacenes.insert({'_key': ciudad.lower(), 'nombre': f"Centro {ciudad}", 'ciudad': ciudad, 'capacidad': 1000})

        # Insertar Productos
        items = [
            {'key': 'p1', 'nombre': 'Portátil XPS', 'cat': 'Electrónica'},
            {'key': 'p2', 'nombre': 'Silla Ergonómica', 'cat': 'Mobiliario'},
            {'key': 'p3', 'nombre': 'Monitor 4K', 'cat': 'Electrónica'}
        ]
        for item in items:
            productos.insert({'_key': item['key'], 'nombre': item['nombre'], 'categoria': item['cat']})

        # Insertar Rutas (Aristas entre almacenes con distancia)
        rutas.insert({'_from': 'Almacenes/madrid', '_to': 'Almacenes/barcelona', 'distancia_km': 620})
        rutas.insert({'_from': 'Almacenes/madrid', '_to': 'Almacenes/sevilla', 'distancia_km': 530})
        rutas.insert({'_from': 'Almacenes/barcelona', '_to': 'Almacenes/valencia', 'distancia_km': 350})
        rutas.insert({'_from': 'Almacenes/madrid', '_to': 'Almacenes/bilbao', 'distancia_km': 400})
        rutas.insert({'_from': 'Almacenes/bilbao', '_to': 'Almacenes/barcelona', 'distancia_km': 610})

        # Insertar Stock (Aristas entre productos y almacenes)
        stock_en.insert({'_from': 'Productos/p1', '_to': 'Almacenes/madrid', 'cantidad': 50})
        stock_en.insert({'_from': 'Productos/p1', '_to': 'Almacenes/barcelona', 'cantidad': 20})
        stock_en.insert({'_from': 'Productos/p2', '_to': 'Almacenes/sevilla', 'cantidad': 100})
        stock_en.insert({'_from': 'Productos/p3', '_to': 'Almacenes/madrid', 'cantidad': 15})

        print("Datos de prueba cargados.")

    def obtener_ruta_optima(self, origen_key, destino_key):
        """4. MÉTODOS DE CONSULTA: Calcula el camino más corto y la distancia total."""
        if not self.db:
            self.db = self.client.db(self.db_name, username=self.username, password=self.password)

        # Consulta mejorada: agrupa las ciudades y suma la distancia
        # Usamos 'e ? e.distancia_km : 0' porque el nodo de origen no tiene arista previa (e es nulo)
        query = """
        LET ruta = (
            FOR v, e IN ANY SHORTEST_PATH @origen TO @destino
            Rutas
            OPTIONS { weightAttribute: 'distancia_km' }
            RETURN { ciudad: v.ciudad, distancia_tramo: e ? e.distancia_km : 0 }
        )
        FILTER LENGTH(ruta) > 0
        RETURN {
            ciudades_ruta: ruta[*].ciudad,
            distancia_total_km: SUM(ruta[*].distancia_tramo),
            detalle_tramos: ruta
        }
        """
        bind_vars = {
            'origen': f'Almacenes/{origen_key.lower()}',
            'destino': f'Almacenes/{destino_key.lower()}'
        }
        
        try:
            cursor = self.db.aql.execute(query, bind_vars=bind_vars)
            resultados = [doc for doc in cursor]
            
            # Protección: Si no hay conexión entre las ciudades
            if not resultados:
                return {"error": f"No existe una ruta posible entre {origen_key} y {destino_key}."}
                
            return resultados[0] # Devolvemos solo el diccionario con los totales
        except Exception as e:
            return {"error": f"Error al calcular la ruta: {e}"}

    def consultar_stock(self, producto_key):
        """4. MÉTODOS DE CONSULTA: Busca en qué almacenes hay un producto."""
        if not self.db:
            self.db = self.client.db(self.db_name, username=self.username, password=self.password)

        query = """
        FOR almacen, arista IN 1..1 OUTBOUND @producto GRAPH 'RedLogistica'
        FILTER arista.cantidad > 0
        RETURN { almacen: almacen.nombre, cantidad_disponible: arista.cantidad }
        """
        bind_vars = {'producto': f'Productos/{producto_key}'}
        
        try:
            cursor = self.db.aql.execute(query, bind_vars=bind_vars)
            return [doc for doc in cursor]
        except Exception as e:
            return f"Error al consultar stock: {e}"
        
    def ver_stock_almacen(self, almacen_key):
        """4. MÉTODOS DE CONSULTA: Busca qué productos hay en un almacén específico."""
        if not self.db:
            self.db = self.client.db(self.db_name, username=self.username, password=self.password)

        # Usamos INBOUND porque la flecha va de Producto a Almacén
        query = """
        FOR producto, arista IN 1..1 INBOUND @almacen GRAPH 'RedLogistica'
        FILTER arista.cantidad > 0
        SORT arista.cantidad DESC
        RETURN { 
            sku: producto._key,
            nombre: producto.nombre, 
            categoria: producto.categoria,
            unidades_disponibles: arista.cantidad 
        }
        """
        bind_vars = {'almacen': f'Almacenes/{almacen_key.lower()}'}
        
        try:
            cursor = self.db.aql.execute(query, bind_vars=bind_vars)
            resultados = [doc for doc in cursor]
            
            if not resultados:
                return {"mensaje": f"El almacén de {almacen_key} está vacío o no existe."}
            
            return resultados
        except Exception as e:
            return {"error": f"Error al consultar el almacén: {e}"}

    def cerrar_ruta(self, origen_key, destino_key):
        """MÉTODOS DE ESCRITURA: Elimina una arista del grafo simulando un corte de carretera."""
        if not self.db:
            self.db = self.client.db(self.db_name, username=self.username, password=self.password)

        query = """
        FOR arista IN Rutas
            FILTER arista._from == @origen AND arista._to == @destino
            REMOVE arista IN Rutas
            RETURN OLD
        """
        bind_vars = {
            'origen': f'Almacenes/{origen_key.lower()}',
            'destino': f'Almacenes/{destino_key.lower()}'
        }
        
        try:
            cursor = self.db.aql.execute(query, bind_vars=bind_vars)
            resultados = [doc for doc in cursor]
            if not resultados:
                return {"mensaje": "La ruta no existía previamente."}
            return {"mensaje": f"⚠️ Ruta cerrada con éxito entre {origen_key} y {destino_key}."}
        except Exception as e:
            return {"error": f"Error al cerrar la ruta: {e}"}
    
    def modificar_stock(self, almacen_key, producto_key, variacion):
        """MÉTODOS DE ESCRITURA: Suma o resta cantidad a un producto en un almacén."""
        if not self.db:
            self.db = self.client.db(self.db_name, username=self.username, password=self.password)

        # Buscamos la arista específica y le sumamos/restamos la 'variacion'
        query = """
        FOR arista IN Stock_en
            FILTER arista._from == @producto AND arista._to == @almacen
            LET nueva_cantidad = arista.cantidad + @variacion
            UPDATE arista WITH { cantidad: nueva_cantidad < 0 ? 0 : nueva_cantidad } IN Stock_en
            RETURN NEW
        """
        bind_vars = {
            'almacen': f'Almacenes/{almacen_key.lower()}',
            'producto': f'Productos/{producto_key}',
            'variacion': variacion
        }
        
        try:
            cursor = self.db.aql.execute(query, bind_vars=bind_vars)
            resultados = [doc for doc in cursor]
            
            if not resultados:
                return {"error": "No hay registro previo de ese producto en ese almacén."}
                
            nuevo_stock = resultados[0]['cantidad']
            return {"mensaje": f"Stock actualizado. Nueva cantidad: {nuevo_stock} unidades."}
        except Exception as e:
            return {"error": f"Error al modificar el stock: {e}"}
    
# --- Script de ejecución rápida para el Integrante A ---
if __name__ == "__main__":
    gestor = GestorLogisticaDB()
    # gestor.inicializar_base_datos() 
    # gestor.cargar_datos_prueba()
    
    print("\n--- PRUEBAS DE ESCRITURA (CRUD) ---")
    
    print("\n1. Llegada de mercancía: Añadimos 15 portátiles XPS (p1) a Madrid.")
    print(gestor.modificar_stock('madrid', 'p1', 15))
    
    print("\n2. Simulando accidente temporal: Cerramos ruta Madrid-Barcelona.")
    print(gestor.cerrar_ruta('madrid', 'barcelona'))
    
    print("\n3. Calculando nueva ruta alternativa de Madrid a Barcelona:")
    # Como cerramos el tramo directo, ahora el camión debería verse obligado a ir por otro sitio (ej: vía Zaragoza o Bilbao, según los datos de prueba que cargamos).
    print(gestor.obtener_ruta_optima('madrid', 'barcelona'))