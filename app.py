import streamlit as st
from supabase import create_client, Client
import os
import uuid

# Configuración visual
st.set_page_config(page_title="NotPed - Panel", page_icon="👞", layout="centered")

@st.cache_resource
def init_connection():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase: Client = init_connection()

st.title("📦 Cargar Nuevo Producto")

# 1. Creamos el formulario visual
with st.form("form_carga", clear_on_submit=True):
    st.subheader("Datos del Calzado")
    
    articulo = st.text_input("Artículo (Ej: Bota de Cuero)")
    categoria = st.selectbox("Categoría", ["General", "Colegial", "Urbano", "Deportivo", "Vestir"])
    precio = st.number_input("Precio ($)", min_value=0)
    curva = st.text_input("Curva de Talles (Ej: 35-40)")
    foto = st.file_uploader("Foto del Producto", type=["jpg", "png", "jpeg"])

    submit = st.form_submit_button("Guardar Producto")

# 2. Lógica que se ejecuta al apretar el botón
if submit:
    if not articulo or not curva or not foto:
        st.warning("⚠️ Por favor completa los campos principales y sube una foto.")
    else:
        with st.spinner("Subiendo imagen y guardando datos..."):
            try:
                # A. Le damos un nombre único a la foto para que no se pisen los archivos
                extension = foto.name.split('.')[-1]
                nombre_archivo = f"{uuid.uuid4()}.{extension}"
                
                # B. Subimos la foto al "disco duro" (bucket) de Supabase
                supabase.storage.from_("fotos_productos").upload(
                    nombre_archivo,
                    foto.getvalue(),
                    {"content-type": foto.type}
                )
                
                # C. Obtenemos el link público de la foto
                foto_url = supabase.storage.from_("fotos_productos").get_public_url(nombre_archivo)
                
                # D. Guardamos toda la fila en la base de datos
                nuevo_producto = {
                    "articulo": articulo,
                    "categoria": categoria,
                    "precio": precio,
                    "curva": curva,
                    "foto_url": foto_url
                }
                supabase.table("productos").insert(nuevo_producto).execute()
                
                st.success("✅ ¡Producto cargado con éxito a la nube!")
            except Exception as e:
                st.error(f"Error al guardar: {e}")

st.write("---")
st.write("### Catálogo Actualizado")

# 3. Mostramos la tabla para ver cómo se va llenando
try:
    respuesta = supabase.table("productos").select("*").execute()
    if respuesta.data:
        st.dataframe(respuesta.data)
    else:
        st.info("No hay productos cargados todavía.")
except Exception as e:
    st.error("Error al cargar la tabla.")
