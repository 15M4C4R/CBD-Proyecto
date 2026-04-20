import os
from dotenv import load_dotenv
from arango import ArangoClient
from app.crud import CRUDAlmacenes, CRUDProductos, CRUDRutas, CRUDStock

load_dotenv()

class GestorLogisticaDB:
    def __init__(self):
        self.url = os.getenv("ARANGO_URL", "http://localhost:8529")
        self.username = os.getenv("ARANGO_USER", "root")
        self.password = os.getenv("ARANGO_PWD", "password_seguro")
        self.db_name = os.getenv("ARANGO_DB", "LogisticaDB")
        
        self.client = ArangoClient(hosts=self.url)
        self.sys_db = self.client.db('_system', username=self.username, password=self.password)
        
        self.db = None
        
        # Inicializamos los submódulos CRUD vacíos. Se asignarán tras conectar a la BD.
        self.almacenes = None
        self.productos = None
        self.rutas = None
        self.stock = None

    def conectar(self):
        """Abre la conexión a la base de datos específica y enlaza las clases CRUD."""
        self.db = self.client.db(self.db_name, username=self.username, password=self.password)
        
        # Inyección de dependencias (Repository Pattern)
        self.almacenes = CRUDAlmacenes(self.db)
        self.productos = CRUDProductos(self.db)
        self.rutas = CRUDRutas(self.db)
        self.stock = CRUDStock(self.db)

    def inicializar_base_datos(self):
        print(f"Inicializando base de datos '{self.db_name}'...")
        if self.sys_db.has_database(self.db_name):
            self.sys_db.delete_database(self.db_name)
        self.sys_db.create_database(self.db_name)
        
        self.conectar()

        self.db.create_collection('Almacenes')
        self.db.create_collection('Productos')
        self.db.create_collection('Rutas', edge=True)
        self.db.create_collection('Stock_en', edge=True)

        grafo = self.db.create_graph('RedLogistica')
        grafo.create_edge_definition(edge_collection='Rutas', from_vertex_collections=['Almacenes'], to_vertex_collections=['Almacenes'])
        grafo.create_edge_definition(edge_collection='Stock_en', from_vertex_collections=['Productos'], to_vertex_collections=['Almacenes'])
        print("Esqueleto creado.")

    def cargar_datos_prueba(self):
        if not self.db:
            self.conectar()
            
        ciudades = ["Madrid", "Barcelona", "Sevilla", "Valencia", "Bilbao"]
        for ciudad in ciudades:
            self.almacenes.crear(ciudad, 1000)

        items = [('p1', 'Portátil XPS', 'Electrónica'), ('p2', 'Silla Ergonómica', 'Mobiliario'), ('p3', 'Monitor 4K', 'Electrónica')]
        for item in items:
            self.productos.crear(item[0], item[1], item[2])

        rutas = [('madrid','barcelona',620), ('madrid','sevilla',530), ('barcelona','valencia',350), ('madrid','bilbao',400), ('bilbao','barcelona',610)]
        for r in rutas:
            self.rutas.crear(r[0], r[1], r[2])

        stocks = [('madrid','p1',50), ('barcelona','p1',20), ('sevilla','p2',100), ('madrid','p3',15)]
        for s in stocks:
            self.stock.modificar(s[0], s[1], s[2])
            
        print("Datos de prueba cargados.")