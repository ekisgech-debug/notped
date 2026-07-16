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
        .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 95%; }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 8px 12px !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        }
        .stMarkdown p { margin-bottom: 0px !important; }
        [data-testid="column"] { padding: 0 6px !important; }
        /* Ajuste para los casilleros de talles del cliente */
        input[type="number"] { text-align: center; font-weight: bold; }
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
if "ndp_activa" not in st.session_state: st.session_state.ndp_activa = None
if "cat_activa" not in st.session_state: st.session_state.cat_activa = None

fk = st.session_state.form_key 

if st.session_state.usuario_actual is None and "uid" in st.query_params:
    try:
        res = supabase.table("usuarios").select("*").eq("id", st.query_params["uid"]).execute()
        if res.data:
            st.session_state.usuario_actual = res.data[0]["email"]
            st.session_state.rol_actual = res.data[0]["rol"]
            st.session_state.marca_actual = res.data[0]["nombre_marca"]
            st.session_state.panel_privado = st.query_params.get("panel", "carga")
    except: pass

# ========================================================
# VENTANAS FLOTANTES
# ========================================================
@st.dialog("Renombrar Categoría")
def dialog_editar_categoria(c_id, viejo_nombre):
    nuevo_nombre = st.text_input("Nuevo nombre:", value=viejo_nombre).strip()
    if st.button("Guardar Cambios", type="primary"):
        if nuevo_nombre and nuevo_nombre != viejo_nombre:
            supabase.table("configuraciones_fabrica").update({"nombre": nuevo_nombre}).eq("id", c_id).execute()
            supabase.table("productos").update({"categoria": nuevo_nombre}).eq("proveedor", st.session_state.usuario_actual).eq("categoria", viejo_nombre).execute()
            st.rerun()

@st.dialog("Editar Producto")
def dialog_editar_producto(p):
    n_art = st.text_input("Artículo", value=p['articulo'])
    n_col = st.text_input("Color", value=p.get('color',''))
    n_desc = st.text_input("Descripción", value=p.get('descripcion',''))
    n_precio = st.number_input("Precio ($)", value=float(p['precio']))
    n_vid = st.text_input("URL Video YouTube", value=p.get('video_url', '') or '')
    if st.button("Guardar Cambios", type="primary", use_container_width=True):
        supabase.table("productos").update({
            "articulo": n_art, "color": n_col, "descripcion": n_desc, 
            "precio": n_precio, "video_url": n_vid
        }).eq("id", p['id']).execute()
        st.rerun()

@st.dialog("Subir Foto del Producto")
def dialog_subir_foto(p_id, articulo):
    img_up = st.file_uploader("JPG / PNG", type=["jpg", "png", "jpeg"], key=f"up_{p_id}")
    if img_up:
        with st.spinner("Subiendo..."):
            extension = img_up.name.split('.')[-1]
            nombre_archivo = f"{uuid.uuid4()}.{extension}"
            supabase.storage.from_("fotos_productos").upload(nombre_archivo, img_up.getvalue(), {"content-type": img_up.type})
            f_url = supabase.storage.from_("fotos_productos").get_public_url(nombre_archivo)
            supabase.table("productos").update({"foto_url": f_url}).eq("id", p_id).execute()
            st.rerun()

@st.dialog("Vista Ampliada")
def dialog_ampliar_imagen(url, articulo):
    st.image(url, use_container_width=True)

@st.dialog("Compartir Código NdP")
def dialog_compartir_categoria(categoria):
    st.write(f"Compartiendo: **{categoria}**")
    cliente = st.text_input("Referencia (Ej: Local Centro)").strip()
    descuento = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    if st.button("Generar Código", type="primary"):
        if cliente:
            codigo = f"NDP-{uuid.uuid4().hex[:5].upper()}"
            try:
                supabase.table("notas_pedido").insert({
                    "codigo_acceso": codigo,
                    "proveedor_email": st.session_state.usuario_actual,
                    "nombre_cliente_referencia": cliente,
                    "categoria_compartida": categoria,
                    "descuento": descuento
                }).execute()
                st.success("✅ ¡Código Creado!")
                st.code(codigo)
                st.info("Copia el código y envíalo al cliente.")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Debes ingresar una referencia.")

@st.dialog("Duplicar Catálogo Completo")
def dialog_duplicar_categoria(cat_name):
    st.info(f"Vas a crear una copia exacta de todos los productos de **{cat_name}**.")
    nuevo_nombre = st.text_input("Nombre para el nuevo catálogo:", value=f"{cat_name} (Copia)").strip()
    if st.button("Crear Duplicado", type="primary"):
        if nuevo_nombre and nuevo_nombre != cat_name:
            with st.spinner("Clonando catálogo..."):
                prods = supabase.table("productos").select("*").eq("proveedor", st.session_state.usuario_actual).eq("categoria", cat_name).execute().data
                for p in prods:
                    del p['id']  # Quitamos el ID para que Supabase genere unos nuevos
                    if 'created_at' in p: del p['created_at']
                    p['categoria'] = nuevo_nombre
                
                if prods:
                    supabase.table("productos").insert(prods).execute()
                
                st.success(f"¡Catálogo '{nuevo_nombre}' creado con éxito!")
                time.sleep(1.5)
                st.rerun()
        else:
            st.warning("Ingresa un nombre diferente al original.")

def mostrar_detalle_pedido(detalle_json, codigo_pedido):
    if not detalle_json:
        return
    
    filas = []
    # Recorremos el JSON para armar filas de datos
    for p_id, data in detalle_json.items():
        fila = {
            "Artículo": data.get("articulo", ""),
            "Precio Unit. ($)": data.get("precio_unitario", 0),
            "Pares Totales": data.get("pares_totales", 0)
        }
        # Desglosar los talles en columnas dinámicas
        for talle, cant in data.get("curva_elegida", {}).items():
            fila[f"T-{talle}"] = cant
        filas.append(fila)
        
    if filas:
        # Convertir a DataFrame de pandas
        df = pd.DataFrame(filas).fillna(0)
        
        # Ordenar columnas para que los talles queden al final
        cols_base = ["Artículo", "Precio Unit. ($)", "Pares Totales"]
        cols_talles = sorted([c for c in df.columns if c.startswith("T-")])
        df = df[cols_base + cols_talles]
        
        # Formatear números para que no salgan con decimales .0
        for col in cols_talles + ["Pares Totales"]:
            df[col] = df[col].astype(int)
                
        # Mostrar tabla interactiva en Streamlit
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Preparar archivo Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Nota de Pedido')
        excel_data = output.getvalue()
        
        # Botón de exportación
        st.download_button(
            label="📊 Descargar Excel", 
            data=excel_data, 
            file_name=f"NdP_{codigo_pedido}.xlsx", 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"xls_{codigo_pedido}_{uuid.uuid4().hex[:5]}"
        )
        

# --- GENERADOR DE PDF ---
@st.cache_data(show_spinner=False)
def generar_pdf_catalogo(productos, marca, titulo_cat):
    try:
        from fpdf import FPDF
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("helvetica", style="B", size=16)
        pdf.cell(0, 10, f"CATÁLOGO MAYORISTA - {marca}", ln=True, align="C")
        pdf.set_font("helvetica", style="I", size=12)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Categoría: {titulo_cat}", ln=True, align="C")
        pdf.ln(6)
        
        for p in productos:
            x_start = pdf.get_x()
            y_start = pdf.get_y()
            if y_start > 265:
                pdf.add_page()
                y_start = pdf.get_y()
            pdf.set_draw_color(220, 220, 220)
            pdf.rect(10, y_start, 190, 22)
            if p.get('foto_url'):
                try:
                    resp = requests.get(p['foto_url'], timeout=3)
                    if resp.status_code == 200:
                        img_stream = io.BytesIO(resp.content)
                        pdf.image(img_stream, x=12, y=y_start+2, w=22, h=18, keep_aspect_ratio=True)
                except: pass
            pdf.set_text_color(40, 40, 40)
            pdf.set_xy(38, y_start + 5)
            pdf.set_font("helvetica", style="B", size=11)
            pdf.cell(70, 6, f"{p['articulo']}  |  {p.get('color','')}", ln=False)
            pdf.set_xy(38, y_start + 11)
            pdf.set_font("helvetica", size=8)
            pdf.set_text_color(120, 120, 120)
            desc = str(p.get('descripcion',''))[:45] + "..." if len(str(p.get('descripcion',''))) > 45 else str(p.get('descripcion',''))
            pdf.cell(70, 5, desc, ln=False)
            pdf.set_xy(110, y_start + 5)
            pdf.set_font("helvetica", size=9)
            pdf.set_text_color(100, 100, 100)
            if p.get("curva") == "N/A": pdf.cell(40, 6, "Talles: Sin Curva", ln=False)
            else:
                pdf.cell(40, 6, f"Talles: {p['talle_desde']} al {p['talle_hasta']}", ln=False)
                pdf.set_xy(110, y_start + 11)
                pdf.set_font("courier", style="B", size=9)
                pdf.set_text_color(23, 162, 184)
                pdf.cell(40, 5, f"Curva: {p.get('curva','')}", ln=False)
            pdf.set_xy(150, y_start + 7)
            pdf.set_font("helvetica", style="B", size=14)
            pdf.set_text_color(40, 167, 69)
            pdf.cell(45, 8, f"${p['precio']:,.0f}", ln=False, align="R")
            pdf.set_text_color(0, 0, 0)
            pdf.set_y(y_start + 24)
        return bytes(pdf.output())
    except: return None

# ========================================================
# FLUX 1: ENTORNO PÚBLICO
# ========================================================
if st.session_state.usuario_actual is None:
    st.query_params.clear() 
    col_logo, col_nav = st.columns([2, 3])
    with col_logo: st.markdown("<h2 style='margin:0;'>👞 NotPed <span style='font-size:14px; color:gray;'>B2B</span></h2>", unsafe_allow_html=True)
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
        st.title("🚀 Conectamos Fábricas con Revendedores")
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
                        st.session_state.panel_privado = "pedidos" if res.data[0]["rol"] == "proveedor" else "ingresar_ndp"
                        st.session_state.remember_email = u_email if recordar else ""
                        st.query_params["uid"] = str(res.data[0]["id"])
                        st.query_params["panel"] = st.session_state.panel_privado
                        st.rerun()
                    else: st.error("❌ Datos incorrectos.")
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
                            st.success("✅ Cuenta creada.")
                            time.sleep(1)
                            st.session_state.seccion_publica = "login"
                            st.rerun()

# ========================================================
# FLUX 2: ENTORNO PRIVADO
# ========================================================
else:
    # ----------------------------------------------------
    # PANEL FÁBRICA
    # ----------------------------------------------------
    if st.session_state.rol_actual == "proveedor":
        with st.sidebar:
            st.markdown(f"### {st.session_state.marca_actual}")
            st.success("🏭 Panel Fábrica")
            st.write("---")
            if st.button("📦 Notas de Pedido", use_container_width=True): 
                st.session_state.panel_privado = "pedidos"
                st.query_params["panel"] = "pedidos"
                st.rerun()
            if st.button("👞 Mis Catálogos", use_container_width=True): 
                st.session_state.cat_activa = None
                st.session_state.panel_privado = "catalogo"
                st.query_params["panel"] = "catalogo"
                st.rerun()
            if st.button("➕ Cargar Calzado", use_container_width=True): 
                st.session_state.panel_privado = "carga"
                st.query_params["panel"] = "carga"
                st.rerun()
            st.write("---")
            if st.button("🚪 Cerrar Sesión", use_container_width=True):
                st.session_state.clear(); st.query_params.clear(); st.rerun()

        # BI & Notas de Pedido (Fábrica)
        if st.session_state.panel_privado == "pedidos":
            st.title("📦 Mis Notas de Pedido")
            res_pedidos = supabase.table("notas_pedido").select("*").eq("proveedor_email", st.session_state.usuario_actual).execute().data or []
            finalizados = [p for p in res_pedidos if p['estado'] == 'Finalizado']
            
            c1, c2, c3 = st.columns(3)
            c1.metric("$ Vendido", f"{sum(p['monto_total'] for p in finalizados):,.0f}")
            c2.metric("Pares Solicitados", f"{sum(p['pares_totales'] for p in finalizados)}")
            c3.metric("NdP Finalizadas", f"{len(finalizados)}")
            st.write("---")
            
            st.subheader("Historial de Códigos NdP")
            for ndp in sorted(res_pedidos, key=lambda x: x['id'], reverse=True):
                with st.expander(f"[{ndp['estado']}] {ndp['codigo_acceso']} | Cliente: {ndp['nombre_cliente_referencia']} | Total: ${ndp['monto_total']:,.0f}"):
                    st.write(f"**Categoría Compartida:** {ndp['categoria_compartida']} | **Descuento:** {ndp['descuento']}%")
                    if ndp['estado'] == "Finalizado" and ndp.get('detalle_json'):
                        mostrar_detalle_pedido(ndp['detalle_json'], ndp['codigo_acceso'])
                    elif ndp['estado'] == "En Proceso":
                        st.info("El cliente está armando el pedido en este momento.")

        # CARGA
        elif st.session_state.panel_privado == "carga":
            st.title(f"🏭 Carga de Calzado")
            st.info("Funcionalidad de carga oculta por brevedad en este ejemplo. (Utiliza tu bloque de código de carga anterior).")

        # CATÁLOGOS: VISTA DE GRILLA -> VISTA DE DETALLE
        elif st.session_state.panel_privado == "catalogo":
            # Si no hay catálogo activo, mostramos la grilla de catálogos
            if st.session_state.cat_activa is None:
                st.title(f"🏭 Mis Catálogos | {st.session_state.marca_actual}")
                st.write("---")
                res_prod = supabase.table("productos").select("categoria").eq("proveedor", st.session_state.usuario_actual).execute()
                
                if res_prod.data:
                    categorias_presentes = sorted(list(set([p['categoria'] for p in res_prod.data])))
                    
                    # Mostrar las categorías como tarjetas (3 columnas)
                    cols = st.columns(3)
                    for idx, cat_name in enumerate(categorias_presentes):
                        with cols[idx % 3]:
                            with st.container(border=True):
                                st.markdown(f"<h3 style='color: #FFB300; text-align:center;'>📁 {cat_name}</h3>", unsafe_allow_html=True)
                                
                                c_abrir, c_comp = st.columns(2)
                                with c_abrir:
                                    if st.button("📂 Abrir", key=f"abr_{idx}", use_container_width=True):
                                        st.session_state.cat_activa = cat_name
                                        st.rerun()
                                with c_comp:
                                    if st.button("🔗 Compartir", key=f"cmp_{idx}", use_container_width=True):
                                        dialog_compartir_categoria(cat_name)
                                        
                                if st.button("📋 Duplicar Catálogo", key=f"dup_{idx}", use_container_width=True):
                                    dialog_duplicar_categoria(cat_name)
                else:
                    st.info("Aún no tienes productos en tu catálogo.")
            
            # Si hay un catálogo seleccionado, mostramos sus productos
            else:
                cat_name = st.session_state.cat_activa
                
                # Cabecera con botón de retroceso
                c_back, c_titulo, c_pdf = st.columns([1, 5, 2], vertical_alignment="bottom")
                with c_back:
                    if st.button("🔙 Volver"):
                        st.session_state.cat_activa = None
                        st.rerun()
                with c_titulo:
                    st.markdown(f"<h2 style='color: #FFB300; margin-bottom: 0px;'>📁 {cat_name}</h2>", unsafe_allow_html=True)
                
                res_prod = supabase.table("productos").select("*").eq("proveedor", st.session_state.usuario_actual).eq("categoria", cat_name).execute()
                prods_cat = res_prod.data if res_prod.data else []
                prods_cat = sorted(prods_cat, key=lambda x: str(x.get('articulo', '')).lower())
                
                with c_pdf:
                    pdf_data = generar_pdf_catalogo(prods_cat, st.session_state.marca_actual, cat_name)
                    if pdf_data:
                        st.download_button("📥 PDF Categoría", data=pdf_data, file_name=f"{cat_name}.pdf", mime="application/pdf", use_container_width=True)
                
                st.write("---")
                
                for p in prods_cat:
                    with st.container(border=True):
                        c_img, c_lupa, c_vid, c_info, c_talles, c_precio, c_edit, c_del = st.columns([0.8, 0.5, 0.5, 3.5, 2.5, 1.5, 0.5, 0.5], vertical_alignment="center")
                        with c_img:
                            if p.get("foto_url"): st.image(p["foto_url"])
                            else:
                                if st.button("📷", key=f"f_{p['id']}"): dialog_subir_foto(p['id'], p['articulo'])
                        with c_lupa:
                            if p.get("foto_url"):
                                if st.button("🔍", key=f"z_{p['id']}"): dialog_ampliar_imagen(p["foto_url"], p['articulo'])
                        with c_vid:
                            if p.get("video_url"): st.link_button("▶️", p["video_url"])
                        with c_info:
                            st.markdown(f"<strong style='font-size:15px;'>{p['articulo']}</strong> | <span style='color:gray;'>{p.get('color','')}</span>", unsafe_allow_html=True)
                        with c_talles:
                            if p.get("curva") == "N/A": st.caption("Sin Curva")
                            else:
                                st.caption(f"Talles: {p.get('talle_desde')} al {p.get('talle_hasta')}")
                                st.code(p.get('curva'))
                        with c_precio:
                            st.markdown(f"<div style='color:#00a650; font-size:22px; font-weight:bold;'>${p['precio']:,.0f}</div>", unsafe_allow_html=True)
                        with c_edit:
                            if st.button("✏️", key=f"e_{p['id']}"): dialog_editar_producto(p)
                        with c_del:
                            if st.button("🗑️", key=f"d_{p['id']}"): 
                                supabase.table("productos").delete().eq("id", p['id']).execute()
                                st.rerun()

    # ----------------------------------------------------
    # PANEL REVENDEDOR
    # ----------------------------------------------------
    elif st.session_state.rol_actual == "revendedor":
        with st.sidebar:
            st.markdown(f"### {st.session_state.marca_actual}")
            st.warning("🛒 Panel Revendedor")
            st.write("---")
            if st.button("🛒 Ingresar código NdP", use_container_width=True): 
                st.session_state.panel_privado = "ingresar_ndp"
                st.query_params["panel"] = "ingresar_ndp"
                st.rerun()
            if st.button("📦 Mis Pedidos", use_container_width=True): 
                st.session_state.panel_privado = "mis_pedidos"
                st.query_params["panel"] = "mis_pedidos"
                st.rerun()
            st.write("---")
            if st.button("🚪 Cerrar Sesión", use_container_width=True):
                st.session_state.clear(); st.query_params.clear(); st.rerun()

        # INGRESAR CÓDIGO & CARRITO INTELIGENTE
        if st.session_state.panel_privado == "ingresar_ndp":
            col_in, _ = st.columns([2, 1])
            with col_in:
                cod_input = st.text_input("Ingresar código NdP:", placeholder="Ej: NDP-A1B2C").strip()
                if st.button("Validar y Cargar Catálogo", type="primary"):
                    if cod_input:
                        res = supabase.table("notas_pedido").select("*").eq("codigo_acceso", cod_input).execute()
                        if res.data:
                            ndp = res.data[0]
                            if ndp['estado'] == "Enviado" and not ndp['revendedor_email']:
                                supabase.table("notas_pedido").update({"revendedor_email": st.session_state.usuario_actual, "estado": "En Proceso"}).eq("id", ndp['id']).execute()
                                st.session_state.ndp_activa = cod_input
                                st.rerun()
                            elif ndp['revendedor_email'] == st.session_state.usuario_actual and ndp['estado'] == "En Proceso":
                                st.session_state.ndp_activa = cod_input
                                st.rerun()
                            elif ndp['estado'] == "Finalizado":
                                st.warning("Esta Nota de Pedido ya fue enviada a la fábrica y finalizada.")
                            else:
                                st.error("Código no asignado a tu cuenta.")
                        else:
                            st.error("Código no encontrado.")

            # VISTA DE CARRITO (Con carga por talle individual)
            if st.session_state.ndp_activa:
                cod = st.session_state.ndp_activa
                ndp_data = supabase.table("notas_pedido").select("*").eq("codigo_acceso", cod).execute().data[0]
                descuento_aplicado = float(ndp_data['descuento'])
                
                st.write("---")
                if descuento_aplicado > 0:
                    st.markdown(f"<h3 style='color:#00a650;'>📦 Pedido Activo: {ndp_data['categoria_compartida']} <span style='font-size:16px; background-color:#FFB300; padding:3px 8px; border-radius:5px; color:black;'>Descuento: {descuento_aplicado}% OFF</span></h3>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<h3 style='color:#00a650;'>📦 Pedido Activo: {ndp_data['categoria_compartida']}</h3>", unsafe_allow_html=True)
                
                prods = supabase.table("productos").select("*").eq("proveedor", ndp_data['proveedor_email'])
                if ndp_data['categoria_compartida'] != "Todo el Catálogo":
                    prods = prods.eq("categoria", ndp_data['categoria_compartida'])
                prods = prods.order("articulo").execute().data
                
                # Memoria de carrito por código
                if f"cart_{cod}" not in st.session_state: st.session_state[f"cart_{cod}"] = {}

                total_plata = 0
                total_pares = 0
                
                for p in prods:
                    precio_final = float(p['precio']) * (1 - descuento_aplicado/100)
                    
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([1, 2, 6, 1.5], vertical_alignment="center")
                        
                        with c1:
                            if p.get('foto_url'): st.image(p['foto_url'])
                        
                        with c2:
                            st.markdown(f"**{p['articulo']}**<br><span style='color:gray; font-size:14px;'>{p.get('color','')}</span>", unsafe_allow_html=True)
                        
                        with c3:
                            # ---------------------------------------------
                            # GENERADOR DE CURVAS A ELECCIÓN DEL CLIENTE
                            # ---------------------------------------------
                            st.markdown(f"<span style='font-size:12px; color:#17A2B8;'>Talles fábrica: {p.get('talle_desde')} al {p.get('talle_hasta')} | Curva base sugerida: {p.get('curva','N/A')}</span>", unsafe_allow_html=True)
                            
                            talles = []
                            if str(p.get('talle_desde','')).isdigit() and str(p.get('talle_hasta','')).isdigit():
                                talles = [str(i) for i in range(int(p['talle_desde']), int(p['talle_hasta'])+1)]
                            else:
                                talles = [f"T-{i+1}" for i in range(len(p.get('curva','').split('-')))] if p.get('curva') != 'N/A' else ["Único"]
                            if not talles: talles = ["Único"]
                            
                            cols_talles = st.columns(len(talles))
                            pares_articulo = 0
                            detalle_talles_elegidos = {}
                            
                            for i, t in enumerate(talles):
                                with cols_talles[i]:
                                    # Cargar memoria si ya lo había llenado
                                    val_previo = 0
                                    if str(p['id']) in st.session_state[f"cart_{cod}"]:
                                        val_previo = st.session_state[f"cart_{cod}"][str(p['id'])]["curva_elegida"].get(t, 0)
                                        
                                    val = st.number_input(t, min_value=0, step=1, value=val_previo, key=f"t_{p['id']}_{t}")
                                    if val > 0: detalle_talles_elegidos[t] = val
                                    pares_articulo += val
                                    
                            if pares_articulo > 0:
                                st.session_state[f"cart_{cod}"][str(p['id'])] = {
                                    "articulo": p['articulo'],
                                    "precio_unitario": precio_final,
                                    "pares_totales": pares_articulo,
                                    "curva_elegida": detalle_talles_elegidos
                                }
                            else:
                                if str(p['id']) in st.session_state[f"cart_{cod}"]:
                                    del st.session_state[f"cart_{cod}"][str(p['id'])]
                                    
                            total_pares += pares_articulo
                            total_plata += (pares_articulo * precio_final)

                        with c4:
                            # Mostrar precio original tachado SOLO si hay descuento
                            if descuento_aplicado > 0:
                                st.markdown(f"<span style='text-decoration:line-through; color:gray; font-size:14px;'>${p['precio']:,.0f}</span>", unsafe_allow_html=True)
                            
                            st.markdown(f"<h4 style='color:#00a650; margin:0;'>${precio_final:,.0f}</h4>", unsafe_allow_html=True)
                            
                            if pares_articulo > 0:
                                st.caption(f"Subtotal: ${pares_articulo * precio_final:,.0f}")
                                
                st.write("---")
                c_tot1, c_tot2, c_btn = st.columns([3, 3, 4], vertical_alignment="center")
                c_tot1.markdown(f"### Pares: {total_pares}")
                c_tot2.markdown(f"### Total: ${total_plata:,.0f}")
                
                with c_btn:
                    if st.button("✅ Finalizar Pedido", type="primary", use_container_width=True):
                        detalle_final = st.session_state[f"cart_{cod}"]
                        if not detalle_final:
                            st.error("Agrega al menos 1 par de algún producto antes de finalizar.")
                        else:
                            supabase.table("notas_pedido").update({
                                "estado": "Finalizado",
                                "monto_total": total_plata,
                                "pares_totales": total_pares,
                                "detalle_json": detalle_final
                            }).eq("id", ndp_data['id']).execute()
                            
                            st.session_state.ndp_activa = None
                            st.success("¡Pedido enviado a la fábrica exitosamente!")
                            time.sleep(2)
                            st.session_state.panel_privado = "mis_pedidos"
                            st.rerun()

        # BI & HISTORIAL DEL REVENDEDOR
        elif st.session_state.panel_privado == "mis_pedidos":
            st.title("📦 Mis Pedidos Históricos")
            res_pedidos = supabase.table("notas_pedido").select("*").eq("revendedor_email", st.session_state.usuario_actual).eq("estado", "Finalizado").execute().data or []
            
            c1, c2, c3 = st.columns(3)
            c1.metric("$ Invertido", f"{sum(p['monto_total'] for p in res_pedidos):,.0f}")
            c2.metric("Pares Comprados", f"{sum(p['pares_totales'] for p in res_pedidos)}")
            c3.metric("NdP Finalizadas", f"{len(res_pedidos)}")
            st.write("---")
            
            for ndp in sorted(res_pedidos, key=lambda x: x['id'], reverse=True):
                with st.expander(f"Código: {ndp['codigo_acceso']} | Fábrica: {ndp['proveedor_email']} | Total: ${ndp['monto_total']:,.0f}"):
                    st.write(f"**Categoría:** {ndp['categoria_compartida']} | **Descuento Aplicado:** {ndp['descuento']}% | **Pares Totales:** {ndp['pares_totales']}")
                    mostrar_detalle_pedido(ndp['detalle_json'], ndp['codigo_acceso'])
