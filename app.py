import streamlit as st
from supabase import create_client, Client
import os
import uuid

# Configuración visual
st.set_page_config(page_title="Catálogo - Calzados Salamone", page_icon="👞", layout="wide")

@st.cache_resource
def init_connection():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase: Client = init_connection()

# --- SISTEMA DE LOGIN BÁSICO ---
# Revisamos si el usuario ya ingresó la clave
if "admin_autenticado" not in st.session_state:
    st.session_state.admin_autenticado = False

# Traemos la contraseña secreta de Render
CLAVE_SECRETA = os.environ.get("ADMIN_PASSWORD", "1234") 

# Creamos una barra lateral para el acceso
with st.sidebar:
    if not st.session_state.admin_autenticado:
        st.markdown("### Acceso Fábrica")
        clave_ingresada = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if clave_ingresada == CLAVE_SECRETA:
                st.session_state.admin_autenticado = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
    else:
        st.success("🟢 Administrador conectado")
        if st.button("Cerrar Sesión"):
            st.session_state.admin_autenticado = False
            st.rerun()

# --- FORMULARIO (SOLO VISIBLE PARA ADMIN) ---
if st.session_state.admin_autenticado:
    st.title("📦 Panel de Control: Cargar Nuevo Producto")
    with st.form("form_carga", clear_on_submit=True):
        st.subheader("Datos del Calzado")
        
        articulo = st.text_input("Artículo (Ej: Bota de Cuero)")
        categoria = st.selectbox("Categoría", ["General", "Colegial", "Urbano", "Deportivo", "Vestir"])
        precio = st.number_input("Precio ($)", min_value=0)
        curva = st.text_input("Curva de Talles (Ej: 35-40)")
        foto = st.file_uploader("Foto del Producto", type=["jpg", "png", "jpeg"])

        submit = st.form_submit_button("Guardar Producto")

    if submit:
        if not articulo or not curva or not foto:
            st.warning("⚠️ Por favor completa los campos principales y sube una foto.")
        else:
            with st.spinner("Subiendo imagen y guardando datos..."):
                try:
                    extension = foto.name.split('.')[-1]
                    nombre_archivo = f"{uuid.uuid4()}.{extension}"
                    
                    supabase.storage.from_("fotos_productos").upload(
                        nombre_archivo,
                        foto.getvalue(),
                        {"content-type": foto.type}
                    )
                    
                    foto_url = supabase.storage.from_("fotos_productos").get_public_url(nombre_archivo)
                    
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

# --- CATÁLOGO PÚBLICO (VISIBLE PARA TODOS) ---
st.title("👞 Catálogo en Vivo")

try:
    respuesta = supabase.table("productos").select("*").order("id", desc=True).execute()
    productos = respuesta.data

    if productos:
        columnas = st.columns(3)
        for index, prod in enumerate(productos):
            columna_actual = columnas[index % 3]
            with columna_actual:
                st.markdown(f"### {prod['articulo']}")
                if prod.get("foto_url"):
                    st.image(prod["foto_url"], use_container_width=True)
                st.markdown(f"**Categoría:** {prod['categoria']}")
                st.markdown(f"**Precio:** ${prod['precio']:,.0f}")
                st.markdown(f"**Curva:** {prod['curva']}")
                st.write("---")
    else:
        st.info("No hay productos cargados todavía.")
except Exception as e:
    st.error("Error al cargar el catálogo.")
