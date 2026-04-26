class CRUDAlmacenes:
    def __init__(self, db):
        self.db = db

    def crear(self, ciudad, capacidad):
        query = "INSERT { _key: LOWER(@c), nombre: CONCAT('Centro ', @c), ciudad: @c, capacidad: @cap } INTO Almacenes RETURN NEW"
        return self._ejecutar(query, {'c': ciudad.capitalize(), 'cap': capacidad})

    def leer_todos(self):
        query = "FOR a IN Almacenes RETURN a"
        return self._ejecutar(query)

    def actualizar(self, key, nueva_capacidad):
        query = "UPDATE @k WITH { capacidad: @cap } IN Almacenes RETURN NEW"
        return self._ejecutar(query, {'k': key.lower(), 'cap': nueva_capacidad})

    def eliminar(self, key):
        key_id = f"Almacenes/{key.lower()}"
        query = """
        LET aristas_rutas = (FOR r IN Rutas FILTER r._from == @id OR r._to == @id REMOVE r IN Rutas)
        LET aristas_stock = (FOR s IN Stock_en FILTER s._to == @id REMOVE s IN Stock_en)
        REMOVE @k IN Almacenes RETURN OLD
        """
        return self._ejecutar(query, {'k': key.lower(), 'id': key_id})

    def _ejecutar(self, query, bind_vars=None):
        try:
            cursor = self.db.aql.execute(query, bind_vars=bind_vars or {})
            return [doc for doc in cursor]
        except Exception as e:
            return {"error": str(e)}


class CRUDProductos:
    def __init__(self, db):
        self.db = db

    def crear(self, sku, nombre, categoria):
        query = "INSERT { _key: LOWER(@s), nombre: @n, categoria: @c } INTO Productos RETURN NEW"
        return self._ejecutar(query, {'s': sku, 'n': nombre, 'c': categoria})

    def leer_todos(self):
        query = "FOR p IN Productos RETURN p"
        return self._ejecutar(query)

    def actualizar(self, sku, nombre, categoria):
        query = "UPDATE @k WITH { nombre: @n, categoria: @c } IN Productos RETURN NEW"
        return self._ejecutar(query, {'k': sku.lower(), 'n': nombre, 'c': categoria})

    def eliminar(self, sku):
        key_id = f"Productos/{sku.lower()}"
        query = """
        LET aristas_stock = (FOR s IN Stock_en FILTER s._from == @id REMOVE s IN Stock_en)
        REMOVE @k IN Productos RETURN OLD
        """
        return self._ejecutar(query, {'k': sku.lower(), 'id': key_id})

    def _ejecutar(self, query, bind_vars=None):
        try:
            return [doc for doc in self.db.aql.execute(query, bind_vars=bind_vars or {})]
        except Exception as e:
            return {"error": str(e)}


class CRUDRutas:
    def __init__(self, db):
        self.db = db

    def crear(self, origen, destino, distancia):
        query = "INSERT { _from: @o, _to: @d, distancia_km: @dist } INTO Rutas RETURN NEW"
        bind_vars = {'o': f'Almacenes/{origen.lower()}', 'd': f'Almacenes/{destino.lower()}', 'dist': distancia}
        return self._ejecutar(query, bind_vars)

    def leer_optima(self, origen, destino):
        query = """
        LET ruta = (FOR v, e IN ANY SHORTEST_PATH @o TO @d Rutas OPTIONS { weightAttribute: 'distancia_km' }
            RETURN { ciudad: v.ciudad, distancia_tramo: e ? e.distancia_km : 0 })
        FILTER LENGTH(ruta) > 0
        RETURN { ciudades_ruta: ruta[*].ciudad, distancia_total_km: SUM(ruta[*].distancia_tramo), detalle_tramos: ruta }
        """
        bind_vars = {'o': f'Almacenes/{origen.lower()}', 'd': f'Almacenes/{destino.lower()}'}
        res = self._ejecutar(query, bind_vars)
        return res[0] if res and isinstance(res, list) and not "error" in res else {"error": "Ruta no encontrada."}

    def actualizar(self, origen, destino, nueva_distancia):
        query = """
        FOR r IN Rutas FILTER r._from == @o AND r._to == @d
        UPDATE r WITH { distancia_km: @dist } IN Rutas RETURN NEW
        """
        bind_vars = {'o': f'Almacenes/{origen.lower()}', 'd': f'Almacenes/{destino.lower()}', 'dist': nueva_distancia}
        return self._ejecutar(query, bind_vars)

    def eliminar(self, origen, destino):
        query = "FOR r IN Rutas FILTER r._from == @o AND r._to == @d REMOVE r IN Rutas RETURN OLD"
        bind_vars = {'o': f'Almacenes/{origen.lower()}', 'd': f'Almacenes/{destino.lower()}'}
        return self._ejecutar(query, bind_vars)

    def _ejecutar(self, query, bind_vars=None):
        try:
            return [doc for doc in self.db.aql.execute(query, bind_vars=bind_vars or {})]
        except Exception as e:
            return {"error": str(e)}


class CRUDStock:
    def __init__(self, db):
        self.db = db

    def modificar(self, almacen, producto, variacion):
        query = """
        UPSERT { _from: @p, _to: @a }
        INSERT { _from: @p, _to: @a, cantidad: @var > 0 ? @var : 0 }
        UPDATE { cantidad: (OLD.cantidad + @var) < 0 ? 0 : (OLD.cantidad + @var) } IN Stock_en
        RETURN NEW
        """
        bind_vars = {'a': f'Almacenes/{almacen.lower()}', 'p': f'Productos/{producto.lower()}', 'var': variacion}
        return self._ejecutar(query, bind_vars)

    def leer_por_almacen(self, almacen):
        query = """
        FOR p, e IN 1..1 INBOUND @a GRAPH 'RedLogistica' FILTER e.cantidad > 0 SORT e.cantidad DESC
        RETURN { sku: p._key, nombre: p.nombre, categoria: p.categoria, unidades: e.cantidad }
        """
        return self._ejecutar(query, {'a': f'Almacenes/{almacen.lower()}'})

    def leer_por_producto(self, sku):
        query = """
        FOR a, e IN 1..1 OUTBOUND @p GRAPH 'RedLogistica' FILTER e.cantidad > 0
        RETURN { almacen: a.nombre, unidades: e.cantidad }
        """
        return self._ejecutar(query, {'p': f'Productos/{sku.lower()}'})

    def eliminar(self, almacen, producto):
        query = "FOR s IN Stock_en FILTER s._from == @p AND s._to == @a REMOVE s IN Stock_en RETURN OLD"
        bind_vars = {'a': f'Almacenes/{almacen.lower()}', 'p': f'Productos/{producto.lower()}'}
        return self._ejecutar(query, bind_vars)

    def _ejecutar(self, query, bind_vars=None):
        try:
            return [doc for doc in self.db.aql.execute(query, bind_vars=bind_vars or {})]
        except Exception as e:
            return {"error": str(e)}