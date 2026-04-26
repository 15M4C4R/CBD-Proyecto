import streamlit as st
import pandas as pd
from app.database import GestorLogisticaDB
import json
import streamlit.components.v1 as components

# Configuración de la página
st.set_page_config(page_title="Sistema de Logística ArangoDB", layout="wide")

@st.cache_resource
def inicializar_sistema():
    try:
        gestor = GestorLogisticaDB()
        gestor.conectar()
        return gestor
    except Exception as e:
        st.error(f"Error crítico de conexión: {e}")
        return None

db = inicializar_sistema()

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

if db:
    st.title("📦 Panel de Gestión Logística")
    
    st.sidebar.header("Navegación")
    menu = st.sidebar.radio("Sección", ["📦 Inventario", "🗺️ Rutas", "⚙️ Administración"])

    if menu == "📦 Inventario":
        st.header("Gestión de Inventario")
        tab1, tab2, tab3 = st.tabs(["Por Almacén", "Por Producto", "Modificar Stock"])

        with tab1:
            ciudades = obtener_ciudades()
            ciudad_sel = st.selectbox("Almacén", ciudades, key="inv_alm")
            if st.button("Consultar Stock"):
                resultados = db.stock.leer_por_almacen(ciudad_sel)
                if resultados and "error" not in resultados:
                    st.dataframe(pd.DataFrame(resultados), use_container_width=True)
                else:
                    st.info("Sin existencias.")

        with tab2:
            skus = obtener_skus()
            sku_sel = st.selectbox("Producto (SKU)", skus, key="inv_prod")
            if st.button("Consultar Disponibilidad"):
                resultados = db.stock.leer_por_producto(sku_sel)
                if resultados and "error" not in resultados:
                    st.dataframe(pd.DataFrame(resultados), use_container_width=True)
                else:
                    st.info("Producto no disponible.")

        with tab3:
            col1, col2, col3 = st.columns(3)
            with col1:
                alm_mod = st.selectbox("Almacén", obtener_ciudades(), key="mod_alm")
            with col2:
                prod_mod = st.selectbox("Producto", obtener_skus(), key="mod_prod")
            with col3:
                variacion = st.number_input("Variación", value=0, step=1)
            
            if st.button("Aplicar"):
                res = db.stock.modificar(alm_mod, prod_mod, variacion)
                if "error" not in res:
                    st.success("Stock actualizado.")
                else:
                    st.error(f"Error: {res.get('error')}")

    elif menu == "🗺️ Rutas":
        st.title("🗺️ Rutas y Red")
        tab_calc, tab_mapa = st.tabs(["Cálculo de Ruta", "Mapa Interactivo"])

        with tab_calc:
            st.header("Ruta Óptima")
            ciudades = obtener_ciudades()
            col1, col2 = st.columns(2)
            with col1:
                origen = st.selectbox("Origen", ciudades, key="ruta_origen")
            with col2:
                destino = st.selectbox("Destino", ciudades, key="ruta_destino")
                
            if st.button("Calcular"):
                if origen == destino:
                    st.warning("Origen y destino coinciden.")
                else:
                    resultado = db.rutas.leer_optima(origen, destino)
                    if "error" not in resultado:
                        st.success(f"Distancia: {resultado['distancia_total_km']} km")
                        st.write("**Ruta:**", " ➔ ".join(resultado['ciudades_ruta']))
                        st.dataframe(pd.DataFrame(resultado['detalle_tramos']))
                    else:
                        st.error("Ruta no encontrada.")

        with tab_mapa:
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
            
            aristas_lista = []
            query_rutas = "FOR r IN Rutas RETURN {orig: r._from, dest: r._to, dist: r.distancia_km}"
            cursor_rutas = db.db.aql.execute(query_rutas)
            for r in cursor_rutas:
                o = r['orig'].split('/')[-1].capitalize()
                d = r['dest'].split('/')[-1].capitalize()
                aristas_lista.append({
                    "from": o, 
                    "to": d, 
                    "label": f"{r['dist']} km", 
                    "arrows": "to"
                })

            html_code = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
              <style type="text/css">
                #mynetwork {{ width: 100%; height: 550px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9; }}
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
                  edges: {{ smooth: {{ type: 'continuous' }}, color: '#888' }}
                }};
                var network = new vis.Network(container, data, options);
              </script>
            </body>
            </html>
            """
            components.html(html_code, height=600)

    elif menu == "⚙️ Administración":
        st.header("Administración")
        tab_alm, tab_prod, tab_rutas = st.tabs(["Almacenes", "Productos", "Rutas"])

        with tab_alm:
            with st.form("form_nuevo_almacen"):
                n_ciudad = st.text_input("Ciudad")
                n_capacidad = st.number_input("Capacidad", min_value=1, value=1000)
                if st.form_submit_button("Crear"):
                    res = db.almacenes.crear(n_ciudad, n_capacidad)
                    if "error" not in res: st.success("Creado.")
                    else: st.error("Error al crear.")
            
            ciudades = obtener_ciudades()
            del_ciudad = st.selectbox("Eliminar almacén", ciudades)
            if st.button("Confirmar Eliminación"):
                res = db.almacenes.eliminar(del_ciudad)
                if "error" not in res: st.success("Eliminado.")
                else: st.error("Error.")

        with tab_prod:
            with st.form("form_nuevo_prod"):
                p_sku = st.text_input("SKU")
                p_nombre = st.text_input("Nombre")
                p_categoria = st.text_input("Categoría")
                if st.form_submit_button("Registrar"):
                    res = db.productos.crear(p_sku, p_nombre, p_categoria)
                    if "error" not in res: st.success("Registrado.")

        with tab_rutas:
            ciudades = obtener_ciudades()
            with st.form("form_nueva_ruta"):
                r_origen = st.selectbox("Origen", ciudades)
                r_destino = st.selectbox("Destino", ciudades)
                r_dist = st.number_input("Distancia (km)", min_value=1, value=100)
                if st.form_submit_button("Guardar Ruta"):
                    if r_origen != r_destino:
                        res = db.rutas.crear(r_origen, r_destino, r_dist)
                        if "error" not in res: st.success("Ruta guardada.")
                    else:
                        st.warning("Origen y destino deben ser distintos.")
else:
    st.error("Error de conexión con la base de datos.")
    st.stop()
else:
    st.error("No se pudo iniciar la aplicación por falta de conexión a la base de datos.")
    st.stop()