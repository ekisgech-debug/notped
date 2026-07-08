import streamlit as st
from supabase import create_client, Client
import os
import uuid
import random
import string
import requests

# Configuración básica de la página
st.set_page_config(page_title="NotPed - B2B", page_icon="👞", layout="wide")

@st.cache_resource
def init_connection():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase: Client = init_connection()

# --- ESTADO DE SESIÓN PERSISTENTE ---
if "usuario_actual" not in st.session_state: st.session_state.usuario_actual = None
if "rol_actual" not in st.session_state: st.session_state.rol_actual = None
if "seccion_publica" not in st.session_state: st.session_state.seccion_publica = "Inicio"

# --- FUNCIÓN DE EMAIL (PUENTE GOOGLE APPS SCRIPT) ---
def enviar_correo_recuperacion(destinatario, nueva_clave):
    url_google_script = "https://script.google.com/macros/s/AKfycbxrQT5YiENHleJRr8d5ORF6VnUumzLsLvzKJYpl2vSSOl0D2eh65_D99nExatQCnR6DCg/exec" 
    payload = {"destinatario": destinatario, "clave": nueva_clave}
    try:
        respuesta = requests.post(url_google_script, json=payload, timeout=10)
        if respuesta.status_code == 200 and respuesta.json().get("estado") == "ok":
            return True, "OK"
        return False, "Error en el script de Google"
    except Exception as e:
        return False, str(e)


# ========================================================
# FLUX 1: ENTORNO PÚBLICO (PORTADA + LOGIN / REGISTRO)
# ========================================================
if st.session_state.usuario_actual is None:
    
    # --- MENÚ SUPERIOR DE NAVEGACIÓN PÚBLICA ---
    col_logo, col_nav = st.columns([2, 3])
    with col_logo:
        st.markdown("<h2 style='margin:0;'>👞 NotPed <span style='font-size:14px; color:gray;'>B2B Calzado</span></h2>", unsafe_allow_html=True)
    with col_nav:
        # Simulamos una barra de navegación con botones alineados a la derecha
        sub_col1, sub_col2, sub_col3 = st.columns(3)
        with sub_col1:
            if st.button("🏠 Inicio / Portada", use_container_width=True):
                st.session_state.seccion_publica = "Inicio"
                st.rerun()
        with sub_col2:
            if st.button("🔐 Iniciar Sesión", use_container_width=True):
                st.session_state.seccion_publica = "Login"
                st.rerun()
        with sub_col3:
            if st.button("📝 Registrar mi Negocio", use_container_width=True):
                st.session_state.seccion_publica = "Registro"
                st.rerun()
    st.write("---")

    # --- VISTA: PORTADA PRINCIPAL CON BANNERS ---
    if st.session_state.seccion_publica == "Inicio":
        st.title("🚀 Conectamos Fábricas de Calzado con Revendedores de todo el País")
        st.subheader("La plataforma mayorista más rápida y eficiente.")
        
        st.write("")
        st.markdown("### 📢 Espacios Publicitarios Destacados")
        
        # Grid de Banners Publicitarios (Puedes reemplazar los contenedores por st.image cuando tengas los diseños)
        col_banner1, col_banner2 = st.columns(2)
        
        with col_banner1:
            st.markdown(
                """
                <div style='background-color: #f0f2f6; padding: 40px; border-radius: 10px; border-left: 8px solid #000; text-align: center;'>
                    <h4>🏭 FÁBRICA DESTACADA A</h4>
                    <p>Nueva Colección Primavera-Verano. Lanzamientos exclusivos y curvas completas.</p>
                    <small style='color: gray;'>Espacio publicitario disponible</small>
                </div>
                """, 
                unsafe_allow_html=True
            )
            if st.button("Explorar Fábrica A", key="btn_pub_a"):
                st.session_state.seccion_publica = "Login"
                st.rerun()

        with col_banner2:
            st.markdown(
                """
                <div style='background-color: #f0f2f6; padding: 40px; border-radius: 10px; border-left: 8px solid #28a745; text-align: center;'>
                    <h4>🏭 FÁBRICA DESTACADA B</h4>
                    <p>Especialistas en Línea Urbana y Deportiva. Envíos inmediatos a todo el país.</p>
                    <small style='color: gray;'>Espacio publicitario disponible</small>
                </div>
                """, 
                unsafe_allow_html=True
            )
            if st.button("Explorar Fábrica B", key="btn_pub_b"):
                st.session_state.seccion_publica = "Login"
                st.rerun()
                
        st.write("")
        st.write("---")
        st.markdown(
            """
            <div style='text-align: center; color: gray; padding: 20px;'>
                ¿Eres fabricante y quieres anunciar aquí? Contáctanos a <b>info_notped@gmail.com</b>
            </div>
            """, 
            unsafe_allow_html=True
        )

    # --- VISTA: LOGIN NORMAL ---
    elif st.session_state.seccion_publica == "Login":
        st.markdown("<h3 style='text-align: center;'>Ingresar a la Plataforma</h3>", unsafe_allow_html=True)
        col_login_center = st.columns([1, 2, 1])[1]
        with col_login_center:
            with st.form("login_form"):
                usr_email = st.text_input("Correo Electrónico").strip().lower()
                pwd = st.text_input("Contraseña", type="password")
                submit = st.form_submit_button("Ingresar")
                
                if submit:
                    res = supabase.table("usuarios").select("*").eq("email", usr_email).eq("contrasena", pwd).execute()
                    if res.data:
                        datos = res.data[0]
                        st.session_state.usuario_actual = datos["email"]
                        st.session_state.rol_actual = datos["rol"]
                        st.rerun()
                    else:
                        st.error("❌ Correo o contraseña incorrectos.")
            
            if st.button("¿Olvidaste tu contraseña?"):
                st.session_state.seccion_publica = "Recuperar"
                st.rerun()

    # --- VISTA: REGISTRO ---
    elif st.session_state.seccion_publica == "Registro":
        st.markdown("<h3 style='text-align: center;'>Crea tu Cuenta Mayorista</h3>", unsafe_allow_html=True)
        col_reg_center = st.columns([1, 2, 1])[1]
        with col_reg_center:
            with st.form("registro_form"):
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
                                    supabase.table("usuarios").insert({
                                        "email": new_email, "contrasena": new_pwd, 
                                        "rol": rol_asignado, "nombre_marca": new_marca 
                                    }).execute()
                                    st.success("✅ Cuenta creada con éxito. Ya puedes iniciar sesión.")
                                    st.session_state.seccion_publica = "Login"
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Hubo un problema: {e}")
                    else:
                        st.warning("⚠️ Completa todos los campos.")

    # --- VISTA: RECUPERAR CLAVE ---
    elif st.session_state.seccion_publica == "Recuperar":
        col_rec_center = st.columns([1, 2, 1])[1]
        with col_rec_center:
            with st.form("recuperar_form"):
                st.subheader("Recuperar Contraseña")
                recup_email = st.text_input("Correo Electrónico").strip().lower()
                submit_recup = st.form_submit_button("Enviar nueva contraseña")
                
                if submit_recup:
                    if recup_email:
                        with st.spinner("Procesando..."):
                            consulta = supabase.table("usuarios").select("id").execute()
                            clave_temporal = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(6))
                            exito, msj_error = enviar_correo_recuperacion(recup_email, clave_temporal)
                            if exito:
                                supabase.table("usuarios").update({"contrasena": clave_temporal}).eq("email", recup_email).execute()
                                st.success("✅ Te hemos enviado un correo con tu nueva contraseña temporal.")
                            else:
                                st.error(f"❌ Error en el envío: {msj_error}")


# ========================================================
# FLUX 2: ENTORNO PRIVADO (USUARIO AUTENTICADO)
# ========================================================
else:
    # --- BARRA LATERAL PRIVADA ---
    with st.sidebar:
        st.markdown(f"### 👤 Conectado")
        st.write(f"**Email:** {st.session_state.usuario_actual}")
        
        # Etiquetas visuales claras por rol
        if st.session_state.rol_actual == "super_admin":
            st.info("👑 Súper Administrador")
        elif st.session_state.rol_actual == "proveedor":
            st.success("🏭 Panel Fábrica")
        else:
            st.warning("🛒 Panel Revendedor")
            
        st.write("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # --- ENRUTAMIENTO DE PANELES PRIVADOS ---
    
    # 1. TU TABLERO ÚNICO DE CONTROL (SUPER ADMIN)
    if st.session_state.rol_actual == "super_admin":
        st.title("⚙️ Tablero Maestro - NotPed Global")
        st.subheader("Control absoluto del ecosistema")
        
        # Aquí colocaremos el control de accesos, reset de claves maestro y la gestión de anuncios
        st.info("Estructura base lista. Aquí verás la lista de usuarios, estados de cuenta y métricas del sistema.")

    # 2. PANEL INDEPENDIENTE PARA LAS FÁBRICAS
    elif st.session_state.rol_actual == "proveedor":
        st.title("🏭 Centro de Control de Fábrica")
        st.subheader("Gestiona tus productos y recibe pedidos de revendedores")
        st.info("Estructura base lista. Aquí la fábrica podrá subir artículos, curvas de talles y procesar sus ventas.")

    # 3. PANEL INDEPENDIENTE PARA LOS REVENDEDORES
    elif st.session_state.rol_actual == "revendedor":
        st.title("🛒 Plataforma Mayorista de Compras")
        st.subheader("Explora catálogos y arma tus notas de pedido")
        st.info("Estructura base lista. Aquí el cliente final podrá ver los productos de las marcas y cargar su carrito.")
