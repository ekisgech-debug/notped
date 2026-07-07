import streamlit as st
from supabase import create_client, Client
import os
import smtplib
from email.mime.text import MIMEText
import random
import string
import uuid

# Configuración básica
st.set_page_config(page_title="NotPed - B2B", page_icon="👞", layout="wide")

@st.cache_resource
def init_connection():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase: Client = init_connection()

# --- FUNCIÓN DE CORREO BLINDADA ---
def enviar_correo_recuperacion(destinatario, nueva_clave):
    remitente = "info_notped@gmail.com"
    # IMPORTANTE: Esta debe ser la "Contraseña de Aplicación" de 16 letras de Google, configurada en Render.
    password = os.environ.get("EMAIL_PASS") 
    
    if not password:
        return False, "Falta configurar la variable EMAIL_PASS en Render."

    cuerpo = f"""Hola,

Se ha solicitado un reseteo de contraseña para tu cuenta en NotPed.
Tu nueva contraseña temporal es: {nueva_clave}

Por favor, ingresa a la plataforma con esta clave y cámbiala desde tu panel lateral lo antes posible.

Saludos,
El equipo de NotPed"""

    msg = MIMEText(cuerpo)
    msg['Subject'] = 'Recuperación de Contraseña - NotPed'
    msg['From'] = remitente
    msg['To'] = destinatario
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
        return True, "OK"
    except Exception as e:
        # Esto atrapará errores como el "[Errno 101] Network is unreachable" de Render
        return False, str(e)

# --- ESTADO DE SESIÓN (Persistente para F5) ---
if "email_actual" not in st.session_state: st.session_state.email_actual = None
if "rol_actual" not in st.session_state: st.session_state.rol_actual = None
if "marca_actual" not in st.session_state: st.session_state.marca_actual = None
if "modo_registro" not in st.session_state: st.session_state.modo_registro = False
if "modo_recuperar" not in st.session_state: st.session_state.modo_recuperar = False

# --- PANTALLA DE INGRESO / REGISTRO / RECUPERACIÓN ---
if st.session_state.email_actual is None:
    st.title("Bienvenido a NotPed")
    
    # 1. VISTA: RECUPERAR CLAVE (POR EMAIL)
    if st.session_state.modo_recuperar:
        with st.form("recuperar_form"):
            st.subheader("Recuperar Contraseña")
            st.write("Ingresa tu correo y te enviaremos una clave temporal.")
            
            recup_email = st.text_input("Correo Electrónico").strip().lower()
            submit_recup = st.form_submit_button("Enviar nueva contraseña")
            
            if submit_recup:
                if recup_email:
                    with st.spinner("Buscando cuenta y enviando correo..."):
                        consulta = supabase.table("usuarios").select("id").eq("email", recup_email).execute()
                        
                        if consulta.data:
                            clave_temporal = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(6))
                            
                            # Intentamos enviar el correo PRIMERO, antes de cambiar la clave en la BD
                            exito, msj_error = enviar_correo_recuperacion(recup_email, clave_temporal)
                            
                            if exito:
                                supabase.table("usuarios").update({"contrasena": clave_temporal}).eq("email", recup_email).execute()
                                st.success("✅ Te hemos enviado un correo con tu nueva contraseña temporal.")
                            else:
                                st.error(f"❌ Falló el envío del correo. Error técnico del servidor: {msj_error}")
                        else:
                            st.error("❌ No encontramos ninguna cuenta con ese correo electrónico.")
                else:
                    st.warning("⚠️ Ingresa un correo electrónico.")
            
        if st.button("Volver al Inicio"):
            st.session_state.modo_recuperar = False
            st.rerun()
                
    # 2. VISTA: REGISTRARSE (CON EMAIL)
    elif st.session_state.modo_registro:
        with st.form("registro_form"):
            st.subheader("Crear Cuenta Nueva")
            
            tipo_cuenta = st.selectbox("¿Qué tipo de cuenta necesitas?", ["Revendedor (Quiero comprar)", "Fábrica/Proveedor (Quiero vender)"])
            new_marca = st.text_input("Nombre de tu Negocio / Marca").strip()
            new_email = st.text_input("Correo Electrónico").strip().lower()
            new_pwd = st.text_input("Contraseña", type="password")
            new_pwd_confirm = st.text_input("Confirmar Contraseña", type="password")
            
            submit_reg = st.form_submit_button("Registrarse")
            
            if submit_reg:
                if new_marca and new_email and new_pwd and new_pwd_confirm:
                    if new_pwd != new_pwd_confirm:
                        st.error("❌ Las contraseñas no coinciden.")
                    else:
                        rol_asignado = "proveedor" if "Fábrica" in tipo_cuenta else "revendedor"
                        try:
                            chequeo = supabase.table("usuarios").select("id").eq("email", new_email).execute()
                            if chequeo.data:
                                st.error("❌ Este correo ya está registrado.")
                            else:
                                nuevo_user = {
                                    "email": new_email,
                                    "contrasena": new_pwd, 
                                    "rol": rol_asignado, 
                                    "nombre_marca": new_marca 
                                }
                                supabase.table("usuarios").insert(nuevo_user).execute()
                                st.success("✅ Cuenta creada con éxito. Ya puedes iniciar sesión.")
                                st.session_state.modo_registro = False
                                st.rerun()
                        except Exception as e:
                            st.error(f"Hubo un problema: {e}")
                else:
                    st.warning("⚠️ Completa todos los campos.")
        
        if st.button("Volver al Login"):
            st.session_state.modo_registro = False
            st.rerun()
            
    # 3. VISTA: LOGIN NORMAL (CON EMAIL)
    else:
        with st.form("login_form"):
            st.subheader("Iniciar Sesión")
            usr_email = st.text_input("Correo Electrónico").strip().lower()
            pwd = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Ingresar")
            
            if submit:
                res = supabase.table("usuarios").select("*").eq("email", usr_email).eq("contrasena", pwd).execute()
                if res.data:
                    datos = res.data[0]
                    st.session_state.email_actual = datos["email"]
                    st.session_state.rol_actual = datos["rol"]
                    st.session_state.marca_actual = datos["nombre_marca"]
                    st.rerun()
                else:
                    st.error("❌ Correo o contraseña incorrectos.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("¿No tienes cuenta? Regístrate"):
                st.session_state.modo_registro = True
                st.rerun()
        with col2:
            if st.button("¿Olvidaste tu contraseña?"):
                st.session_state.modo_recuperar = True
                st.rerun()

# --- SISTEMA PRINCIPAL (USUARIO CONECTADO) ---
else:
    with st.sidebar:
        st.markdown(f"### {st.session_state.marca_actual}")
        st.write(f"*{st.session_state.email_actual}*")
        
        if st.session_state.rol_actual == "super_admin":
            st.info("👑 Súper Administrador")
        elif st.session_state.rol_actual == "proveedor":
            st.success("🏭 Fábrica / Proveedor")
        else:
            st.warning("🛒 Revendedor")
        
        st.write("---")
        with st.expander("🔐 Cambiar mi Contraseña"):
            with st.form("form_cambio_clave", clear_on_submit=True):
                clave_actual = st.text_input("Contraseña Actual", type="password")
                clave_nueva = st.text_input("Nueva Contraseña", type="password")
                clave_confirmar = st.text_input("Confirmar Nueva", type="password")
                if st.form_submit_button("Actualizar"):
                    consulta = supabase.table("usuarios").select("contrasena").eq("email", st.session_state.email_actual).execute()
                    if consulta.data and consulta.data[0]["contrasena"] == clave_actual:
                        if clave_nueva == clave_confirmar:
                            supabase.table("usuarios").update({"contrasena": clave_nueva}).eq("email", st.session_state.email_actual).execute()
                            st.success("✅ Contraseña actualizada.")
                        else:
                            st.error("❌ Las nuevas contraseñas no coinciden.")
                    else:
                        st.error("❌ La contraseña actual es incorrecta.")
        
        st.write("---")
        if st.button("Cerrar Sesión"):
            st.session_state.clear()
            st.rerun()
            

    # --- PANELES SEGÚN ROL ---
    if st.session_state.rol_actual == "super_admin":
        st.title("⚙️ Tablero Maestro - NotPed")
        st.write("Panel exclusivo de administración de la plataforma.")
        # Aquí irá tu panel de métricas y comparativos luego.

    elif st.session_state.rol_actual == "proveedor":
        st.title("📦 Mi Fábrica")
        # Tu formulario de carga de productos iría aquí
        st.info("Espacio para el catálogo de la fábrica.")

    elif st.session_state.rol_actual == "revendedor":
        st.title("👞 Plataforma Mayorista")
        # El selector de fábricas para armar las Notas de Pedido iría aquí
        st.info("Espacio para que el revendedor vea productos y haga pedidos.")
