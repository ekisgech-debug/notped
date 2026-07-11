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

# ========================================================
# AUTO-RECUPERACIÓN DE SESIÓN (ANTI-F5)
# ========================================================
# Si el usuario no está en memoria pero hay un UID en la URL, lo reconectamos silenciosamente
if st.session_state.usuario_actual is None and "uid" in st.query_params:
    try:
        res = supabase.table("usuarios").select("*").eq("id", st.query_params["uid"]).execute()
        if res.data:
            st.session_state.usuario_actual = res.data[0]["email"]
            st.session_state.rol_actual = res.data[0]["rol"]
            st.session_state.marca_actual = res.data[0]["nombre_marca"]
            st.session_state.panel_privado = st.query_params.get("panel", "carga")
    except:
        pass

def enviar_correo_recuperacion(destinatario, nueva_clave):
    url_google_script = "https://script.google.com/macros/s/AKfycbxrQT5YiENHleJRr8d5ORF6VnUumzLsLvzKJYpl2vSSOl0D2eh65_D99nExatQCnR6DCg/exec" 
    payload = {"destinatario": destinatario, "clave": nueva_clave}
    try:
        respuesta = requests.post(url_google_script, json=payload, timeout=10)
        if respuesta.status_code == 200 and respuesta.json().get("estado") == "ok": return True, "OK"
        return False, "Error en el script de Google"
    except Exception as e: return False, str(e)

def generar_lista_talles(tipo, d, h):
    if "Sin Curva" in tipo: return []
    elif "Numérica Simple" in tipo:
        return [str(i) for i in range(int(d), int(h)+1)] if int(h) >= int(d) else []
    elif "Doble Par" in tipo:
        lista = [f"{i}/{i+1}" for i in range(12, 54, 2)]
        if d in lista and h in lista and lista.index(h) >= lista.index(d):
            return lista[lista.index(d) : lista.index(h)+1]
        return []
    elif "Doble Impar" in tipo:
        lista = [f"{i}/{i+1}" for i in range(13, 55, 2)]
        if d in lista and h in lista and lista.index(h) >= lista.index(d):
            return lista[lista.index(d) : lista.index(h)+1]
        return []
    elif "Alfabética" in tipo:
        lista = ["XXXS", "XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL"]
        if d in lista and h in lista and lista.index(h) >= lista.index(d):
            return lista[lista.index(d) : lista.index(h)+1]
        return []
    return []

# ========================================================
# FLUX 1: ENTORNO PÚBLICO
# ========================================================
if st.session_state.usuario_actual is None:
    st.query_params.clear() # Limpia la URL solo si estás fuera de sesión
    
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

    if st.session_state.seccion_publica == "inicio":
        st.title("🚀 Conectamos Fábricas de Calzado con Revendedores")
        st.write("")
        col_b1, col_b2 = st.columns(2)
        with col_b1: st.info("🏭 **FÁBRICA DESTACADA A**\n\nNueva Colección Primavera-Verano. Lanzamientos exclusivos.")
        with col_b2: st.success("🏭 **FÁBRICA DESTACADA B**\n\nEspecialistas en Línea Urbana y Deportiva. Envíos inmediatos.")

    elif st.session_state.seccion_publica == "login":
        col_login = st.columns([1, 2, 1])[1]
        with col_login:
            with st.form("login_form"):
                st.subheader("Ingresar")
                u_email = st.text_input("Correo", value=st.session_state.remember_email).strip().lower()
                pwd = st.text_input("Contraseña", type="password").strip()
                recordar = st.checkbox("Recordar mi correo", value=True if st.session_state.remember_email else False)
                
                if st.form_submit_button("Ingresar"):
                    res = supabase.table("usuarios").select("*").eq("email", u_email).eq("contrasena", pwd).execute()
                    if res.data:
                        st.session_state.usuario_actual = res.data[0]["email"]
                        st.session_state.rol_actual = res.data[0]["rol"]
                        st.session_state.marca_actual = res.data[0]["nombre_marca"]
                        st.session_state.panel_privado = "carga"
                        
                        if recordar: st.session_state.remember_email = u_email
                        else: st.session_state.remember_email = ""
                        
                        st.query_params["uid"] = str(res.data[0]["id"])
                        st.query_params["panel"] = "carga"
                        st.rerun()
                    else: st.error("❌ Datos incorrectos.")
            if st.button("¿Olvidaste tu contraseña?"): st.session_state.seccion_publica = "recuperar"; st.rerun()

    elif st.session_state.seccion_publica == "registro":
        col_reg = st.columns([1, 2, 1])[1]
        with col_reg:
            with st.form("reg_form"):
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
                            st.session_state.seccion_publica = "login"
                            st.rerun()
                        else: st.error("❌ Correo ya registrado.")
                    else: st.warning("Revisa los datos.")

    elif st.session_state.seccion_publica == "recuperar":
        col_rec = st.columns([1, 2, 1])[1]
        with col_rec:
            with st.form("recup_form"):
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
    with st.sidebar:
        st.markdown(f"### {st.session_state.marca_actual}")
        st.write(f"*{st.session_state.usuario_actual}*")
        
        if st.session_state.rol_actual == "proveedor":
            st.success("🏭 Panel Fábrica")
            st.write("---")
            if st.button("🏠 Portada Principal", use_container_width=True): 
                st.session_state.panel_privado = "portada"
                st.query_params["panel"] = "portada"
                st.rerun()
            if st.button("➕ Cargar Calzado", use_container_width=True): 
                st.session_state.panel_privado = "carga"
                st.query_params["panel"] = "carga"
                st.rerun()
            if st.button("👞 Mi Catálogo", use_container_width=True): 
                st.session_state.panel_privado = "catalogo"
                st.query_params["panel"] = "catalogo"
                st.rerun()
            if st.button("👥 Mis Revendedores", use_container_width=True): 
                st.session_state.panel_privado = "clientes"
                st.query_params["panel"] = "clientes"
                st.rerun()
        
        elif st.session_state.rol_actual == "revendedor": st.warning("🛒 Panel Revendedor")
        else: st.info("👑 Admin")
            
        st.write("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            rem_email = st.session_state.get("remember_email", "")
            st.session_state.clear()
            st.session_state.remember_email = rem_email
            st.query_params.clear()
            st.rerun()

    if st.session_state.rol_actual == "proveedor":
        res_conf = supabase.table("configuraciones_fabrica").select("*").eq("proveedor", st.session_state.usuario_actual).execute()
        mis_configs = res_conf.data if res_conf.data else []
        mis_categorias = [c for c in mis_configs if c['tipo'] == 'categoria']
        mis_colores = [c for c in mis_configs if c['tipo'] == 'color']
        mis_curvas = [c for c in mis_configs if c['tipo'] == 'curva']
        
        if st.session_state.panel_privado == "portada":
            st.title("🚀 Portada Comercial - NotPed")
            st.write("Así ven tu plataforma los visitantes no registrados:")
            st.write("")
            col_b1, col_b2 = st.columns(2)
            with col_b1: st.info("🏭 **FÁBRICA DESTACADA A**\n\nNueva Colección Primavera-Verano. Lanzamientos exclusivos.")
            with col_b2: st.success("🏭 **FÁBRICA DESTACADA B**\n\nEspecialistas en Línea Urbana y Deportiva. Envíos inmediatos.")

        # PESTAÑA 1: CARGA DE CALZADO
        elif st.session_state.panel_privado == "carga":
            st.title(f"🏭 Panel Fábrica | Carga de Calzado")
            
            tipo_carga = st.radio("Modo de Carga", ["Carga Manual (Uno a Uno)", "Carga Masiva (Excel)"], horizontal=True)
            st.write("---")

            # ----------------------------------------
            # CARGA MANUAL
            # ----------------------------------------
            if tipo_carga == "Carga Manual (Uno a Uno)":
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

                c_cat, c_col = st.columns(2)
                with c_cat:
                    if st.session_state.get(f"crear_cat_{fk}", False):
                        col_input, col_btn = st.columns([8, 1])
                        with col_input: cat_final = st.text_input("Categoría", placeholder="Ingresá la nueva categoría...", key=f"txt_cat_{fk}").strip()
                        with col_btn:
                            st.write("&nbsp;")
                            if st.button("🔙", key=f"b_cat_{fk}"): st.session_state[f"crear_cat_{fk}"] = False; st.rerun()
                        es_nueva_cat = True
                    else:
                        opciones = ["-- Elegir --", "➕ Crear Nueva..."] + [c['nombre'] for c in mis_categorias]
                        opcion_cat = st.selectbox("Categoría", opciones, key=f"sel_cat_{fk}")
                        if opcion_cat == "➕ Crear Nueva...": st.session_state[f"crear_cat_{fk}"] = True; st.rerun()
                        cat_final = opcion_cat if opcion_cat != "-- Elegir --" else ""
                        es_nueva_cat = False

                with c_col:
                    if st.session_state.get(f"crear_col_{fk}", False):
                        col_input, col_btn = st.columns([8, 1])
                        with col_input: col_final = st.text_input("Color", placeholder="Ingresá el nuevo color...", key=f"txt_col_{fk}").strip()
                        with col_btn:
                            st.write("&nbsp;")
                            if st.button("🔙", key=f"b_col_{fk}"): st.session_state[f"crear_col_{fk}"] = False; st.rerun()
                        es_nuevo_col = True
                    else:
                        opciones = ["-- Elegir --", "➕ Crear Nuevo..."] + [c['nombre'] for c in mis_colores]
                        opcion_col = st.selectbox("Color", opciones, key=f"sel_col_{fk}")
                        if opcion_col == "➕ Crear Nuevo...": st.session_state[f"crear_col_{fk}"] = True; st.rerun()
                        col_final = opcion_col if opcion_col != "-- Elegir --" else ""
                        es_nuevo_col = False

                art = st.text_input("Artículo (Ej: Bota 401)", key=f"txt_art_{fk}")
                desc = st.text_input("Descripción detallada", key=f"txt_desc_{fk}")
                
                st.write("---")
                st.markdown("**📏 Configuración de Curva de Talles**")
                
                curva_elegida = st.selectbox("Selecciona una Curva Guardada o crea una nueva", ["➕ Armar Nueva Curva..."] + [c['nombre'] for c in mis_curvas], key=f"sel_curv_{fk}")
                
                cantidades_def = []
                if curva_elegida == "➕ Armar Nueva Curva...":
                    tipo_curva_sel = st.radio("Tipo de Numeración", ["Numérica Simple", "Doble Par (Ej: 12/13)", "Doble Impar (Ej: 13/14)", "Alfabética (XXXS, S...)", "Sin Curva (N/A)"], horizontal=True, key=f"radio_tipo_{fk}")
                    
                    cd, ch = st.columns(2)
                    
                    if tipo_curva_sel == "Sin Curva (N/A)":
                        t_d_sel, t_h_sel = "N/A", "N/A"
                        talles_list_str = []
                        
                    elif tipo_curva_sel == "Numérica Simple":
                        t_d_sel = cd.number_input("Desde", min_value=1, max_value=120, value=35, key=f"n_d_{fk}")
                        t_h_sel = ch.number_input("Hasta", min_value=t_d_sel, max_value=120, value=min(t_d_sel+5, 120), key=f"n_h_{fk}")
                        t_d_sel, t_h_sel = str(t_d_sel), str(t_h_sel)
                        talles_list_str = [str(i) for i in range(int(t_d_sel), int(t_h_sel)+1)]

                    elif tipo_curva_sel == "Doble Par (Ej: 12/13)":
                        lst = [f"{i}/{i+1}" for i in range(12, 54, 2)]
                        t_d_sel = cd.selectbox("Desde", lst, index=11, key=f"dp_d_{fk}")
                        idx_d = lst.index(t_d_sel)
                        idx_h_def = idx_d + 1 if idx_d + 1 < len(lst) else idx_d
                        t_h_sel = ch.selectbox("Hasta", lst, index=idx_h_def, key=f"dp_h_{fk}")
                        idx_h = lst.index(t_h_sel)
                        talles_list_str = lst[idx_d : idx_h+1] if idx_h >= idx_d else []

                    elif tipo_curva_sel == "Doble Impar (Ej: 13/14)":
                        lst = [f"{i}/{i+1}" for i in range(13, 55, 2)]
                        t_d_sel = cd.selectbox("Desde", lst, index=11, key=f"di_d_{fk}")
                        idx_d = lst.index(t_d_sel)
                        idx_h_def = idx_d + 1 if idx_d + 1 < len(lst) else idx_d
                        t_h_sel = ch.selectbox("Hasta", lst, index=idx_h_def, key=f"di_h_{fk}")
                        idx_h = lst.index(t_h_sel)
                        talles_list_str = lst[idx_d : idx_h+1] if idx_h >= idx_d else []

                    elif tipo_curva_sel == "Alfabética (XXXS, S...)":
                        lst = ["XXXS", "XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL"]
                        t_d_sel = cd.selectbox("Desde", lst, index=3, key=f"a_d_{fk}")
                        idx_d = lst.index(t_d_sel)
                        idx_h_def = idx_d + 1 if idx_d + 1 < len(lst) else idx_d
                        t_h_sel = ch.selectbox("Hasta", lst, index=idx_h_def, key=f"a_h_{fk}")
                        idx_h = lst.index(t_h_sel)
                        talles_list_str = lst[idx_d : idx_h+1] if idx_h >= idx_d else []
                    
                    nombre_nueva_curva = st.text_input("💾 Nombre para guardar esta curva en tu lista (Opcional)", placeholder="Ej: Ojotas Mujer M-XL", key=f"txt_ncurv_{fk}").strip()
                    guardar_curva = True if nombre_nueva_curva and tipo_curva_sel != "Sin Curva (N/A)" else False
                    es_nueva_curva = True
                    
                else:
                    obj = next((c for c in mis_curvas if c['nombre'] == curva_elegida), None)
                    partes = obj['valor'].split('|')
                    if len(partes) == 4:
                        tipo_curva_sel, t_d_sel, t_h_sel = partes[0], partes[1], partes[2]
                        cantidades_def = partes[3].split('-')
                    else: 
                        tipo_curva_sel, t_d_sel, t_h_sel = "Numérica Simple", partes[0], partes[1]
                        cantidades_def = partes[2].split('-')
                    
                    st.info(f"📌 Cargando curva predefinida: {tipo_curva_sel} ({t_d_sel} al {t_h_sel})")
                    es_nueva_curva = False
                    guardar_curva = False
                    nombre_nueva_curva = ""
                    talles_list_str = generar_lista_talles(tipo_curva_sel, t_d_sel, t_h_sel)

                if "Sin Curva" in tipo_curva_sel:
                    st.info("📌 Este producto se guardará sin numeración específica.")
                    curva_final_str = "N/A"
                else:
                    if talles_list_str:
                        cols_talles = st.columns(len(talles_list_str))
                        valores_curva, total_pares = [], 0
                        for i, talle in enumerate(talles_list_str):
                            val_defecto = int(cantidades_def[i]) if (len(cantidades_def) > i and cantidades_def[i].isdigit()) else 0
                            with cols_talles[i]:
                                val = st.number_input(f"T-{talle}", min_value=0, step=1, value=val_defecto, key=f"talle_{i}_{fk}")
                                valores_curva.append(str(val))
                                total_pares += val
                        
                        st.markdown(f"<p style='text-align: right; color: #d32f2f; font-weight: bold; font-size:18px;'>Total pares por caja: {total_pares}</p>", unsafe_allow_html=True)
                        curva_final_str = "-".join(valores_curva)
                    else:
                        st.error("❌ Rango inválido. El talle 'Hasta' debe estar después del 'Desde'.")
                        curva_final_str = ""

                st.write("---")
                col_p, col_v = st.columns(2)
                with col_p: precio = st.number_input("Precio de Lista ($)", min_value=0.0, key=f"num_precio_{fk}")
                with col_v: video = st.text_input("URL de YouTube (Opcional)", placeholder="Ej: https://youtu.be/...", key=f"txt_vid_{fk}")
                
                foto = st.file_uploader("Subir Foto del Calzado (Máx 250kb)", type=["jpg", "png", "jpeg"], key=f"file_foto_{fk}")
                
                if st.button("Guardar Producto en Catálogo", type="primary", use_container_width=True):
                    if foto and foto.size > 256000:
                        st.error("❌ La imagen es demasiado pesada. El límite es de 250kb.")
                    elif not art or not foto or curva_final_str == "" or not cat_final or not col_final:
                        st.warning("⚠️ Faltan datos clave (Artículo, Foto, Categoría o Color).")
                    else:
                        with st.spinner("Guardando en la nube..."):
                            try:
                                if es_nueva_cat: supabase.table("configuraciones_fabrica").insert({"proveedor": st.session_state.usuario_actual, "tipo": "categoria", "nombre": cat_final}).execute()
                                if es_nuevo_col: supabase.table("configuraciones_fabrica").insert({"proveedor": st.session_state.usuario_actual, "tipo": "color", "nombre": col_final}).execute()
                                if guardar_curva:
                                    valor_curva = f"{tipo_curva_sel}|{t_d_sel}|{t_h_sel}|{curva_final_str}"
                                    supabase.table("configuraciones_fabrica").insert({"proveedor": st.session_state.usuario_actual, "tipo": "curva", "nombre": nombre_nueva_curva, "valor": valor_curva}).execute()

                                extension = foto.name.split('.')[-1]
                                nombre_archivo = f"{uuid.uuid4()}.{extension}"
                                supabase.storage.from_("fotos_productos").upload(nombre_archivo, foto.getvalue(), {"content-type": foto.type})
                                foto_url = supabase.storage.from_("fotos_productos").get_public_url(nombre_archivo)
                                
                                nuevo_prod = {
                                    "proveedor": st.session_state.usuario_actual, "categoria": cat_final, "articulo": art, "color": col_final, 
                                    "descripcion": desc, "precio": precio, "talle_desde": str(t_d_sel), "talle_hasta": str(t_h_sel),
                                    "curva": curva_final_str, "foto_url": foto_url, "video_url": video
                                }
                                supabase.table("productos").insert(nuevo_prod).execute()
                                
                                st.session_state.form_key += 1
                                st.success("✅ ¡Producto cargado con éxito! Redirigiendo al catálogo...")
                                time.sleep(1)
                                st.session_state.panel_privado = "catalogo"
                                st.query_params["panel"] = "catalogo"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al guardar: {e}")

            # ----------------------------------------
            # CARGA MASIVA (EXCEL) - EXCEL INTELIGENTE CON MENÚS DEPENDIENTES
            # ----------------------------------------
            elif tipo_carga == "Carga Masiva (Excel)":
                st.info("💡 **Instrucciones:** Descarga la plantilla, llénala desde la fila 3 y súbela. El Excel viene equipado con desplegables inteligentes que cambian automáticamente según el Tipo de Curva.")
                
                # Generar Plantilla Excel en memoria
                df_template = pd.DataFrame({
                    "Categoría": ["Ej: Deportiva Goma"],
                    "Artículo": ["Zapa Urban"],
                    "Color": ["Negro"],
                    "Descripción": ["Suela inyectada, alta resistencia"],
                    "Precio": [15000], 
                    "Tipo Curva": ["Numérica Simple"],
                    "Talle Desde": ["35"],
                    "Talle Hasta (Mayor al Desde)": ["40"],
                    "Cantidades (Ej: 2-2-3-2-2-1)": ["2-2-3-2-2-1"],
                    "URL Foto (Opcional)": [""],
                    "URL Video (Opcional)": ["https://youtu.be/..."]
                })
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_template.to_excel(writer, index=False, sheet_name='Plantilla')
                    worksheet = writer.sheets['Plantilla']
                    
                    for column in worksheet.columns:
                        max_length = 0
                        col_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length: max_length = len(str(cell.value))
                            except: pass
                        worksheet.column_dimensions[col_letter].width = max_length + 2

                    # 1. Validación Principal para Tipo de Curva (Columna F)
                    dv_tipo = DataValidation(type="list", formula1='"Numérica Simple,Doble Par,Doble Impar,Alfabética,Sin Curva (N/A)"', allow_blank=True)
                    worksheet.add_data_validation(dv_tipo)
                    dv_tipo.add('F3:F1048576') 

                    # 2. Hoja oculta con los datos en crudo para las validaciones dependientes
                    ws_listas = writer.book.create_sheet('Listas')
                    ws_listas.sheet_state = 'hidden'

                    num_simple = [str(i) for i in range(1, 121)]
                    doble_par = [f"{i}/{i+1}" for i in range(12, 54, 2)]
                    doble_impar = [f"{i}/{i+1}" for i in range(13, 55, 2)]
                    alfabetica = ["XXXS", "XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL"]
                    sin_curva = ["N/A"]

                    ws_listas.append(["Num", "Par", "Impar", "Alfa", "Na"])
                    max_len = max(len(num_simple), len(doble_par), len(doble_impar), len(alfabetica), len(sin_curva))

                    for i in range(max_len):
                        row = [
                            num_simple[i] if i < len(num_simple) else "",
                            doble_par[i] if i < len(doble_par) else "",
                            doble_impar[i] if i < len(doble_impar) else "",
                            alfabetica[i] if i < len(alfabetica) else "",
                            sin_curva[i] if i < len(sin_curva) else ""
                        ]
                        ws_listas.append(row)

                    # 3. Validación Dependiente Avanzada REPARADA (El truco del $F3 bloquea la evaluación relativa horizontal)
                    formula_talles = '=IF($F3="Numérica Simple",Listas!$A$2:$A$121,IF($F3="Doble Par",Listas!$B$2:$B$22,IF($F3="Doble Impar",Listas!$C$2:$C$22,IF($F3="Alfabética",Listas!$D$2:$D$10,Listas!$E$2:$E$2))))'
                    dv_talles = DataValidation(type="list", formula1=formula_talles, allow_blank=True)
                    worksheet.add_data_validation(dv_talles)
                    dv_talles.add('G3:H1048576')
                
                st.download_button(label="📥 Descargar Plantilla Excel Inteligente", data=buffer.getvalue(), file_name="Plantilla_Carga_NotPed.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
                st.write("---")
                excel_file = st.file_uploader("Sube tu archivo Excel lleno", type=["xlsx", "xls"])
                
                if excel_file is not None:
                    if st.button("🚀 Iniciar Procesamiento Masivo", type="primary"):
                        with st.spinner("Procesando productos en bloque... (Esto tomará solo un segundo)"):
                            try:
                                df = pd.read_excel(excel_file, skiprows=[1]).fillna("")
                                
                                nombres_cat_db = [c['nombre'] for c in mis_categorias]
                                nombres_col_db = [c['nombre'] for c in mis_colores]
                                nombres_cur_db = [c['nombre'] for c in mis_curvas]
                                
                                nuevas_cats, nuevas_cols, nuevas_curvas = [], [], []
                                cats_vistas, cols_vistas, curvas_vistas = set(), set(), set()
                                
                                productos_a_insertar = []
                                
                                for index, row in df.iterrows():
                                    cat_xls = str(row.get("Categoría", "")).strip()
                                    art_xls = str(row.get("Artículo", "")).strip()
                                    col_xls = str(row.get("Color", "")).strip()
                                    
                                    if not art_xls or not cat_xls: continue 
                                    
                                    if cat_xls not in nombres_cat_db and cat_xls not in cats_vistas:
                                        nuevas_cats.append({"proveedor": st.session_state.usuario_actual, "tipo": "categoria", "nombre": cat_xls})
                                        cats_vistas.add(cat_xls)
                                        
                                    if col_xls and col_xls not in nombres_col_db and col_xls not in cols_vistas:
                                        nuevas_cols.append({"proveedor": st.session_state.usuario_actual, "tipo": "color", "nombre": col_xls})
                                        cols_vistas.add(col_xls)
                                        
                                    t_curva = str(row.get("Tipo Curva", "Sin Curva (N/A)")).strip()
                                    t_desde = str(row.get("Talle Desde", "N/A")).strip()
                                    t_hasta = str(row.get("Talle Hasta (Mayor al Desde)", "N/A")).strip()
                                    cantidades = str(row.get("Cantidades (Ej: 2-2-3-2-2-1)", "N/A")).strip()
                                    
                                    nombre_curva_xls = f"Excel: {cat_xls} {col_xls}"
                                    if "Sin Curva" not in t_curva and cantidades != "N/A" and nombre_curva_xls not in nombres_cur_db and nombre_curva_xls not in curvas_vistas:
                                        val_curva_xls = f"{t_curva}|{t_desde}|{t_hasta}|{cantidades}"
                                        nuevas_curvas.append({"proveedor": st.session_state.usuario_actual, "tipo": "curva", "nombre": nombre_curva_xls, "valor": val_curva_xls})
                                        curvas_vistas.add(nombre_curva_xls)

                                    precio_xls = row.get("Precio", 0)
                                    precio_xls = float(precio_xls) if str(precio_xls).replace('.','',1).isdigit() else 0.0
                                    
                                    f_url = str(row.get("URL Foto (Opcional)", "")).strip()
                                    v_url = str(row.get("URL Video (Opcional)", "")).strip()
                                    
                                    productos_a_insertar.append({
                                        "proveedor": st.session_state.usuario_actual, "categoria": cat_xls, "articulo": art_xls, "color": col_xls, 
                                        "descripcion": str(row.get("Descripción", "")).strip(), "precio": precio_xls,
                                        "talle_desde": t_desde, "talle_hasta": t_hasta, "curva": cantidades, "foto_url": f_url if f_url else None, "video_url": v_url if v_url else None
                                    })
                                
                                if nuevas_cats: supabase.table("configuraciones_fabrica").insert(nuevas_cats).execute()
                                if nuevas_cols: supabase.table("configuraciones_fabrica").insert(nuevas_cols).execute()
                                if nuevas_curvas: supabase.table("configuraciones_fabrica").insert(nuevas_curvas).execute()
                                
                                if productos_a_insertar:
                                    supabase.table("productos").insert(productos_a_insertar).execute()
                                
                                st.success(f"✅ ¡Se procesaron {len(productos_a_insertar)} productos en tiempo récord! Redirigiendo al catálogo...")
                                time.sleep(2)
                                st.session_state.panel_privado = "catalogo"
                                st.query_params["panel"] = "catalogo"
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Error procesando el archivo: {e}")

        # PESTAÑA 2: CATÁLOGO AGRUPADO
        elif st.session_state.panel_privado == "catalogo":
            st.title(f"🏭 Panel Fábrica | {st.session_state.marca_actual}")
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
                                if p.get("foto_url"): 
                                    st.image(p["foto_url"], use_container_width=True)
                                else:
                                    st.warning("🖼️ Foto Pendiente")
                                    img_up = st.file_uploader("Subir JPG/PNG", type=["jpg", "png", "jpeg"], key=f"up_{p['id']}")
                                    if img_up:
                                        with st.spinner("Subiendo..."):
                                            extension = img_up.name.split('.')[-1]
                                            nombre_archivo = f"{uuid.uuid4()}.{extension}"
                                            supabase.storage.from_("fotos_productos").upload(nombre_archivo, img_up.getvalue(), {"content-type": img_up.type})
                                            f_url = supabase.storage.from_("fotos_productos").get_public_url(nombre_archivo)
                                            supabase.table("productos").update({"foto_url": f_url}).eq("id", p['id']).execute()
                                            st.rerun()

                            with c2:
                                st.markdown(f"**{p['articulo']}** | {p.get('color', '')}")
                                st.write(p.get("descripcion", ""))
                                st.markdown(f"<h4 style='color: #28a745;'>${p['precio']:,.0f}</h4>", unsafe_allow_html=True)
                                if p.get("video_url"):
                                    st.markdown(f"[▶️ Ver Video en YouTube]({p['video_url']})")
                            with c3:
                                if p.get("curva") == "N/A":
                                    st.write("**Curva de Talles:**")
                                    st.code("N/A - Sin Curva Específica")
                                else:
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
        elif st.session_state.panel_privado == "clientes":
            st.title(f"🏭 Panel Fábrica | {st.session_state.marca_actual}")
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
