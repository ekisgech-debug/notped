import streamlit as st
from supabase import create_client, Client
import os
import uuid
import random
import string
import requests
import time
import pandas as pd
import io
from openpyxl.worksheet.datavalidation import DataValidation

# Configuración de página
st.set_page_config(page_title="NotPed - B2B", page_icon="👞", layout="wide")

st.markdown("""
    <style>
        [data-testid="stFileUploader"] small {display: none !important;}
        [data-testid="stFileUploaderDropzoneInstructions"] > div > span {display: none !important;}
    </style>
""", unsafe_allow_html=True)

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
if "form_key" not in st.session_state: st.session_state.form_key = 0 
if "seccion_publica" not in st.session_state: st.session_state.seccion_publica = "inicio"
if "panel_privado" not in st.session_state: st.session_state.panel_privado = "carga"
if "remember_email" not in st.session_state: st.session_state.remember_email = ""

fk = st.session_state.form_key 

# Anti-F5
if st.session_state.usuario_actual is None and "uid" in st.query_params:
    try:
        res = supabase.table("usuarios").select("*").eq("id", st.query_params["uid"]).execute()
        if res.data:
            st.session_state.usuario_actual = res.data[0]["email"]
            st.session_state.rol_actual = res.data[0]["rol"]
            st.session_state.marca_actual = res.data[0]["nombre_marca"]
    except: pass

def generar_lista_talles(tipo, d, h):
    if "Sin Curva" in tipo: return []
    elif "Numérica Simple" in tipo:
        return [str(i) for i in range(1, 121)]
    elif "Doble Par" in tipo:
        return [f"{i}/{i+1}" for i in range(12, 54, 2)]
    elif "Doble Impar" in tipo:
        return [f"{i}/{i+1}" for i in range(13, 55, 2)]
    elif "Alfabética" in tipo:
        return ["XXXS", "XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL"]
    return []

# ========================================================
# FLUX 1: ENTORNO PÚBLICO
# ========================================================
if st.session_state.usuario_actual is None:
    st.query_params.clear()
    
    col_logo, col_nav = st.columns([2, 3])
    with col_logo: st.markdown("<h2 style='margin:0;'>👞 NotPed <span style='font-size:14px; color:gray;'>B2B Calzado</span></h2>", unsafe_allow_html=True)
    with col_nav:
        sub_col1, sub_col2, sub_col3 = st.columns(3)
        with sub_col1:
            if st.button("🏠 Inicio", use_container_width=True): st.session_state.seccion_publica = "inicio"; st.rerun()
        with sub_col2:
            if st.button("🔐 Iniciar Sesión", use_container_width=True): st.session_state.seccion_publica = "login"; st.rerun()
        with sub_col3:
            if st.button("📝 Registrarse", use_container_width=True): st.session_state.seccion_publica = "registro"; st.rerun()
    st.write("---")

    if st.session_state.seccion_publica == "login":
        col_login = st.columns([1, 2, 1])[1]
        with col_login:
            with st.form("login_form"):
                st.subheader("Ingresar")
                u_email = st.text_input("Correo", value=st.session_state.remember_email)
                pwd = st.text_input("Contraseña", type="password")
                recordar = st.checkbox("Recordar mi correo", value=True if st.session_state.remember_email else False)
                if st.form_submit_button("Ingresar"):
                    res = supabase.table("usuarios").select("*").eq("email", u_email.lower().strip()).eq("contrasena", pwd).execute()
                    if res.data:
                        st.session_state.usuario_actual = res.data[0]["email"]
                        st.session_state.remember_email = u_email if recordar else ""
                        st.session_state.rol_actual = res.data[0]["rol"]
                        st.session_state.marca_actual = res.data[0]["nombre_marca"]
                        st.query_params["uid"] = str(res.data[0]["id"])
                        st.rerun()
                    else: st.error("❌ Datos incorrectos.")

    elif st.session_state.seccion_publica == "inicio":
        st.title("🚀 Conectamos Fábricas de Calzado con Revendedores")
    elif st.session_state.seccion_publica == "registro":
        st.subheader("Crear Cuenta")
        # ... (código registro igual anterior)

# ========================================================
# FLUX 2: ENTORNO PRIVADO
# ========================================================
else:
    # Sidebar igual anterior...
    # Lógica de Excel con Validación mejorada
    if st.session_state.panel_privado == "carga" and "tipo_carga" in locals(): # (Simplicidad para visualización)
        # ... (resto de lógica de carga)
        pass
