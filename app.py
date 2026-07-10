import streamlit as st
from supabase import create_client, Client
import os
import uuid
import random
import string
import requests
import time

# Configuración de página
st.set_page_config(page_title="NotPed - B2B", page_icon="👞", layout="wide")

@st.cache_resource
def init_connection():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase: Client = init_connection()

# --- ESTADO DE SESIÓN Y LLAVES DE RESETEO ---
if "usuario_actual" not in st.session_state: st.session_state.usuario_actual = None
if "rol_actual" not in st.session_state: st.session_state.rol_actual = None
if "marca_actual" not in st.session_state: st.session_state.marca_actual = None
if "form_key" not in st.session_state: st.session_state.form_key = 0 # Llave maestra para limpiar el formulario

fk = st.session_state.form_key # Atajo para las llaves de los widgets

def enviar_correo_recuperacion(destinatario, nueva_clave):
    url_google_script = "https://script.google.com/macros/s/AKfycbxrQT5YiENHleJRr8d5ORF6VnUumzLsLvzKJYpl2vSSOl0D2eh65_D99nExatQCnR6DCg/exec" 
    payload = {"destinatario": destinatario, "clave": nueva_clave}
    try:
        respuesta = requests.post(url_google_script, json=payload, timeout=10)
        if respuesta.status_code == 200 and respuesta.json().get("estado") == "ok": return True, "OK"
        return False, "Error en el script de Google"
    except Exception as e: return False, str(e)


# ========================================================
# FLUX 1: ENTORNO PÚBLICO (Manejo con Flecha Atrás)
# ========================================================
if st.session_state.usuario_actual is None:
    # Leemos la URL para saber dónde estamos (permite usar la flecha atrás del navegador)
    ruta_publica = st.query_params.get("sec", "inicio")
    
    col_logo, col_nav = st.columns([2, 3])
    with col_logo: st.markdown("<h2 style='margin:0;'>👞 NotPed <span style='font-size:14px; color:gray;'>B2B Calzado</span></h2>", unsafe_allow_html=True)
    with col_nav:
        sub_col1, sub_col2, sub_col3 = st.columns(3)
        with sub_col1:
            if st.button("🏠 Inicio", use_container_width=True): st.query_params["sec"] = "inicio"; st.rerun()
        with sub_col2:
            if st.button("🔐 Iniciar Sesión", use_container_width=True): st.query_params["sec"] = "login"; st.rerun()
        with sub_col3:
            if st.button("📝 Registrarse", use_container_width=True): st.query_params["sec"] = "registro"; st.rerun()
    st.write("---")

    if ruta_publica == "inicio":
        st.title("🚀 Conectamos Fábricas de Calzado con Revendedores")
        st.write("")
        col_b1, col_b2 = st.columns(2)
        with col_b1: st.info("🏭 **FÁBRICA DESTACADA A**\n\nNueva Colección Primavera-Verano. Lanzamientos exclusivos.")
        with col_b2: st.success("🏭 **FÁBRICA DESTACADA B**\n\nEspecialistas en Línea Urbana y Deportiva. Envíos inmediatos.")

    elif ruta_publica == "login":
        col_login = st.columns([1, 2, 1])[1]
        with col_login:
            with st.form("login"):
                st.subheader("Ingresar")
                u_email = st.text_input("Correo").strip().lower()
                pwd = st.text_input("Contraseña", type="password").strip()
                if st.form_submit_button("Ingresar"):
                    res = supabase.table("usuarios").select("*").eq("email", u_email).eq("contrasena", pwd).execute()
                    if res.data:
                        st.session_state.usuario_actual = res.data[0]["email"]
                        st.session_state.rol_actual = res.data[0]["rol"]
                        st.session_state.marca_actual = res.data[0]["nombre_marca"]
                        # Al loguearse, reseteamos la URL y entramos al panel
                        st.query_params["panel"] = "carga"
                        st.rerun()
                    else: st.error("❌ Datos incorrectos.")
            if st.button("¿Olvidaste tu contraseña?"): st.query_params["sec"] = "recuperar"; st.rerun()

    elif ruta_publica == "registro":
        col_reg = st.columns([1, 2, 1])[1]
        with col_reg:
            with st.form("reg"):
                st.subheader("Crear Cuenta")
                tipo = st.selectbox("Tipo", ["Revendedor", "Fábrica"])
                marca = st.text_input("Marca").strip()
                email = st.text_input("Correo").strip().lower()
                p1 = st.text_input("Clave", type="password")
                p2 = st.text_input("Confirmar", type="password")
                if st.form_submit_button("Registrarse"):
                    if p1 == p2 and marca and email:
                        rol = "proveedor" if tipo == "Fábrica" else "revendedor"
                        chequeo = supabase.table("usuarios").select("id").eq("email", email).execute()
                        if not chequeo.data:
                            supabase.table("usuarios").insert({"email": email, "contrasena": p1, "rol": rol, "nombre_marca": marca}).execute()
                            st.success("✅ Cuenta creada. Redirigiendo al inicio de sesión...")
                            time.sleep(1.5)
                            st.query_params["sec"] = "login"
                            st.rerun()
                        else: st.error("❌ Correo ya registrado.")
                    else: st.warning("Revisa los datos.")

    elif ruta_publica == "recuperar":
        col_rec = st.columns([1, 2, 1])[1]
        with col_rec:
            with st.form("recup"):
                st.subheader("Recuperar Clave")
                email_recup = st.text_input("Correo").strip().lower()
                if st.form_submit_button("Enviar"):
                    res = supabase.table("usuarios").select("id").eq("email", email_recup).execute()
                    if res.data:
                        tmp = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
                        exito, _ = enviar_correo_recuperacion(email_recup, tmp)
                        if exito:
                            supabase.table("usuarios").update({"contrasena": tmp}).eq("email", email_recup).execute()
                            st.success("✅ Correo enviado.")
                        else: st.error("Error al enviar.")
                    else: st.error("No existe la cuenta.")

# ========================================================
# FLUX 2: ENTORNO PRIVADO
# ========================================================
else:
    # Leemos la URL para la navegación privada (permite usar la flecha atrás del navegador)
    ruta_privada = st.query_params.get("panel", "carga")

    with st.sidebar:
        st.markdown(f"### {st.session_state.marca_actual}")
        st.write(f"*{st.session_state.usuario_actual}*")
        
        if st.session_state.rol_actual == "proveedor":
            st.success("🏭 Panel Fábrica")
            st.write("---")
            if st.button("➕ Cargar Calzado", use_container_width=True): st.query_params["panel"] = "carga"; st.rerun()
            if st.button("👞 Mi Catálogo", use_container_width=True): st.query_params["panel"] = "catalogo"; st.rerun()
            if st.button("👥 Mis Revendedores", use_container_width=True): st.query_params["panel"] = "clientes"; st.rerun()
        
        elif st.session_state.rol_actual == "revendedor": st.warning("🛒 Panel Revendedor")
        else: st.info("👑 Admin")
            
        st.write("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.query_params["sec"] = "inicio"
            st.rerun()

    # ----------------------------------------------------
    # MOTOR 1: PANEL FÁBRICA
    # ----------------------------------------------------
    if st.session_state.rol_actual == "proveedor":
        res_conf = supabase.table("configuraciones_fabrica").select("*").eq("proveedor", st.session_state.usuario_actual).execute()
        mis_configs = res_conf.data if res_conf.data else []
        mis_categorias = [c for c in mis_configs if c['tipo'] == 'categoria']
        mis_colores = [c for c in mis_configs if c['tipo'] == 'color']
        mis_curvas = [c for c in mis_configs if c['tipo'] == 'curva']

        st.title(f"🏭 Panel Fábrica | {st.session_state.marca_actual}")
        
        # PESTAÑA 1: CARGA DE CALZADO
        if ruta_privada == "carga":
            with st.expander("⚙️ Administrar mis Listas (Eliminar categorías, colores o curvas)"):
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.markdown("**Categorías**")
                    for c in mis_categorias:
                        if st.button(f"❌ {c['nombre']}", key=f"del_cat_{c['id']}"):
                            supabase.table("configuraciones_fabrica").delete().eq("id", c['id']).execute(); st.rerun()
                with col_m2:
                    st.markdown("**Colores**")
                    for c in mis_colores:
                        if st.button(f"❌ {c['nombre']}", key=f"del_col_{c['id']}"):
                            supabase.table("configuraciones_fabrica").delete().eq("id", c['id']).execute(); st.rerun()
                with col_m3:
                    st.markdown("**Curvas**")
                    for c in mis_curvas:
                        if st.button(f"❌ {c['nombre']}", key=f"del_curv_{c['id']}"):
                            supabase.table("configuraciones_fabrica").delete().eq("id", c['id']).execute(); st.rerun()

            st.write("---")
            st.subheader("Nuevo Producto")
            
            # --- COMBOS INTELIGENTES (Condicionales para mantener 1 sola caja visualmente) ---
            c_cat, c_col = st.columns(2)
            with c_cat:
                opcion_cat = st.selectbox("Categoría", ["➕ Crear Nueva..."] + [c['nombre'] for c in mis_categorias], key=f"sel_cat_{fk}")
                if opcion_cat == "➕ Crear Nueva...":
                    cat_final = st.text_input("✍️ Escribe el nombre de la Categoría y presiona Enter", key=f"txt_cat_{fk}")
                else: cat_final = opcion_cat

            with c_col:
                opcion_col = st.selectbox("Color", ["➕ Crear Nuevo..."] + [c['nombre'] for c in mis_colores], key=f"sel_col_{fk}")
                if opcion_col == "➕ Crear Nuevo...":
                    col_final = st.text_input("✍️ Escribe el nombre del Color y presiona Enter", key=f"txt_col_{fk}")
                else: col_final = opcion_col

            art = st.text_input("Artículo (Ej: Bota 401)", key=f"txt_art_{fk}")
            desc = st.text_input("Descripción detallada", key=f"txt_desc_{fk}")
            
            st.write("---")
            st.markdown("**📏 Configuración de Curva de Talles**")
            
            # Lógica Combinada de Curva
            curva_elegida = st.selectbox("Selecciona una Curva Guardada o crea una nueva", ["➕ Armar Nueva Curva..."] + [c['nombre'] for c in mis_curvas], key=f"sel_curv_{fk}")
            
            t_d_def, t_h_def, cantidades_def = 35, 40, []
            if curva_elegida != "➕ Armar Nueva Curva...":
                obj = next((c for c in mis_curvas if c['nombre'] == curva_elegida), None)
                if obj:
                    partes = obj['valor'].split('|')
                    t_d_def, t_h_def = int(partes[0]), int(partes[1])
                    cantidades_def = partes[2].split('-')

            col_d, col_h = st.columns(2)
            with col_d: t_desde = st.number_input("Talle Desde", min_value=15, max_value=50, value=t_d_def, key=f"num_td_{fk}")
            with col_h: t_hasta = st.number_input("Talle Hasta", min_value=15, max_value=50, value=t_h_def, key=f"num_th_{fk}")
            
            if t_hasta >= t_desde:
                talles_list = list(range(t_desde, t_hasta + 1))
                cols_talles = st.columns(len(talles_list))
                valores_curva, total_pares = [], 0
                
                for i, talle in enumerate(talles_list):
                    val_defecto = int(cantidades_def[i]) if len(cantidades_def) > i else 0
                    with cols_talles[i]:
                        val = st.number_input(f"T-{talle}", min_value=0, step=1, value=val_defecto, key=f"talle_{talle}_{fk}")
                        valores_curva.append(str(val))
                        total_pares += val
                
                st.markdown(f"<p style='text-align: right; color: #d32f2f; font-weight: bold; font-size:18px;'>Total pares por caja: {total_pares}</p>", unsafe_allow_html=True)
                curva_final_str = "-".join(valores_curva)
            else:
                st.error("El Talle Hasta debe ser mayor o igual al Talle Desde.")
                curva_final_str = ""

            if curva_elegida == "➕ Armar Nueva Curva...":
                nombre_nueva_curva = st.text_input("💾 Nombre para guardar esta curva y usarla la próxima vez (Ej: Urbana Mujer)", key=f"txt_ncurv_{fk}")
                guardar_curva = True
            else:
                nombre_nueva_curva = curva_elegida
                guardar_curva = False

            st.write("---")
            precio = st.number_input("Precio de Lista ($)", min_value=0.0, key=f"num_precio_{fk}")
            foto = st.file_uploader("Subir Foto del Calzado (Máx 250kb)", type=["jpg", "png", "jpeg"], key=f"file_foto_{fk}")
            
            # Sacamos el botón del st.form para poder limpiar la pantalla con el contador
            if st.button("Guardar Producto en Catálogo", type="primary", use_container_width=True):
                if foto and foto.size > 256000:
                    st.error("❌ La imagen es demasiado pesada. El límite es de 250kb.")
                elif not art or not foto or curva_final_str == "" or not cat_final or not col_final:
                    st.warning("⚠️ Faltan datos clave (Artículo, Foto, Categoría o Color).")
                else:
                    with st.spinner("Procesando y guardando..."):
                        try:
                            # 1. Guardar nueva categoría/color si son nuevos y no existen
                            if opcion_cat == "➕ Crear Nueva..." and cat_final:
                                supabase.table("configuraciones_fabrica").insert({"proveedor": st.session_state.usuario_actual, "tipo": "categoria", "nombre": cat_final}).execute()
                            if opcion_col == "➕ Crear Nuevo..." and col_final:
                                supabase.table("configuraciones_fabrica").insert({"proveedor": st.session_state.usuario_actual, "tipo": "color", "nombre": col_final}).execute()
                            if guardar_curva and nombre_nueva_curva:
                                valor_curva = f"{t_desde}|{t_hasta}|{curva_final_str}"
                                supabase.table("configuraciones_fabrica").insert({"proveedor": st.session_state.usuario_actual, "tipo": "curva", "nombre": nombre_nueva_curva, "valor": valor_curva}).execute()

                            # 2. Subir foto y guardar producto
                            extension = foto.name.split('.')[-1]
                            nombre_archivo = f"{uuid.uuid4()}.{extension}"
                            supabase.storage.from_("fotos_productos").upload(nombre_archivo, foto.getvalue(), {"content-type": foto.type})
                            foto_url = supabase.storage.from_("fotos_productos").get_public_url(nombre_archivo)
                            
                            nuevo_prod = {
                                "proveedor": st.session_state.usuario_actual,
                                "categoria": cat_final, "articulo": art, "color": col_final, 
                                "descripcion": desc, "precio": precio,
                                "talle_desde": t_desde, "talle_hasta": t_hasta,
                                "curva": curva_final_str, "foto_url": foto_url
                            }
                            supabase.table("productos").insert(nuevo_prod).execute()
                            
                            # Magia de Reseteo: Cambiamos la llave maestra y recargamos
                            st.session_state.form_key += 1
                            st.success("✅ ¡Producto cargado con éxito! Formulario listo para el siguiente.")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")

        # PESTAÑA 2: CATÁLOGO AGRUPADO
        elif ruta_privada == "catalogo":
            st.subheader("Artículos Publicados")
            res_prod = supabase.table("productos").select("*").eq("proveedor", st.session_state.usuario_actual).order("id", desc=True).execute()
            
            if res_prod.data:
                productos = res_prod.data
                categorias_presentes = sorted(list(set([p.get('categoria', 'General') for p in productos])))
                
                for cat_name in categorias_presentes:
                    st.markdown(f"### 📁 {cat_name}")
                    prods_cat = [p for p in productos if p.get('categoria', 'General') == cat_name]
                    
                    for p in prods_cat:
                        with st.container(border=True):
                            c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
                            with c1:
                                if p.get("foto_url"): st.image(p["foto_url"], use_container_width=True)
                            with c2:
                                st.markdown(f"**{p['articulo']}** | {p.get('color', '')}")
                                st.write(p.get("descripcion", ""))
                                st.markdown(f"<h4 style='color: #28a745;'>${p['precio']:,.0f}</h4>", unsafe_allow_html=True)
                            with c3:
                                st.write("**Curva de Talles:**")
                                st.code(f"Talles: {p['talle_desde']} a {p['talle_hasta']}\nCantidades: {p['curva']}")
                            with c4:
                                if st.button("🗑️ Borrar", key=f"del_prod_{p['id']}", type="primary"):
                                    supabase.table("productos").delete().eq("id", p['id']).execute()
                                    st.rerun()
                    st.write("---")
            else:
                st.info("Aún no tienes productos en tu catálogo.")

        # PESTAÑA 3: REVENDEDORES
        elif ruta_privada == "clientes":
            st.subheader("Mis Clientes Autorizados")
            st.info("Próximamente: Aquí verás las notas de pedido que te envíen los revendedores, y podrás asignarles bonificaciones.")

    # ----------------------------------------------------
    # MOTOR 2 y 3 (Pendientes)
    # ----------------------------------------------------
    elif st.session_state.rol_actual == "revendedor":
        st.title("🛒 Plataforma Mayorista")
        st.info("El motor del revendedor estará aquí.")

    elif st.session_state.rol_actual == "super_admin":
        st.title("⚙️ Tablero Maestro")
        st.info("Tu panel de control general.")
