import streamlit as st
from arango import ArangoClient
import os

st.title("Prueba de Conexión ArangoDB")

url = os.getenv("ARANGO_URL", "http://localhost:8529")
pwd = os.getenv("ARANGO_PWD", "password_seguro")

try:
    client = ArangoClient(hosts=url)
    sys_db = client.db('_system', username='root', password=pwd)
    st.success("¡Conexión establecida con ArangoDB dentro de Docker!")
except Exception as e:
    st.error(f"Error de conexión: {e}")