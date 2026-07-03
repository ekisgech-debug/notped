import streamlit as st
from supabase import create_client, Client
import os
import uuid
import random
import string

# Configuración visual de la plataforma
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
if "modo_recuperar" not in st.session_state: st.session_state.modo_recuperar = False

# --- PANTALLA DE INGRESO / REGISTRO / RECUPERACIÓN ---
if st.session_state.usuario_actual is None:
    st.title("Bienvenido a NotPed")
    
    # VISTA: RECUPERAR CLAVE
    if st.session_state.modo_recuperar:
        with st.form("recuperar_form"):
            st.subheader("Recuperar Contraseña")
            st.write("Validaremos tu identidad cruzando tu usuario con tu número de celular registrado.")
            
            recup_usr = st.text_input("Usuario / Marca").strip()
            recup_tel = st.text_input("Celular (con el que te registraste)").strip()
            submit_recup = st.form_submit_button("Validar Identidad")
            
            if submit_recup:
                if recup_usr and recup_tel:
                    with st.spinner("Verificando datos..."):
                        # Cruzamos usuario y teléfono en la base de datos
                        consulta = supabase.table("usuarios").select("id").eq("usuario", recup_usr).eq("telefono", recup_tel).execute()
                        
                        if consulta.data:
                            pin_seguridad = ''.join(random.choice(string.digits) for i in range(4))
                            st.success("✅ Identidad verificada con éxito.")
                            st.info(f"🔒 **Paso Final:**\n\nDesde el celular que tienes registrado (**{recup_tel}**), envíanos un mensaje de WhatsApp con este código de seguridad: **{pin_seguridad}**.\n\nAl recibirlo, te asignaremos tu nueva contraseña.")
                        else:
                            st.error("❌ Los datos no coinciden. Revisa tu usuario y número de celular.")
                else:
                    st.warning("⚠️ Completa ambos campos.")
            
        if st.button("Volver al Inicio"):
            st.session_state.modo_recuperar = False
            st.rerun()
                
    # VISTA: REGISTRARSE
    elif st.session_state.modo_registro:
        with st.form("registro_form"):
            st.subheader("Crear Cuenta Nueva")
            st.info("💡 Tu nombre de usuario será también el nombre visible de tu negocio en el sistema.")
            
            tipo_cuenta = st.selectbox("¿Qué tipo de cuenta necesitas?", ["Revendedor (Quiero comprar)", "Fábrica/Proveedor (Quiero vender)"])
            new_usr = st.text_input("Usuario / Nombre de Marca (Ej: ZapateriaCentro)").strip()
            new_tel = st.text_input("Celular con WhatsApp (Ej: 261...)").strip()
            new_pwd = st.text_input("Contraseña", type="password")
            
            submit_reg = st.form_submit_button("Registrarse")
            
            if submit_reg:
                if new_usr and new_pwd and new_tel:
                    rol_asignado = "proveedor" if "Fábrica" in tipo_cuenta else "revendedor"
                    try:
                        chequeo = supabase.table("usuarios").select("id").eq("usuario", new_usr).execute()
                        if chequeo.data:
                            st.error("❌ Este nombre ya está en uso. Elige otro.")
                        else:
                            nuevo_user = {
                                "usuario": new_usr, 
                                "contrasena": new_pwd, 
                                "telefono": new_tel,
                                "rol": rol_asignado, 
                                "nombre_marca": new_usr 
                            }
                            supabase.table("usuarios").insert(nuevo_user).execute()
                            st.success("✅ Cuenta creada con éxito. Ya puedes iniciar sesión.")
                            st.session_state.modo_registro = False
                            st.rerun()
                    except Exception as e:
                        st.error("Hubo un problema al procesar el registro.")
                else:
                    st.warning("⚠️ Completa todos los campos.")
        
        if st.button("Volver al Login"):
            st.session_state.modo_registro = False
            st.rerun()
            
    # VISTA: LOGIN NORMAL
    else:
        with st.form("login_form"):
            st.subheader("Iniciar Sesión")
            usr = st.text_input("Usuario / Marca").strip()
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
        st.markdown(f"### {st.session_state.usuario_actual}")
        st.write(f"**Perfil:** {st.session_state.rol_actual.capitalize()}")
        
        st.write("---")
        with st.expander("🔐 Cambiar mi Contraseña"):
            with st.form("form_cambio_clave", clear_on_submit=True):
                clave_actual = st.text_input("Contraseña Actual", type="password")
                clave_nueva = st.text_input("Nueva Contraseña", type="password")
                clave_confirmar = st.text_input("Confirmar Nueva", type="password")
                if st.form_submit_button("Actualizar"):
                    consulta = supabase.table("usuarios").select("contrasena").eq("usuario", st.session_state.usuario_actual).execute()
                    if consulta.data and consulta.data[0]["contrasena"] == clave_actual:
                        if clave_nueva == clave_confirmar:
                            supabase.table("usuarios").update({"contrasena": clave_nueva}).eq("usuario", st.session_state.usuario_actual).execute()
                            st.success("✅ Contraseña actualizada.")
                        else:
                            st.error("❌ Las nuevas contraseñas no coinciden.")
                    else:
                        st.error("❌ La contraseña actual es incorrecta.")
        
        st.write("---")
        if st.button("Cerrar Sesión"):
            st.session_state.usuario_actual = None
            st.session_state.rol_actual = None
            st.session_state.marca_actual = None
            st.rerun()
            
    # PERFIL: PROVEEDOR (FÁBRICA)
    if st.session_state.rol_actual == "proveedor":
        st.title("📦 Panel de Control de Fábrica")
        
        with st.expander("👥 Gestión de Clientes (Resetear Claves)", expanded=False):
            st.write("Aquí puedes forzar el cambio de contraseña si un revendedor la olvidó.")
            try:
                # Ahora mostramos el nombre del usuario junto a su teléfono para mayor facilidad
                res_clientes = supabase.table("usuarios").select("usuario", "telefono").eq("rol", "revendedor").execute()
                if res_clientes.data:
                    lista_clientes = {f"{c['usuario']} (Tel: {c.get('telefono', 'Sin cargar')})": c['usuario'] for c in res_clientes.data}
                    
                    with st.form("form_reset_admin", clear_on_submit=True):
                        cliente_elegido = st.selectbox("Seleccionar Cliente", list(lista_clientes.keys()))
                        nueva_clave_admin = st.text_input("Asignar Nueva Contraseña", type="password")
                        if st.form_submit_button("Forzar Reseteo de Clave"):
                            if nueva_clave_admin:
                                usuario_a_modificar = lista_clientes[cliente_elegido]
                                supabase.table("usuarios").update({"contrasena": nueva_clave_admin}).eq("usuario", usuario_a_modificar).execute()
                                st.success(f"✅ Clave actualizada correctamente.")
                            else:
                                st.warning("⚠️ Debes escribir una nueva contraseña.")
                else:
                    st.info("Todavía no tienes revendedores registrados.")
            except Exception as e:
                st.error("Error al cargar la lista de clientes.")

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
                                supabase.storage.from_("fotos_productos").upload(nombre_archivo, foto.getvalue(), {"content-type": foto.type})
                                foto_url = supabase.storage.from_("fotos_productos").get_public_url(nombre_archivo)
                                
                                nuevo_producto = {"articulo": articulo, "categoria": categoria, "precio": precio, "curva": curva, "foto_url": foto_url}
                                supabase.table("productos").insert(nuevo_producto).execute()
                                st.success("✅ ¡Producto cargado con éxito!")
                            except Exception as e:
                                st.error(f"Error: {e}")

    # VISTA: CATÁLOGO PÚBLICO
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
