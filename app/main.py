import streamlit as st
import pandas as pd
from app.database import GestorLogisticaDB
import json
import streamlit.components.v1 as components

# Configuración de la página
st.set_page_config(page_title="Sistema de Logística ArangoDB", layout="wide")

# --- INTEGRACIÓN DE BASE DE DATOS ---
@st.cache_resource
def inicializar_sistema():
    """Instancia el gestor y establece la conexión con los repositorios CRUD."""
    try:
        gestor = GestorLogisticaDB()
        gestor.conectar()
        return gestor
    except Exception as e:
        st.error(f"Error crítico de conexión: {e}")
        return None

db = inicializar_sistema()

# --- FUNCIONES AUXILIARES ---
def obtener_ciudades():
    datos = db.almacenes.leer_todos()
    if isinstance(datos, list) and not "error" in datos:
        return [a['ciudad'] for a in datos]
    return []

def obtener_skus():
    datos = db.productos.leer_todos()
    if isinstance(datos, list) and not "error" in datos:
        return [p['_key'] for p in datos]
    return []

# --- INTERFAZ DE USUARIO ---
if db:
    st.title("📦 Panel de Gestión Logística")
    
    # Menú lateral
    st.sidebar.header("Opciones de Navegación")
    menu = st.sidebar.radio("Selecciona una sección", ["📦 Inventario", "🗺️ Rutas", "⚙️ Administración"])

    # ==========================================
    # SECCIÓN 1: INVENTARIO
    # ==========================================
    if menu == "📦 Inventario":
        st.header("Gestión de Inventario")
        tab1, tab2, tab3 = st.tabs(["Ver por Almacén", "Ver por Producto", "Modificar Stock"])

        with tab1:
            ciudades = obtener_ciudades()
            ciudad_sel = st.selectbox("Selecciona un Almacén (Ciudad)", ciudades, key="inv_alm")
            if st.button("Consultar Stock en Almacén"):
                resultados = db.stock.leer_por_almacen(ciudad_sel)
                if resultados and "error" not in resultados:
                    st.dataframe(pd.DataFrame(resultados), use_container_width=True)
                else:
                    st.info("No hay stock en este almacén o ocurrió un error.")

        with tab2:
            skus = obtener_skus()
            sku_sel = st.selectbox("Selecciona un Producto (SKU)", skus, key="inv_prod")
            if st.button("Consultar Disponibilidad"):
                resultados = db.stock.leer_por_producto(sku_sel)
                if resultados and "error" not in resultados:
                    st.dataframe(pd.DataFrame(resultados), use_container_width=True)
                else:
                    st.info("Este producto no se encuentra en ningún almacén.")

        with tab3:
            st.subheader("Añadir o retirar unidades")
            col1, col2, col3 = st.columns(3)
            with col1:
                alm_mod = st.selectbox("Almacén", obtener_ciudades(), key="mod_alm")
            with col2:
                prod_mod = st.selectbox("Producto (SKU)", obtener_skus(), key="mod_prod")
            with col3:
                variacion = st.number_input("Variación (Positivo para añadir, negativo para retirar)", value=0, step=1)
            
            if st.button("Aplicar Cambios"):
                res = db.stock.modificar(alm_mod, prod_mod, variacion)
                if "error" not in res:
                    st.success(f"Stock modificado con éxito. Nuevo registro: {res}")
                else:
                    st.error(f"Error al modificar stock: {res.get('error')}")

    # ==========================================
    # SECCIÓN 2: RUTAS
    # ==========================================
    elif menu == "🗺️ Rutas":
        st.title("🗺️ Gestión de Rutas y Red")
        
        # DEFINICIÓN DE PESTAÑAS
        tab_calc, tab_mapa = st.tabs(["Cálculo de Rutas Óptimas", "Mapa de Red Interactivo"])

        with tab_calc:
            st.header("Cálculo de Rutas Óptimas")
            st.markdown("Encuentra el camino más corto entre dos almacenes de la red logística.")
            
            ciudades = obtener_ciudades()
            col1, col2 = st.columns(2)
            with col1:
                origen = st.selectbox("Ciudad de Origen", ciudades, key="ruta_origen")
            with col2:
                destino = st.selectbox("Ciudad de Destino", ciudades, key="ruta_destino")
                
            if st.button("Calcular Ruta Óptima"):
                if origen == destino:
                    st.warning("El origen y destino son el mismo.")
                else:
                    resultado = db.rutas.leer_optima(origen, destino)
                    if "error" not in resultado:
                        st.success(f"Ruta encontrada: Distancia total de {resultado['distancia_total_km']} km")
                        st.write("**Ciudades a recorrer:**", " ➔ ".join(resultado['ciudades_ruta']))
                        st.dataframe(pd.DataFrame(resultado['detalle_tramos']))
                    else:
                        st.error(f"No se encontró una ruta válida: {resultado['error']}")

        with tab_mapa:
            st.header("Mapa de Red Interactivo")
            st.markdown("Arrastra las ciudades, haz zoom y explora las conexiones en tiempo real.")
            
            # 1. Extraemos los nodos desde la base de datos
            nodos_lista = []
            almacenes = db.almacenes.leer_todos()
            if isinstance(almacenes, list) and "error" not in almacenes:
                for a in almacenes:
                    nodos_lista.append({
                        "id": a["ciudad"], 
                        "label": f"{a['ciudad']}\n(Cap: {a['capacidad']})", 
                        "shape": "dot", 
                        "size": 25,
                        "color": "#4CAF50"
                    })
            
            # 2. Extraemos las aristas (Rutas) ejecutando AQL
            aristas_lista = []
            query_rutas = "FOR r IN Rutas RETURN {orig: r._from, dest: r._to, dist: r.distancia_km}"
            # Acceso directo al driver de arango a través de db.db
            cursor_rutas = db.db.aql.execute(query_rutas)
            for r in cursor_rutas:
                # Limpiamos IDs: 'Almacenes/madrid' -> 'Madrid'
                o = r['orig'].split('/')[-1].capitalize()
                d = r['dest'].split('/')[-1].capitalize()
                aristas_lista.append({
                    "from": o, 
                    "to": d, 
                    "label": f"{r['dist']} km", 
                    "arrows": "to",
                    "font": {"align": "middle"}
                })

            # 3. Construcción del HTML con Vis.js
            html_code = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
              <style type="text/css">
                #mynetwork {{
                  width: 100%;
                  height: 550px;
                  border: 1px solid #ddd;
                  border-radius: 8px;
                  background-color: #f9f9f9;
                }}
              </style>
            </head>
            <body>
              <div id="mynetwork"></div>
              <script type="text/javascript">
                var nodes = new vis.DataSet({json.dumps(nodos_lista)});
                var edges = new vis.DataSet({json.dumps(aristas_lista)});
                var container = document.getElementById('mynetwork');
                var data = {{ nodes: nodes, edges: edges }};
                var options = {{
                  physics: {{ stabilization: false, barnesHut: {{ springLength: 200 }} }},
                  edges: {{ smooth: {{ type: 'continuous' }}, color: '#888' }},
                  interaction: {{ hover: true, navigationButtons: true }}
                }};
                var network = new vis.Network(container, data, options);
              </script>
            </body>
            </html>
            """
            # 4. Renderizado del componente
            components.html(html_code, height=600)

    # ==========================================
    # SECCIÓN 3: ADMINISTRACIÓN
    # ==========================================
    elif menu == "⚙️ Administración":
        st.header("Administración de la Red Logística")
        tab_alm, tab_prod, tab_rutas = st.tabs(["Almacenes", "Productos", "Rutas"])

        with tab_alm:
            st.subheader("Registrar nuevo Almacén")
            with st.form("form_nuevo_almacen"):
                n_ciudad = st.text_input("Nombre de la Ciudad")
                n_capacidad = st.number_input("Capacidad", min_value=1, value=1000)
                submit_alm = st.form_submit_button("Crear Almacén")
                if submit_alm and n_ciudad:
                    res = db.almacenes.crear(n_ciudad, n_capacidad)
                    if "error" not in res:
                        st.success(f"Almacén en {n_ciudad} creado con éxito.")
                    else:
                        st.error(f"Error: {res.get('error')}")
            
            st.subheader("Eliminar Almacén (Borrado en Cascada)")
            ciudades = obtener_ciudades()
            del_ciudad = st.selectbox("Selecciona ciudad a eliminar", ciudades, key="del_alm")
            if st.button("Eliminar Almacén y sus conexiones"):
                res = db.almacenes.eliminar(del_ciudad)
                if "error" not in res:
                    st.success(f"Almacén {del_ciudad} y sus rutas/stock eliminados.")
                else:
                    st.error(f"Error: {res.get('error')}")

        with tab_prod:
            st.subheader("Registrar nuevo Producto")
            with st.form("form_nuevo_prod"):
                p_sku = st.text_input("SKU (Identificador único, ej. p4)")
                p_nombre = st.text_input("Nombre del producto")
                p_categoria = st.text_input("Categoría")
                submit_prod = st.form_submit_button("Crear Producto")
                if submit_prod and p_sku and p_nombre:
                    res = db.productos.crear(p_sku, p_nombre, p_categoria)
                    if "error" not in res:
                        st.success(f"Producto {p_nombre} creado con éxito.")
                    else:
                        st.error(f"Error: {res.get('error')}")

        with tab_rutas:
            st.subheader("Registrar nueva Ruta")
            ciudades = obtener_ciudades()
            with st.form("form_nueva_ruta"):
                col1, col2 = st.columns(2)
                with col1:
                    r_origen = st.selectbox("Origen", ciudades)
                with col2:
                    r_destino = st.selectbox("Destino", ciudades)
                r_dist = st.number_input("Distancia en km", min_value=1, value=100)
                submit_ruta = st.form_submit_button("Crear/Actualizar Ruta")
                
                if submit_ruta:
                    if r_origen != r_destino:
                        res = db.rutas.crear(r_origen, r_destino, r_dist)
                        if "error" not in res:
                            st.success(f"Ruta {r_origen} -> {r_destino} creada con éxito.")
                        else:
                            st.error(f"Error: {res.get('error')}")
                    else:
                        st.warning("El origen y destino no pueden ser la misma ciudad.")

else:
    st.error("No se pudo iniciar la aplicación por falta de conexión a la base de datos.")
    st.stop()