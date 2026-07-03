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
                    st.error("Usuario o contraseña incorrectos.")
        
        if st.button("¿No tienes cuenta? Regístrate aquí"):
            st.session_state.modo_registro = True
            st.rerun()
            
    else:
        # PANTALLA DE REGISTRO
        with st.form("registro_form"):
            st.subheader("Crear Cuenta (Revendedor)")
            new_usr = st.text_input("Nombre de Usuario")
            new_pwd = st.text_input("Contraseña", type="password")
            new_marca = st.text_input("Nombre de tu Negocio/Marca")
            submit_reg = st.form_submit_button("Registrarse")
            
            if submit_reg:
                if new_usr and new_pwd and new_marca:
                    try:
                        nuevo_user = {
                            "usuario": new_usr,
                            "contrasena": new_pwd,
                            "rol": "revendedor", # Los que se registran solos son revendedores
                            "nombre_marca": new_marca
                        }
                        supabase.table("usuarios").insert(nuevo_user).execute()
                        st.success("✅ Cuenta creada. Ya puedes iniciar sesión.")
                        st.session_state.modo_registro = False
                        st.rerun()
                    except Exception as e:
                        st.error("Error: El usuario ya existe o hubo un problema.")
                else:
                    st.warning("Completa todos los campos.")
        
        if st.button("Volver al Login"):
            st.session_state.modo_registro = False
            st.rerun()

# --- SISTEMA PRINCIPAL (YA LOGUEADO) ---
else:
    # (El resto del código del sistema principal se mantiene igual...)
    with st.sidebar:
        st.markdown(f"### {st.session_state.marca_actual}")
        st.write(f"**Perfil:** {st.session_state.rol_actual.capitalize()}")
        if st.button("Cerrar Sesión"):
            st.session_state.usuario_actual = None
            st.rerun()
            
    # Vista Proveedor
    if st.session_state.rol_actual == "proveedor":
        st.title("📦 Panel de Control")
        # [Carga de productos...]
        # (Aquí va el mismo código de carga que ya tenías)
        with st.expander("➕ Cargar Nuevo Producto"):
            with st.form("form_carga", clear_on_submit=True):
                articulo = st.text_input("Artículo")
                categoria = st.selectbox("Categoría", ["General", "Colegial", "Urbano", "Deportivo", "Vestir"])
                precio = st.number_input("Precio ($)", min_value=0)
                curva = st.text_input("Curva de Talles")
                foto = st.file_uploader("Foto", type=["jpg", "png", "jpeg"])
                if st.form_submit_button("Guardar"):
                    # (Aquí mantienes tu lógica de subida de fotos de antes)
                    st.success("Cargado!")
    
    # Catálogo (Visible para todos)
    st.title("👞 Catálogo")
    # (Aquí mantienes tu lógica de grilla)
