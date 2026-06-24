import streamlit as st
from supabase import create_client, Client
import os

# Configuración visual de la página
st.set_page_config(page_title="NotPed", page_icon="👞", layout="centered")

st.title("NotPed - Plataforma B2B")
st.subheader("¡Base de datos conectada!")

# 1. Función para conectar a la base de datos usando las llaves de Render
@st.cache_resource
def init_connection():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        st.error("Faltan las credenciales de Supabase. Revisa Render.")
        st.stop()
    return create_client(url, key)

# Conectamos...
supabase: Client = init_connection()

st.write("---")
st.write("### Nuestro Catálogo en Vivo:")

# 2. Vamos a buscar los datos a la tabla 'productos'
try:
    respuesta = supabase.table("productos").select("*").execute()
    productos = respuesta.data

    # Si hay productos, los mostramos en una tabla
    if productos:
        st.dataframe(productos)
    else:
        st.info("No hay productos cargados todavía.")
except Exception as e:
    st.error(f"Hubo un error al traer los datos: {e}")
