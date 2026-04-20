import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import random
import string
import plotly.graph_objects as go
import plotly.express as px
from supabase import create_client

st.set_page_config(page_title="Surtidor Médico", layout="wide", initial_sidebar_state="expanded")

# ==============================
# CACHE & CONFIG
# ==============================
@st.cache_resource
def get_supabase_client():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

@st.cache_data(ttl=300)
def get_cached_inventario():
    return cargar_inventario()

@st.cache_data(ttl=300)
def get_cached_asesores():
    return obtener_asesores()

@st.cache_data(ttl=300)
def get_cached_clientes():
    return cargar_clientes()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

ESTADOS_EQUIPO = ["Recién ingresado", "En proceso de venta", "Listo para vender", "Pendiente por repuesto"]
COLOR_ESTADO = {"Recién ingresado": "🟡", "En proceso de venta": "🔵", "Listo para vender": "🟢", "Pendiente por repuesto": "🔴"}
ESTADOS_BATERIA = ["Disponible", "En uso", "Dañada", "En mantenimiento", "Baja de inventario"]
COLOR_BATERIA = {"Disponible": "🟢", "En uso": "🔵", "Dañada": "🔴", "En mantenimiento": "🟡", "Baja de inventario": "⚫"}

def generar_serial(prefijo="SM"):
    chars = string.ascii_uppercase + string.digits
    return f"{prefijo}-{''.join(random.choices(chars, k=6))}"

# ==============================
# BÚSQUEDA
# ==============================
def buscar_por_serial(serial):
    try:
        supabase = get_supabase_client()
        resultado = {"equipo": None, "insumo": None, "bateria": None}
        eq = supabase.table("equipos").select("*").eq("Serial", serial).execute()
        if eq.data: resultado["equipo"] = eq.data[0]
        inv = supabase.table("inventario").select("*").eq("serial", serial).execute()
        if inv.data: resultado["insumo"] = inv.data[0]
        bat = supabase.table("baterias").select("*").eq("serial", serial).execute()
        if bat.data: resultado["bateria"] = bat.data[0]
        return resultado
    except Exception as e:
        st.error(f"❌ Error buscando serial: {e}")
        return {"equipo": None, "insumo": None, "bateria": None}

# ==============================
# AUTENTICACIÓN
# ==============================
def verificar_usuario(usuario, contraseña):
    if not usuario or not contraseña: return False, None, None
    try:
        supabase = get_supabase_client()
        resp = supabase.table("usuarios").select("*").eq("usuario", usuario).execute()
        if not resp.data: return False, None, None
        row = resp.data[0]
        if row["contrasena"] == hash_password(contraseña): return True, row["rol"], row["nombre"]
        return False, None, None
    except Exception as e:
        st.error(f"❌ Error verificando usuario: {e}")
        return False, None, None

# ==============================
# ASESORES Y CLIENTES
# ==============================
def obtener_asesores():
    try:
        supabase = get_supabase_client()
        resp = supabase.table("usuarios").select("usuario,nombre").eq("rol", "asesor").execute()
        return [r["usuario"] for r in (resp.data or [])]
    except: return []

def cargar_clientes(asesor=None):
    try:
        supabase = get_supabase_client()
        query = supabase.table("clientes").select("*")
        if asesor: query = query.eq("asesor", asesor)
        resp = query.execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            for col in ["nombre","cedula","telefono","direccion","asesor"]:
                if col not in df.columns: df[col] = ""
            return df
        return pd.DataFrame(columns=["id","nombre","cedula","telefono","direccion","asesor"])
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return pd.DataFrame(columns=["id","nombre","cedula","telefono","direccion","asesor"])

def guardar_cliente(nombre, cedula, telefono, asesor):
    try:
        supabase = get_supabase_client()
        supabase.table("clientes").insert({"nombre": nombre, "cedula": cedula, "telefono": telefono, "asesor": asesor}).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

def eliminar_cliente(cliente_id):
    try:
        supabase = get_supabase_client()
        supabase.table("clientes").delete().eq("id", cliente_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

# ==============================
# INVENTARIO - CAJAS
# ==============================
def cargar_inventario():
    try:
        supabase = get_supabase_client()
        resp = supabase.table("inventario").select("*").execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            for col in ["Cantidad", "Cantidad_Total"]:
                if col not in df.columns: df[col] = 0
            return df
        return pd.DataFrame(columns=["id","Caja","Cantidad","Cantidad_Total","serial"])
    except Exception as e:
        st.error(f"❌ Error cargando inventario: {e}")
        return pd.DataFrame(columns=["id","Caja","Cantidad","Cantidad_Total","serial"])

def guardar_caja_nueva(caja):
    try:
        supabase = get_supabase_client()
        serial = generar_serial("INS")
        supabase.table("inventario").insert({"Caja": caja, "Cantidad": 0, "Cantidad_Total": 0, "serial": serial}).execute()
        return True, serial
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False, None

def actualizar_caja(caja_id, campos):
    try:
        supabase = get_supabase_client()
        supabase.table("inventario").update(campos).eq("id", caja_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

def eliminar_caja(caja_id):
    try:
        supabase = get_supabase_client()
        # Primero eliminar items
        supabase.table("items_caja").delete().eq("caja_id", caja_id).execute()
        # Luego eliminar caja
        supabase.table("inventario").delete().eq("id", caja_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

# ==============================
# ITEMS EN CAJAS
# ==============================
def cargar_items_caja(caja_id):
    try:
        supabase = get_supabase_client()
        resp = supabase.table("items_caja").select("*").eq("caja_id", caja_id).order("id").execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            for col in ["nombre","descripcion"]:
                if col not in df.columns: df[col] = ""
            for col in ["cantidad","precio_unitario"]:
                if col not in df.columns: df[col] = 0
            return df
        return pd.DataFrame(columns=["id","caja_id","nombre","descripcion","cantidad","precio_unitario","serial_item"])
    except Exception as e:
        st.error(f"❌ Error cargando items: {e}")
        return pd.DataFrame(columns=["id","caja_id","nombre","descripcion","cantidad","precio_unitario","serial_item"])

def guardar_item_caja(caja_id, nombre, descripcion, cantidad, precio_unitario):
    try:
        supabase = get_supabase_client()
        serial_item = generar_serial("ITM")
        supabase.table("items_caja").insert({
            "caja_id": int(caja_id), 
            "nombre": nombre, 
            "descripcion": descripcion, 
            "cantidad": int(cantidad), 
            "precio_unitario": int(precio_unitario),
            "serial_item": serial_item
        }).execute()
        return True, serial_item
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False, None

def eliminar_item_caja(item_id):
    try:
        supabase = get_supabase_client()
        supabase.table("items_caja").delete().eq("id", item_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

def actualizar_item_caja(item_id, campos):
    try:
        supabase = get_supabase_client()
        supabase.table("items_caja").update(campos).eq("id", item_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

def calcular_valor_caja(items_df):
    """Calcula valor total de la caja basado en items"""
    if items_df.empty:
        return 0
    return int((items_df["cantidad"] * items_df["precio_unitario"]).sum())

# ==============================
# EQUIPOS
# ==============================
def cargar_equipos(asesor=None):
    try:
        supabase = get_supabase_client()
        query = supabase.table("equipos").select("*")
        if asesor: query = query.eq("Asesor_Asignado", asesor)
        resp = query.execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            for col in ["Nombre","Serial","Estado","Comentarios","Asesor_Asignado","Cliente_Asignado"]:
                if col not in df.columns: df[col] = ""
            if "Precio" not in df.columns: df["Precio"] = 0
            return df
        return pd.DataFrame(columns=["id","Nombre","Serial","Estado","Comentarios","Precio","Asesor_Asignado","Cliente_Asignado"])
    except Exception as e:
        st.error(f"❌ Error cargando equipos: {e}")
        return pd.DataFrame(columns=["id","Nombre","Serial","Estado","Comentarios","Precio","Asesor_Asignado","Cliente_Asignado"])

def guardar_equipo_nuevo(d):
    try:
        supabase = get_supabase_client()
        if not d.get("Serial"): d["Serial"] = generar_serial("EQ")
        supabase.table("equipos").insert(d).execute()
        return True, d["Serial"]
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False, None

def actualizar_equipo(equipo_id, campos):
    try:
        supabase = get_supabase_client()
        supabase.table("equipos").update(campos).eq("id", equipo_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

def eliminar_equipo(equipo_id):
    try:
        supabase = get_supabase_client()
        supabase.table("equipos").delete().eq("id", equipo_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

# ==============================
# BATERÍAS
# ==============================
def cargar_baterias():
    try:
        supabase = get_supabase_client()
        resp = supabase.table("baterias").select("*").execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            for col in ["nombre","serial","proveedor","estado","equipo_asignado","notas"]:
                if col not in df.columns: df[col] = ""
            for col in ["tiempo_uso_horas","costo"]:
                if col not in df.columns: df[col] = 0
            if "fecha_compra" not in df.columns: df["fecha_compra"] = None
            else: df["fecha_compra"] = pd.to_datetime(df["fecha_compra"], errors="coerce")
            return df
        return pd.DataFrame(columns=["id","nombre","serial","proveedor","fecha_compra","tiempo_uso_horas","costo","estado","equipo_asignado","notas"])
    except Exception as e:
        st.error(f"❌ Error cargando baterías: {e}")
        return pd.DataFrame(columns=["id","nombre","serial","proveedor","fecha_compra","tiempo_uso_horas","costo","estado","equipo_asignado","notas"])

def guardar_bateria(nombre, proveedor, fecha_compra, tiempo_uso_horas, costo, estado, equipo_asignado, notas, serial_manual=""):
    try:
        supabase = get_supabase_client()
        serial = serial_manual if serial_manual else generar_serial("BAT")
        supabase.table("baterias").insert({
            "nombre": nombre, "serial": serial, "proveedor": proveedor,
            "fecha_compra": fecha_compra.strftime("%Y-%m-%d"),
            "tiempo_uso_horas": int(tiempo_uso_horas), "costo": int(costo),
            "estado": estado, "equipo_asignado": equipo_asignado, "notas": notas
        }).execute()
        return True, serial
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False, None

def actualizar_bateria(bat_id, campos):
    try:
        supabase = get_supabase_client()
        supabase.table("baterias").update(campos).eq("id", bat_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

def eliminar_bateria(bat_id):
    try:
        supabase = get_supabase_client()
        supabase.table("baterias").delete().eq("id", bat_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

# ==============================
# HISTORIAL
# ==============================
def registrar_historial_asignacion(asesor, caja, cantidad, tipo, nota=""):
    try:
        supabase = get_supabase_client()
        supabase.table("historial_asignaciones").insert({
            "asesor": asesor, "caja": caja, "cantidad": int(cantidad),
            "tipo": tipo, "nota": nota,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
    except Exception as e:
        st.warning(f"⚠️ No se pudo registrar historial: {e}")

def cargar_historial_asignaciones(asesor=None, caja=None):
    try:
        supabase = get_supabase_client()
        query = supabase.table("historial_asignaciones").select("*")
        if asesor: query = query.eq("asesor", asesor)
        if caja: query = query.eq("caja", caja)
        resp = query.order("fecha", desc=True).execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
            for col in ["asesor","caja","tipo","nota"]:
                if col not in df.columns: df[col] = ""
            if "cantidad" not in df.columns: df["cantidad"] = 0
            return df
        return pd.DataFrame(columns=["id","asesor","caja","cantidad","tipo","nota","fecha"])
    except Exception as e:
        st.error(f"❌ Error cargando historial: {e}")
        return pd.DataFrame(columns=["id","asesor","caja","cantidad","tipo","nota","fecha"])

# ==============================
# ASIGNACIONES
# ==============================
def cargar_asignaciones(asesor=None):
    try:
        supabase = get_supabase_client()
        query = supabase.table("asignaciones").select("*")
        if asesor: query = query.eq("asesor", asesor)
        resp = query.execute()
        if resp.data: return pd.DataFrame(resp.data)
        return pd.DataFrame(columns=["id","asesor","caja","cantidad","fecha"])
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return pd.DataFrame(columns=["id","asesor","caja","cantidad","fecha"])

def guardar_asignacion(asesor, caja, cantidad, fecha):
    try:
        supabase = get_supabase_client()
        supabase.table("asignaciones").insert({"asesor": asesor, "caja": caja, "cantidad": int(cantidad), "fecha": fecha.strftime("%Y-%m-%d")}).execute()
        registrar_historial_asignacion(asesor, caja, cantidad, "asignacion", f"Asignación de {cantidad} uds de '{caja}' a {asesor}")
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

# ==============================
# VENTAS
# ==============================
def cargar_ventas(asesor=None):
    try:
        supabase = get_supabase_client()
        query = supabase.table("ventas").select("*")
        if asesor: query = query.eq("asesor", asesor)
        resp = query.execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            if "fecha" in df.columns: df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
            for col in ["cliente","caja","asesor"]:
                if col not in df.columns: df[col] = ""
            for col in ["cantidad","valor_unitario","monto"]:
                if col not in df.columns: df[col] = 0
            if "es_credito" not in df.columns: df["es_credito"] = False
            return df
        return pd.DataFrame(columns=["id","fecha","cliente","caja","cantidad","valor_unitario","monto","es_credito","asesor"])
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return pd.DataFrame(columns=["id","fecha","cliente","caja","cantidad","valor_unitario","monto","es_credito","asesor"])

def guardar_venta(fecha, cliente, caja, cantidad, valor_unitario, monto, es_credito, asesor):
    try:
        supabase = get_supabase_client()
        supabase.table("ventas").insert({
            "fecha": fecha.strftime("%Y-%m-%d"), 
            "cliente": cliente, 
            "caja": caja, 
            "cantidad": int(cantidad), 
            "valor_unitario": int(valor_unitario), 
            "monto": int(monto),
            "es_credito": es_credito,
            "asesor": asesor
        }).execute()
        registrar_historial_asignacion(asesor, caja, cantidad, "venta", f"Venta de {cantidad} uds a cliente '{cliente}'")
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

def eliminar_venta(venta_id):
    try:
        supabase = get_supabase_client()
        supabase.table("ventas").delete().eq("id", venta_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

# ==============================
# CRÉDITOS
# ==============================
def cargar_creditos(asesor=None):
    try:
        supabase = get_supabase_client()
        query = supabase.table("creditos").select("*")
        if asesor: query = query.eq("asesor", asesor)
        resp = query.execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            for col in ["fecha_credito","fecha_pago"]:
                if col in df.columns: df[col] = pd.to_datetime(df[col], errors="coerce")
            if "pagado" not in df.columns: df["pagado"] = False
            for col in ["cliente","asesor"]:
                if col not in df.columns: df[col] = ""
            if "monto" not in df.columns: df["monto"] = 0
            return df
        return pd.DataFrame(columns=["id","cliente","monto","fecha_credito","pagado","fecha_pago","asesor"])
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return pd.DataFrame(columns=["id","cliente","monto","fecha_credito","pagado","fecha_pago","asesor"])

def guardar_credito(cliente, monto, fecha, asesor):
    try:
        supabase = get_supabase_client()
        supabase.table("creditos").insert({"cliente": cliente, "monto": int(monto), "fecha_credito": fecha.strftime("%Y-%m-%d"), "pagado": False, "asesor": asesor}).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

def marcar_credito_pagado(credito_id):
    try:
        supabase = get_supabase_client()
        supabase.table("creditos").update({"pagado": True, "fecha_pago": datetime.now().strftime("%Y-%m-%d")}).eq("id", credito_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}"); return False

# ==============================
# SESIÓN
# ==============================
for k, v in [("authenticated", False), ("usuario", None), ("rol", None), ("nombre_usuario", None)]:
    if k not in st.session_state: st.session_state[k] = v

# ==============================
# LOGIN
# ==============================
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("# 🏥 Surtidor Médico")
        st.markdown("### Sistema de Gestión de Inventario")
        st.markdown("---")
        usuario = st.text_input("👤 Usuario", placeholder="Ingresa tu usuario")
        contraseña = st.text_input("🔑 Contraseña", type="password", placeholder="Ingresa tu contraseña")
        ca, cb = st.columns(2)
        with ca:
            if st.button("✅ Iniciar Sesión", use_container_width=True):
                ok, rol, nombre = verificar_usuario(usuario, contraseña)
                if ok:
                    st.session_state.authenticated = True
                    st.session_state.usuario = usuario
                    st.session_state.rol = rol
                    st.session_state.nombre_usuario = nombre
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
        with cb:
            if st.button("❌ Salir", use_container_width=True): 
                st.info("👋 Hasta luego")
        st.markdown("---")

else:
    ROL = st.session_state.rol
    USUARIO = st.session_state.usuario
    NOMBRE = st.session_state.nombre_usuario

    # SIDEBAR
    with st.sidebar:
        st.title(f"👤 {NOMBRE}")
        st.caption(f"{'🔑 Administrador' if ROL == 'admin' else '🧑‍💼 Asesor'}")
        st.markdown(f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            for k in ["authenticated","usuario","rol","nombre_usuario"]:
                st.session_state[k] = False if k == "authenticated" else None
            st.rerun()
        st.markdown("---")

        if ROL == "admin":
            menu = st.radio("📋 MENÚ", [
                "📊 Dashboard", "👥 Clientes", "📦 Insumos (Cajas)",
                "🖥️ Equipos", "🔋 Baterías", "📋 Asignaciones",
                "🛒 Ventas", "💳 Créditos", "📜 Historial", "📈 Reportes"
            ])
        else:
            menu = st.radio("📋 MENÚ", [
                "📊 Mi Resumen", "👥 Mis Clientes", "📦 Mis Insumos",
                "🖥️ Mis Equipos", "🛒 Registrar Venta", "💳 Mis Créditos"
            ])

    # ============================================================
    # ADMIN - DASHBOARD
    # ============================================================
    if menu == "📊 Dashboard" and ROL == "admin":
        st.title("📊 PANEL DE CONTROL")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1: st.metric("👥 CLIENTES", len(get_cached_clientes()))
        with col2: st.metric("📦 CAJAS", len(get_cached_inventario()))
        with col3: 
            ventas = cargar_ventas()
            st.metric("💳 VENTAS", f"${ventas['monto'].sum():,.0f}" if not ventas.empty else "$0")
        with col4:
            creditos = cargar_creditos()
            cred_pend = creditos[creditos["pagado"] == False]["monto"].sum() if not creditos.empty else 0
            st.metric("⚠️ PENDIENTE", f"${cred_pend:,.0f}")
        with col5:
            baterias = cargar_baterias()
            st.metric("🔋 BATERÍAS", len(baterias[baterias["estado"] == "Disponible"]) if not baterias.empty else 0)
        
        st.markdown("---")
        st.subheader("🔍 BUSCAR POR SERIAL")
        serial_buscar = st.text_input("Ingresa serial", placeholder="EQ-XXXXX / INS-XXXXX / BAT-XXXXX")
        
        if st.button("🔍 Buscar", use_container_width=True):
            if serial_buscar:
                resultado = buscar_por_serial(serial_buscar.strip().upper())
                if resultado["equipo"]:
                    eq = resultado["equipo"]
                    st.success("✅ Equipo encontrado")
                    st.write(f"🖥️ **{eq.get('Nombre','')}** | {eq.get('Serial','')} | {eq.get('Estado','')}")
                elif resultado["insumo"]:
                    inv = resultado["insumo"]
                    st.success("✅ Insumo encontrado")
                    st.write(f"📦 **{inv.get('Caja','')}** | ${int(inv.get('Cantidad',0))}")
                elif resultado["bateria"]:
                    bat = resultado["bateria"]
                    st.success("✅ Batería encontrada")
                    st.write(f"🔋 **{bat.get('nombre','')}** | {bat.get('serial','')}")
                else:
                    st.warning(f"⚠️ No encontrado: **{serial_buscar}**")

        st.markdown("---")
        if not ventas.empty:
            st.subheader("📊 Últimas Ventas")
            vd = ventas.tail(10)[["fecha","asesor","cliente","caja","cantidad","monto"]].copy()
            vd["fecha"] = pd.to_datetime(vd["fecha"], errors="coerce").dt.strftime("%d/%m")
            vd["monto"] = vd["monto"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(vd, use_container_width=True, hide_index=True)

    # ADMIN - CLIENTES
    elif menu == "👥 Clientes" and ROL == "admin":
        st.title("👥 CLIENTES")
        clientes = get_cached_clientes(); asesores = get_cached_asesores()
        
        tab1, tab2 = st.tabs(["📋 Ver", "➕ Agregar"])
        
        with tab1:
            if not clientes.empty:
                st.dataframe(clientes[["nombre","cedula","telefono","asesor"]], use_container_width=True, hide_index=True)
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    sel = st.selectbox("Selecciona cliente para eliminar", clientes["nombre"].tolist())
                with col2:
                    if st.button("🗑️ Eliminar", use_container_width=True):
                        if eliminar_cliente(int(clientes[clientes["nombre"]==sel].iloc[0]["id"])): 
                            st.success("✅ Eliminado"); st.cache_data.clear(); st.rerun()
            else: 
                st.info("📭 Sin clientes")
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre")
                telefono = st.text_input("Teléfono")
            with col2:
                cedula = st.text_input("Cédula")
                asesor_sel = st.selectbox("Asesor", asesores)
            
            if st.button("💾 Guardar", use_container_width=True):
                if nombre and cedula:
                    if guardar_cliente(nombre, cedula, telefono, asesor_sel): 
                        st.success("✅ Agregado"); st.cache_data.clear(); st.rerun()
                else: 
                    st.error("❌ Completa nombre y cédula")

    # ADMIN - INSUMOS (CAJAS)
    elif menu == "📦 Insumos (Cajas)" and ROL == "admin":
        st.title("📦 CAJAS E ITEMS")
        inventario = get_cached_inventario()
        
        tab1, tab2, tab3 = st.tabs(["📋 Ver Cajas", "➕ Nueva Caja", "📝 Gestionar Items"])
        
        with tab1:
            if not inventario.empty:
                for idx, row in inventario.iterrows():
                    items = cargar_items_caja(int(row["id"]))
                    valor_total = calcular_valor_caja(items)
                    
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"### 📦 {row['Caja']}")
                    with col2:
                        st.metric("Items", len(items))
                    with col3:
                        if st.button("🗑️", key=f"del_caja_{row['id']}", use_container_width=True):
                            if eliminar_caja(int(row["id"])): 
                                st.success("✅"); st.cache_data.clear(); st.rerun()
                    
                    if not items.empty:
                        st.write(f"💰 **Valor Total:** ${valor_total:,.0f}")
                        item_display = items[["nombre", "cantidad", "precio_unitario"]].copy()
                        item_display["subtotal"] = (items["cantidad"] * items["precio_unitario"]).apply(lambda x: f"${x:,.0f}")
                        item_display["cantidad"] = item_display["cantidad"].apply(lambda x: f"{x} uds")
                        item_display["precio_unitario"] = item_display["precio_unitario"].apply(lambda x: f"${x:,.0f}")
                        st.dataframe(item_display, use_container_width=True, hide_index=True)
                    else:
                        st.info("ℹ️ Sin items")
                    st.divider()
            else: 
                st.info("📭 Sin cajas")
        
        with tab2:
            caja_nombre = st.text_input("Nombre de la Caja", placeholder="Ej: Jeringas 10ml")
            if st.button("💾 Crear Caja", use_container_width=True):
                if caja_nombre:
                    ok, serial = guardar_caja_nueva(caja_nombre)
                    if ok: 
                        st.success(f"✅ Caja '{caja_nombre}' creada")
                        st.info(f"📋 Serial: `{serial}`")
                        st.cache_data.clear(); st.rerun()
                else: 
                    st.error("❌ Ingresa nombre de caja")
        
        with tab3:
            st.subheader("📝 Agregar / Editar Items en Caja")
            if not inventario.empty:
                caja_sel = st.selectbox("Selecciona Caja", inventario["Caja"].tolist())
                caja_id = int(inventario[inventario["Caja"]==caja_sel].iloc[0]["id"])
                items = cargar_items_caja(caja_id)
                
                st.markdown("---")
                
                if not items.empty:
                    st.markdown("**📋 Items Actuales:**")
                    for _, item in items.iterrows():
                        col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 0.8, 1.2, 1, 0.8])
                        with col1: 
                            st.write(f"**{item['nombre']}**")
                        with col2: 
                            st.write(f"{item['descripcion']}")
                        with col3: 
                            st.write(f"x{int(item['cantidad'])}")
                        with col4:
                            nuevo_precio = st.number_input(
                                f"Precio {item['nombre']}", 
                                value=int(item['precio_unitario']), 
                                step=100,
                                key=f"edit_price_{item['id']}"
                            )
                            if nuevo_precio != int(item['precio_unitario']):
                                if actualizar_item_caja(int(item["id"]), {"precio_unitario": nuevo_precio}):
                                    st.success("✅")
                        with col5: 
                            st.write(f"${int(item['cantidad'] * item['precio_unitario']):,.0f}")
                        with col6:
                            if st.button("🗑️", key=f"del_item_{item['id']}", use_container_width=True):
                                if eliminar_item_caja(int(item["id"])): 
                                    st.success("✅"); st.rerun()
                    st.markdown("---")
                
                st.markdown("**➕ Nuevo Item:**")
                col1, col2 = st.columns(2)
                with col1:
                    item_nombre = st.text_input("Nombre Item", placeholder="Jeringa", key=f"item_nom_{caja_id}")
                    item_cantidad = st.number_input("Cantidad", min_value=1, value=1, key=f"item_cant_{caja_id}")
                with col2:
                    item_desc = st.text_input("Descripción", placeholder="10ml Luer Lock", key=f"item_desc_{caja_id}")
                    item_precio = st.number_input("Precio Unitario ($)", min_value=0, value=1000, step=100, key=f"item_precio_{caja_id}")
                
                if st.button("💾 Agregar Item", use_container_width=True):
                    if item_nombre and item_precio > 0:
                        ok, serial = guardar_item_caja(caja_id, item_nombre, item_desc, item_cantidad, item_precio)
                        if ok: 
                            st.success(f"✅ Item agregado")
                            st.rerun()
                    else: 
                        st.error("❌ Completa nombre y precio")
            else:
                st.warning("⚠️ Crea una caja primero")

    # ADMIN - EQUIPOS
    elif menu == "🖥️ Equipos" and ROL == "admin":
        st.title("🖥️ EQUIPOS")
        equipos = cargar_equipos(); asesores = get_cached_asesores()
        
        tab1, tab2 = st.tabs(["📋 Ver", "➕ Agregar"])
        
        with tab1:
            if not equipos.empty:
                for _, row in equipos.iterrows():
                    with st.expander(f"{COLOR_ESTADO.get(row['Estado'],'⚪')} {row['Nombre']} | {row['Serial']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"💰 ${int(row.get('Precio',0)):,.0f}")
                            st.write(f"🧑‍💼 {row.get('Asesor_Asignado','')}")
                        with col2:
                            st.write(f"👤 {row.get('Cliente_Asignado','')}")
                        
                        idx_e = ESTADOS_EQUIPO.index(row["Estado"]) if row["Estado"] in ESTADOS_EQUIPO else 0
                        ne = st.selectbox("Estado", ESTADOS_EQUIPO, index=idx_e, key=f"e_{row['id']}")
                        
                        oa = [""]+asesores
                        ia = oa.index(row.get("Asesor_Asignado","")) if row.get("Asesor_Asignado","") in oa else 0
                        na = st.selectbox("Asesor", oa, index=ia, key=f"a_{row['id']}")
                        
                        nc = st.text_input("Comentario", value=str(row.get("Comentarios","")), key=f"c_{row['id']}")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("💾 Actualizar", key=f"u_{row['id']}", use_container_width=True):
                                if actualizar_equipo(int(row["id"]), {"Estado":ne,"Asesor_Asignado":na,"Comentarios":nc}): 
                                    st.success("✅"); st.rerun()
                        with col_b:
                            if st.button("🗑️ Eliminar", key=f"d_{row['id']}", use_container_width=True):
                                if eliminar_equipo(int(row["id"])): 
                                    st.success("✅"); st.rerun()
            else: 
                st.info("📭 Sin equipos")
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                ne2 = st.text_input("Nombre del equipo")
                se2 = st.text_input("Serial / Código")
            with col2:
                pe2 = st.number_input("Precio ($)", min_value=0, value=0, step=1000)
                ee2 = st.selectbox("Estado inicial", ESTADOS_EQUIPO)
            
            ae2 = st.selectbox("Asesor asignado", [""] + asesores)
            ce2 = st.text_input("Cliente (opcional)")
            
            if st.button("💾 Agregar Equipo", use_container_width=True):
                if ne2:
                    sf = se2 if se2 else generar_serial("EQ")
                    ok, sr = guardar_equipo_nuevo({"Nombre":ne2,"Serial":sf,"Estado":ee2,"Precio":int(pe2),"Asesor_Asignado":ae2,"Cliente_Asignado":ce2})
                    if ok: 
                        st.success(f"✅ Equipo agregado"); 
                        st.info(f"📋 Serial: `{sr}`")
                        st.rerun()
                else: 
                    st.error("❌ Ingresa nombre")

    # ADMIN - BATERÍAS
    elif menu == "🔋 Baterías" and ROL == "admin":
        st.title("🔋 BATERÍAS")
        baterias = cargar_baterias(); equipos_lista = cargar_equipos()
        
        if not baterias.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("🔋 Total", len(baterias))
            with col2: st.metric("🟢 Disponibles", len(baterias[baterias["estado"]=="Disponible"]))
            with col3: st.metric("🔵 En Uso", len(baterias[baterias["estado"]=="En uso"]))
            with col4: st.metric("🔴 Dañadas", len(baterias[baterias["estado"]=="Dañada"]))
            st.markdown("---")
        
        tab1, tab2, tab3 = st.tabs(["📋 Ver", "➕ Agregar", "📊 Estadísticas"])
        
        with tab1:
            if not baterias.empty:
                fb_est = st.selectbox("Filtrar estado", ["Todos"]+ESTADOS_BATERIA)
                bf = baterias.copy() if fb_est == "Todos" else baterias[baterias["estado"]==fb_est]
                
                for _, row in bf.iterrows():
                    eb = row.get("estado","")
                    with st.expander(f"{COLOR_BATERIA.get(eb,'⚪')} {row['nombre']} | {row['serial']}"):
                        st.write(f"🏭 **Proveedor:** {row.get('proveedor','')}")
                        st.write(f"💰 **Costo:** ${int(row.get('costo',0)):,.0f}")
                        
                        idx_eb = ESTADOS_BATERIA.index(eb) if eb in ESTADOS_BATERIA else 0
                        neb = st.selectbox("Estado", ESTADOS_BATERIA, index=idx_eb, key=f"bst_{row['id']}")
                        
                        if st.button("💾 Actualizar", key=f"bupd_{row['id']}", use_container_width=True):
                            if actualizar_bateria(int(row["id"]), {"estado":neb}): 
                                st.success("✅"); st.rerun()
            else: 
                st.info("📭 Sin baterías")
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                nb_nombre = st.text_input("Nombre / Modelo")
                nb_proveedor = st.text_input("Proveedor")
            with col2:
                nb_costo = st.number_input("Costo ($)", min_value=0, value=0, step=1000)
                nb_estado = st.selectbox("Estado", ESTADOS_BATERIA)
            
            if st.button("💾 Registrar", use_container_width=True):
                if nb_nombre and nb_proveedor:
                    ok, sb = guardar_bateria(nb_nombre, nb_proveedor, datetime.now().date(), 0, nb_costo, nb_estado, "", "", "")
                    if ok: 
                        st.success(f"✅ Batería registrada"); 
                        st.info(f"📋 Serial: `{sb}`")
                        st.rerun()
                else: 
                    st.error("❌ Completa todos")
        
        with tab3:
            if not baterias.empty:
                st.subheader("📊 Distribución")
                est_c = baterias["estado"].value_counts()
                fig = px.pie(values=est_c.values, names=est_c.index)
                st.plotly_chart(fig, use_container_width=True)

    # ADMIN - ASIGNACIONES
    elif menu == "📋 Asignaciones" and ROL == "admin":
        st.title("📋 ASIGNACIONES")
        asesores = get_cached_asesores(); inventario = get_cached_inventario()
        
        tab1, tab2 = st.tabs(["📋 Ver", "➕ Nueva"])
        
        with tab1:
            asignaciones = cargar_asignaciones()
            if not asignaciones.empty:
                for asesor in asesores:
                    asig = asignaciones[asignaciones["asesor"]==asesor]
                    if not asig.empty:
                        with st.expander(f"🧑‍💼 {asesor} — {int(asig['cantidad'].sum())} uds"):
                            for _, arow in asig.iterrows():
                                st.markdown(f"📦 **{arow['caja']}** | {int(arow['cantidad'])} uds")
                                if st.button("🗑️ Eliminar", key=f"del_asig_{arow['id']}", use_container_width=True):
                                    try:
                                        supabase = get_supabase_client()
                                        supabase.table("asignaciones").delete().eq("id",int(arow["id"])).execute()
                                        st.success("✅"); st.rerun()
                                    except Exception as e: 
                                        st.error(f"❌ {e}")
            else: 
                st.info("📭 Sin asignaciones")
        
        with tab2:
            if not inventario.empty:
                col1, col2, col3 = st.columns(3)
                with col1: ad = st.selectbox("Asesor", asesores)
                with col2: cs = st.selectbox("Caja", inventario["Caja"].tolist())
                with col3:
                    disp = int(inventario[inventario["Caja"]==cs].iloc[0]["Cantidad"])
                    st.metric("Disponible", disp)
                
                ca2 = st.number_input("Cantidad", min_value=1, max_value=max(disp, 1), value=1)
                fa2 = st.date_input("Fecha")
                
                if st.button("📋 Asignar", use_container_width=True):
                    if ca2 <= disp:
                        row_c = inventario[inventario["Caja"]==cs].iloc[0]
                        actualizar_caja(int(row_c["id"]), {"Cantidad":disp-ca2})
                        if guardar_asignacion(ad, cs, ca2, fa2): 
                            st.success("✅"); st.rerun()
                    else: 
                        st.error("❌ Stock insuficiente")
            else: 
                st.error("❌ Sin cajas")

    # ADMIN - VENTAS
    elif menu == "🛒 Ventas" and ROL == "admin":
        st.title("🛒 VENTAS")
        inventario = get_cached_inventario(); clientes = get_cached_clientes(); asesores = get_cached_asesores()
        
        tab1, tab2 = st.tabs(["➕ Nueva", "📋 Historial"])
        
        with tab1:
            col1, col2 = st.columns(2)
            with col1: fecha = st.date_input("Fecha")
            with col2: av = st.selectbox("Asesor", asesores)
            
            cli_f = clientes[clientes["asesor"]==av] if not clientes.empty else pd.DataFrame()
            lcli = cli_f["nombre"].tolist() if not cli_f.empty else []
            cv = st.selectbox("Cliente", lcli if lcli else ["Sin clientes"])
            
            col3, col4 = st.columns(2)
            with col3: cajav = st.selectbox("Caja", inventario["Caja"].tolist() if not inventario.empty else ["Sin cajas"])
            with col4:
                if not inventario.empty and cajav != "Sin cajas": 
                    st.metric("Disponible", int(inventario[inventario["Caja"]==cajav].iloc[0]["Cantidad"]))
            
            col5, col6 = st.columns(2)
            with col5: cantv = st.number_input("Cantidad", min_value=1, value=1)
            with col6:
                valu = 0
                if not inventario.empty and cajav!="Sin cajas":
                    caja_id = int(inventario[inventario["Caja"]==cajav].iloc[0]["id"])
                    items = cargar_items_caja(caja_id)
                    valu = int((items["precio_unitario"].mean())) if not items.empty else 0
                st.metric("Precio Unitario", f"${valu:,.0f}")
            
            montov = cantv * valu
            st.metric("Monto Total", f"${montov:,.0f}")
            ecv = st.checkbox("Venta a Crédito")
            
            if st.button("💾 Guardar Venta", use_container_width=True):
                if cv != "Sin clientes" and cajav != "Sin cajas":
                    crow = inventario[inventario["Caja"]==cajav].iloc[0]
                    nc = int(crow["Cantidad"])-cantv
                    if nc < 0: 
                        st.error("❌ Stock insuficiente")
                    else:
                        actualizar_caja(int(crow["id"]), {"Cantidad":nc})
                        guardar_venta(fecha, cv, cajav, cantv, valu, montov, ecv, av)
                        if ecv: 
                            guardar_credito(cv, montov, fecha, av)
                        st.success("✅ Venta guardada"); st.rerun()
                else: 
                    st.error("❌ Completa campos")
        
        with tab2:
            ventas = cargar_ventas()
            if not ventas.empty:
                vd = ventas[["fecha","asesor","cliente","cantidad","monto"]].copy()
                vd["fecha"] = pd.to_datetime(vd["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")
                vd["monto"] = vd["monto"].apply(lambda x: f"${x:,.0f}")
                st.dataframe(vd, use_container_width=True, hide_index=True)
            else: 
                st.info("📭 Sin ventas")

    # ADMIN - CRÉDITOS
    elif menu == "💳 Créditos" and ROL == "admin":
        st.title("💳 CRÉDITOS")
        creditos = cargar_creditos(); asesores_cred = get_cached_asesores()
        
        if not creditos.empty:
            pend = creditos[creditos["pagado"]==False]
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("💳 PENDIENTE", f"${pend['monto'].sum():,.0f}")
            with col2: st.metric("👥 CLIENTES", pend["cliente"].nunique())
            with col3: st.metric("📋 REGISTROS", len(pend))
            
            st.markdown("---")
            filtro_ac = st.selectbox("Filtrar por asesor", ["Todos"]+asesores_cred)
            
            for ac in (asesores_cred if filtro_ac=="Todos" else [filtro_ac]):
                ca = creditos[creditos["asesor"]==ac]
                if ca.empty: continue
                
                with st.expander(f"🧑‍💼 {ac}"):
                    for _, row in ca.iterrows():
                        col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1])
                        with col1: st.write(f"👤 {row['cliente']}")
                        with col2: st.write(f"💰 ${int(row['monto']):,.0f}")
                        with col3:
                            fc = row["fecha_credito"].strftime("%d/%m/%Y") if pd.notna(row["fecha_credito"]) else ""
                            st.write(f"📅 {fc}")
                        with col4:
                            if not row["pagado"]:
                                if st.button("✓", key=f"p_{row['id']}", use_container_width=True):
                                    if marcar_credito_pagado(int(row["id"])): 
                                        st.success("✅"); st.rerun()
        else: 
            st.info("✅ Sin créditos")

    # ADMIN - HISTORIAL
    elif menu == "📜 Historial" and ROL == "admin":
        st.title("📜 HISTORIAL")
        historial = cargar_historial_asignaciones()
        
        if not historial.empty:
            st.metric("Total registros", len(historial))
            st.dataframe(historial[["fecha","asesor","tipo","cantidad"]].tail(20), use_container_width=True, hide_index=True)
        else: 
            st.info("📭 Sin registros")

    # ADMIN - REPORTES
    elif menu == "📈 Reportes" and ROL == "admin":
        st.title("📈 REPORTES")
        ventas = cargar_ventas()
        
        if not ventas.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Ventas Totales", f"${ventas['monto'].sum():,.0f}")
            with col2:
                st.metric("Número de Ventas", len(ventas))
            
            st.markdown("---")
            st.subheader("Ventas por Asesor")
            va = ventas.groupby("asesor")["monto"].sum().reset_index()
            fig = px.bar(va, x="asesor", y="monto", color="monto", color_continuous_scale="Teal")
            st.plotly_chart(fig, use_container_width=True)

    # ============================================================
    # ASESOR - MI RESUMEN
    # ============================================================
    elif menu == "📊 Mi Resumen" and ROL == "asesor":
        st.title(f"📊 MI RESUMEN")
        
        mv = cargar_ventas(asesor=USUARIO)
        mc = cargar_creditos(asesor=USUARIO)
        mcli = cargar_clientes(asesor=USUARIO)
        pend = mc[mc["pagado"]==False] if not mc.empty else pd.DataFrame()
        
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("👥 MIS CLIENTES", len(mcli))
        with col2: st.metric("💳 MIS VENTAS", f"${mv['monto'].sum():,.0f}" if not mv.empty else "$0")
        with col3: st.metric("⚠️ PENDIENTE", f"${pend['monto'].sum():,.0f}" if not pend.empty else "$0")

    # ASESOR - MIS CLIENTES
    elif menu == "👥 Mis Clientes" and ROL == "asesor":
        st.title("👥 MIS CLIENTES")
        mc = cargar_clientes(asesor=USUARIO)
        
        tab1, tab2 = st.tabs(["📋 Ver", "➕ Agregar"])
        
        with tab1:
            if not mc.empty: 
                st.dataframe(mc[["nombre","cedula","telefono"]], use_container_width=True, hide_index=True)
            else: 
                st.info("📭 Sin clientes")
        
        with tab2:
            nombre = st.text_input("Nombre")
            col1, col2 = st.columns(2)
            with col1: cedula = st.text_input("Cédula")
            with col2: telefono = st.text_input("Teléfono")
            
            if st.button("💾 Guardar", use_container_width=True):
                if nombre and cedula:
                    if guardar_cliente(nombre, cedula, telefono, USUARIO): 
                        st.success("✅"); st.rerun()
                else: 
                    st.error("❌ Completa campos")

    # ASESOR - MIS INSUMOS
    elif menu == "📦 Mis Insumos" and ROL == "asesor":
        st.title("📦 MIS INSUMOS")
        ma = cargar_asignaciones(asesor=USUARIO)
        
        if not ma.empty:
            st.metric("Total unidades", int(ma["cantidad"].sum()))
            st.dataframe(ma[["caja","cantidad","fecha"]], use_container_width=True, hide_index=True)
        else: 
            st.info("📭 Sin insumos")

    # ASESOR - MIS EQUIPOS
    elif menu == "🖥️ Mis Equipos" and ROL == "asesor":
        st.title("🖥️ MIS EQUIPOS")
        me = cargar_equipos(asesor=USUARIO)
        
        if not me.empty:
            for _, row in me.iterrows():
                with st.expander(f"{COLOR_ESTADO.get(row['Estado'],'⚪')} {row['Nombre']}"):
                    st.write(f"💰 ${int(row.get('Precio',0)):,.0f}")
                    st.write(f"👤 {row.get('Cliente_Asignado','')}")
        else: 
            st.info("📭 Sin equipos")

    # ASESOR - REGISTRAR VENTA
    elif menu == "🛒 Registrar Venta" and ROL == "asesor":
        st.title("🛒 REGISTRAR VENTA")
        
        mcli = cargar_clientes(asesor=USUARIO)
        ma = cargar_asignaciones(asesor=USUARIO)
        inventario = get_cached_inventario()
        
        col1, col2 = st.columns(2)
        with col1: fecha = st.date_input("Fecha")
        with col2:
            lcli = mcli["nombre"].tolist() if not mcli.empty else []
            cv = st.selectbox("Cliente", lcli if lcli else ["Sin clientes"])
        
        cajas_d = ma["caja"].unique().tolist() if not ma.empty else []
        col3, col4 = st.columns(2)
        with col3: cajav = st.selectbox("Caja", cajas_d if cajas_d else ["Sin cajas"])
        with col4:
            if cajas_d and not inventario.empty and cajav in inventario["Caja"].values:
                st.metric("Stock", int(inventario[inventario["Caja"]==cajav].iloc[0]["Cantidad"]))
        
        col5, col6 = st.columns(2)
        with col5: cantv = st.number_input("Cantidad", min_value=1, value=1)
        with col6:
            valu = 0
            if cajas_d and not inventario.empty and cajav in inventario["Caja"].values:
                caja_id = int(inventario[inventario["Caja"]==cajav].iloc[0]["id"])
                items = cargar_items_caja(caja_id)
                valu = int((items["precio_unitario"].mean())) if not items.empty else 0
            st.metric("Precio", f"${valu:,.0f}")
        
        montov = cantv * valu
        st.metric("Total", f"${montov:,.0f}")
        ecv = st.checkbox("Venta a Crédito")
        
        if st.button("💾 Guardar", use_container_width=True):
            if cv != "Sin clientes" and cajav != "Sin cajas":
                crow = inventario[inventario["Caja"]==cajav].iloc[0]
                nc = int(crow["Cantidad"]) - cantv
                if nc < 0: 
                    st.error("❌ Stock insuficiente")
                else:
                    actualizar_caja(int(crow["id"]), {"Cantidad":nc})
                    guardar_venta(fecha, cv, cajav, cantv, valu, montov, ecv, USUARIO)
                    if ecv: 
                        guardar_credito(cv, montov, fecha, USUARIO)
                    st.success("✅ Venta registrada"); st.rerun()
            else: 
                st.error("❌ Completa campos")

    # ASESOR - MIS CRÉDITOS
    elif menu == "💳 Mis Créditos" and ROL == "asesor":
        st.title("💳 MIS CRÉDITOS")
        mc = cargar_creditos(asesor=USUARIO)
        
        if not mc.empty:
            pend = mc[mc["pagado"]==False]
            col1, col2 = st.columns(2)
            with col1: st.metric("PENDIENTE", f"${pend['monto'].sum():,.0f}" if not pend.empty else "$0")
            with col2: st.metric("REGISTROS", len(pend))
            
            for _, row in mc.iterrows():
                col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1])
                with col1: st.write(f"👤 {row['cliente']}")
                with col2: st.write(f"💰 ${int(row['monto']):,.0f}")
                with col3:
                    fc = row["fecha_credito"].strftime("%d/%m/%Y") if pd.notna(row["fecha_credito"]) else ""
                    st.write(f"📅 {fc}")
                with col4:
                    if not row["pagado"]:
                        if st.button("✓", key=f"pa_{row['id']}", use_container_width=True):
                            if marcar_credito_pagado(int(row["id"])): 
                                st.success("✅"); st.rerun()
        else: 
            st.info("✅ Sin créditos")