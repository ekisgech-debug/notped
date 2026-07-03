import streamlit as st
from supabase import create_client, Client
import os
import uuid
import random
import string
import urllib.parse

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
if "modo_registro" not in st.session_state: st.session_state.modo_registro = False
if "modo_recuperar" not in st.session_state: st.session_state.modo_recuperar = False

# --- PANTALLA DE INGRESO / REGISTRO / RECUPERACIÓN ---
if st.session_state.usuario_actual is None:
    st.title("Bienvenido a NotPed")
    
    if st.session_state.modo_recuperar:
        with st.form("recuperar_form"):
            st.subheader("Solicitud de Recuperación")
            recup_usr = st.text_input("Usuario / Marca").strip()
            recup_tel = st.text_input("Celular registrado").strip()
            if st.form_submit_button("Enviar solicitud a NotPed"):
                if recup_usr and recup_tel:
                    consulta = supabase.table("usuarios").select("id").eq("usuario", recup_usr).eq("telefono", recup_tel).execute()
                    if consulta.data:
                        pin = ''.join(random.choice(string.digits) for i in range(4))
                        clave = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(6))
                        supabase.table("solicitudes_recuperacion").insert({
                            "usuario": recup_usr, "telefono": recup_tel, 
                            "codigo_seguridad": pin, "clave_propuesta": clave
                        }).execute()
                        st.success("✅ Solicitud enviada. NotPed la procesará en breve.")
                    else:
                        st.error("Datos incorrectos.")
        if st.button("Volver"): st.session_state.modo_recuperar = False; st.rerun()

    elif st.session_state.modo_registro:
        with st.form("registro"):
            tipo = st.selectbox("Rol", ["Revendedor", "Fábrica"])
            usr = st.text_input("Usuario/Nombre Marca").strip()
            tel = st.text_input("Celular").strip()
            pwd = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Registrarse"):
                rol = "proveedor" if tipo == "Fábrica" else "revendedor"
                supabase.table("usuarios").insert({"usuario": usr, "telefono": tel, "contrasena": pwd, "rol": rol, "nombre_marca": usr}).execute()
                st.success("Cuenta creada. Inicia sesión.")
                st.session_state.modo_registro = False; st.rerun()
        if st.button("Volver"): st.session_state.modo_registro = False; st.rerun()

    else:
        with st.form("login"):
            u = st.text_input("Usuario").strip()
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar"):
                res = supabase.table("usuarios").select("*").eq("usuario", u).eq("contrasena", p).execute()
                if res.data:
                    d = res.data[0]
                    st.session_state.usuario_actual = d["usuario"]
                    st.session_state.rol_actual = d["rol"]
                    st.rerun()
        if st.button("¿No tienes cuenta?"): st.session_state.modo_registro = True; st.rerun()
        if st.button("¿Olvidaste clave?"): st.session_state.modo_recuperar = True; st.rerun()

else:
    # --- MENÚ SIDEBAR ---
    with st.sidebar:
        st.write(f"Usuario: {st.session_state.usuario_actual}")
        if st.button("Cerrar Sesión"):
            st.session_state.clear()
            st.rerun()

    # --- LÓGICA DE ROLES ---
    if st.session_state.rol_actual == "super_admin":
        st.title("⚙️ Tablero Maestro")
        st.subheader("Tickets de Recuperación")
        solics = supabase.table("solicitudes_recuperacion").select("*").eq("estado", "pendiente").execute()
        for s in solics.data:
            with st.container(border=True):
                st.write(f"**{s['usuario']}** | Tel: {s['telefono']} | Cod: **{s['codigo_seguridad']}** | Propuesta: {s['clave_propuesta']}")
                if st.button(f"Aprobar {s['usuario']}", key=s['id']):
                    supabase.table("usuarios").update({"contrasena": s['clave_propuesta']}).eq("usuario", s['usuario']).execute()
                    supabase.table("solicitudes_recuperacion").update({"estado": "aprobado"}).eq("id", s['id']).execute()
                    st.rerun()

    elif st.session_state.rol_actual == "proveedor":
        st.title("📦 Mi Fábrica")
        # [Carga de productos igual al anterior...]
    
    elif st.session_state.rol_actual == "revendedor":
        st.title("👞 Catálogo")
        # [Selector de fábrica y productos...]
