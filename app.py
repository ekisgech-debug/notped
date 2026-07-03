import streamlit as st
from supabase import create_client, Client
import os
import uuid

# Configuración visual
st.set_page_config(page_title="NotPed - B2B", page_icon="👞", layout="wide")

@st.cache_resource
def init_connection():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase: Client = init_connection()

# --- ESTADO DE SESIÓN ---
if "usuario_actual" not in st.session_state: st.session_state.usuario_actual = None
if "rol_actual" not in st.session_state: st.session_state.rol_actual = None
if "marca_actual" not in st.session_state: st.session_state.marca_actual = None
if "modo_registro" not in st.session_state: st.session_state.modo_registro = False

# --- PANTALLA DE INGRESO / REGISTRO ---
if st.session_state.usuario_actual is None:
    st.title("Bienvenido a NotPed")
    
    # Alternar entre Login y Registro
    if not st.session_state.modo_registro:
        # PANTALLA DE LOGIN
        with st.form("login_form"):
            st.subheader("Iniciar Sesión")
            usr = st.text_input("Usuario")
            pwd = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Ingresar")
            
            if submit:
                res = supabase.table("usuarios").select("*").eq("usuario", usr).eq("contrasena", pwd).execute()
                if res.data:
                    datos = res.data[0]
                    st.session_state.usuario_actual = datos["usuario"]
                    st.session_state.rol_actual = datos["rol"]
                    st.session_state.marca_actual = datos["nombre_marca"]
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
        
        if st.button("¿No tienes cuenta? Regístrate aquí"):
            st.session_state.modo_registro = True
            st.rerun()
            
    else:
        # PANTALLA DE REGISTRO
        with st.form("registro_form"):
            st.subheader("Crear Cuenta Nueva")
            new_usr = st.text_input("Nombre de Usuario")
            new_pwd = st.text_input("Contraseña", type="password")
            new_marca = st.text_input("Nombre de tu Negocio/Marca")
            
            # --- NUEVO SELECTOR DE ROL ---
            tipo_cuenta = st.selectbox(
                "¿Qué tipo de cuenta necesitas?", 
                ["Revendedor (Quiero comprar)", "Fábrica/Proveedor (Quiero vender)"]
            )
            
            submit_reg = st.form_submit_button("Registrarse")
            
            if submit_reg:
                if new_usr and new_pwd and new_marca:
                    # Asignamos el rol interno según lo que eligió en el selector
                    rol_asignado = "proveedor" if "Fábrica" in tipo_cuenta else "revendedor"
                    
                    try:
                        nuevo_user = {
                            "usuario": new_usr,
                            "contrasena": new_pwd,
                            "rol": rol_asignado,
                            "nombre_marca": new_marca
                        }
                        supabase.table("usuarios").insert(nuevo_user).execute()
                        st.success("✅ Cuenta creada con éxito. Ya puedes iniciar sesión.")
                        st.session_state.modo_registro = False
                        st.rerun()
                    except Exception as e:
                        st.error("Error: El usuario ya existe o hubo un problema de conexión.")
                else:
                    st.warning("⚠️ Por favor completa todos los campos.")
        
        if st.button("Volver al Login"):
            st.session_state.modo_registro = False
            st.rerun()

# --- SISTEMA PRINCIPAL (YA LOGUEADO) ---
else:
    with st.sidebar:
        st.markdown(f"### {st.session_state.marca_actual}")
        st.write(f"**Perfil:** {st.session_state.rol_actual.capitalize()}")
        st.write("---")
        if st.button("Cerrar Sesión"):
            st.session_state.usuario_actual = None
            st.session_state.rol_actual = None
            st.session_state.marca_actual = None
            st.rerun()
            
    # VISTA PARA PROVEEDORES (Fábrica)
    if st.session_state.rol_actual == "proveedor":
        st.title("📦 Panel de Control")
        with st.expander("➕ Cargar Nuevo Producto", expanded=False):
            with st.form("form_carga", clear_on_submit=True):
                articulo = st.text_input("Artículo (Ej: Bota de Cuero)")
                categoria = st.selectbox("Categoría", ["General", "Colegial", "Urbano", "Deportivo", "Vestir"])
                precio = st.number_input("Precio ($)", min_value=0)
                curva = st.text_input("Curva de Talles (Ej: 35-40)")
                foto = st.file_uploader("Foto del Producto", type=["jpg", "png", "jpeg"])
                submit_prod = st.form_submit_button("Guardar Producto")

                if submit_prod:
                    if not articulo or not curva or not foto:
                        st.warning("⚠️ Completa los campos principales y sube una foto.")
                    else:
                        with st.spinner("Guardando..."):
                            try:
                                extension = foto.name.split('.')[-1]
                                nombre_archivo = f"{uuid.uuid4()}.{extension}"
                                supabase.storage.from_("fotos_productos").upload(
                                    nombre_archivo, foto.getvalue(), {"content-type": foto.type}
                                )
                                foto_url = supabase.storage.from_("fotos_productos").get_public_url(nombre_archivo)
                                
                                nuevo_producto = {
                                    "articulo": articulo, "categoria": categoria,
                                    "precio": precio, "curva": curva, "foto_url": foto_url
                                }
                                supabase.table("productos").insert(nuevo_producto).execute()
                                st.success("✅ ¡Producto cargado!")
                            except Exception as e:
                                st.error(f"Error: {e}")

    # VISTA PARA TODOS (Proveedores y Revendedores)
    st.write("---")
    st.title("👞 Catálogo Mayorista")
    
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
