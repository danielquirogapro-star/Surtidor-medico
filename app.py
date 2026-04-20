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

@st.cache_resource
def get_supabase_client():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

ESTADOS_EQUIPO = ["Recién ingresado", "En proceso de venta", "Listo para vender", "Pendiente por repuesto"]
COLOR_ESTADO = {"Recién ingresado": "🟡", "En proceso de venta": "🔵", "Listo para vender": "🟢", "Pendiente por repuesto": "🔴"}
ESTADOS_BATERIA = ["Disponible", "En uso", "Dañada", "En mantenimiento", "Baja de inventario"]
COLOR_BATERIA = {"Disponible": "🟢", "En uso": "🔵", "Dañada": "🔴", "En mantenimiento": "🟡", "Baja de inventario": "⚫"}

def generar_serial(prefijo="SM"):
    chars = string.ascii_uppercase + string.digits
    return f"{prefijo}-{''.join(random.choices(chars, k=6))}"

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
        st.error(f"Error buscando serial: {e}")
        return {"equipo": None, "insumo": None, "bateria": None}

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
        st.error(f"Error verificando usuario: {e}")
        return False, None, None

def obtener_asesores():
    try:
        supabase = get_supabase_client()
        resp = supabase.table("usuarios").select("usuario,nombre").eq("rol", "asesor").execute()
        return [r["usuario"] for r in (resp.data or [])]
    except: return []

def cargar_inventario():
    try:
        supabase = get_supabase_client()
        resp = supabase.table("inventario").select("*").execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            for col in ["Valor_Unitario", "Cantidad", "Cantidad_Total"]:
                if col not in df.columns: df[col] = 0
            return df
        return pd.DataFrame(columns=["id","Caja","Cantidad","Valor_Unitario","Cantidad_Total"])
    except Exception as e:
        st.error(f"Error cargando inventario: {e}")
        return pd.DataFrame(columns=["id","Caja","Cantidad","Valor_Unitario","Cantidad_Total"])

def guardar_caja_nueva(caja, cantidad, valor_unitario):
    try:
        supabase = get_supabase_client()
        serial = generar_serial("INS")
        supabase.table("inventario").insert({"Caja": caja, "Cantidad": int(cantidad), "Valor_Unitario": int(valor_unitario), "Cantidad_Total": int(cantidad), "serial": serial}).execute()
        return True, serial
    except Exception as e:
        st.error(f"Error: {e}"); return False, None

def actualizar_caja(caja_id, campos):
    try:
        supabase = get_supabase_client()
        supabase.table("inventario").update(campos).eq("id", caja_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}"); return False

def eliminar_caja(caja_id):
    try:
        supabase = get_supabase_client()
        supabase.table("inventario").delete().eq("id", caja_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}"); return False

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
        st.error(f"Error cargando equipos: {e}")
        return pd.DataFrame(columns=["id","Nombre","Serial","Estado","Comentarios","Precio","Asesor_Asignado","Cliente_Asignado"])

def guardar_equipo_nuevo(d):
    try:
        supabase = get_supabase_client()
        if not d.get("Serial"): d["Serial"] = generar_serial("EQ")
        supabase.table("equipos").insert(d).execute()
        return True, d["Serial"]
    except Exception as e:
        st.error(f"Error: {e}"); return False, None

def actualizar_equipo(equipo_id, campos):
    try:
        supabase = get_supabase_client()
        supabase.table("equipos").update(campos).eq("id", equipo_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}"); return False

def eliminar_equipo(equipo_id):
    try:
        supabase = get_supabase_client()
        supabase.table("equipos").delete().eq("id", equipo_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}"); return False

# ==============================
# BATERIAS
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
        st.error(f"Error cargando baterías: {e}")
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
        st.error(f"Error: {e}"); return False, None

def actualizar_bateria(bat_id, campos):
    try:
        supabase = get_supabase_client()
        supabase.table("baterias").update(campos).eq("id", bat_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}"); return False

def eliminar_bateria(bat_id):
    try:
        supabase = get_supabase_client()
        supabase.table("baterias").delete().eq("id", bat_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}"); return False

# ==============================
# HISTORIAL ASIGNACIONES
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
        st.warning(f"No se pudo registrar historial: {e}")

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
        st.error(f"Error cargando historial: {e}")
        return pd.DataFrame(columns=["id","asesor","caja","cantidad","tipo","nota","fecha"])

# ==============================
# CLIENTES
# ==============================
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
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=["id","nombre","cedula","telefono","direccion","asesor"])

def guardar_cliente(nombre, cedula, telefono, asesor):
    try:
        supabase = get_supabase_client()
        supabase.table("clientes").insert({"nombre": nombre, "cedula": cedula, "telefono": telefono, "asesor": asesor}).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}"); return False

def eliminar_cliente(cliente_id):
    try:
        supabase = get_supabase_client()
        supabase.table("clientes").delete().eq("id", cliente_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}"); return False

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
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=["id","asesor","caja","cantidad","fecha"])

def guardar_asignacion(asesor, caja, cantidad, fecha):
    try:
        supabase = get_supabase_client()
        supabase.table("asignaciones").insert({"asesor": asesor, "caja": caja, "cantidad": int(cantidad), "fecha": fecha.strftime("%Y-%m-%d")}).execute()
        registrar_historial_asignacion(asesor, caja, cantidad, "asignacion", f"Asignación de {cantidad} uds de '{caja}' a {asesor}")
        return True
    except Exception as e:
        st.error(f"Error: {e}"); return False

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
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=["id","fecha","cliente","caja","cantidad","valor_unitario","monto","es_credito","asesor"])

def guardar_venta(fecha, cliente, caja, cantidad, valor_unitario, monto, es_credito, asesor):
    try:
        supabase = get_supabase_client()
        supabase.table("ventas").insert({"fecha": fecha.strftime("%Y-%m-%d"), "cliente": cliente, "caja": caja, "cantidad": int(cantidad), "valor_unitario": int(valor_unitario), "monto": int(monto), "es_credito": bool(es_credito), "asesor": asesor}).execute()
        registrar_historial_asignacion(asesor, caja, cantidad, "venta", f"Venta de {cantidad} uds a cliente '{cliente}'")
        return True
    except Exception as e:
        st.error(f"Error: {e}"); return False

def eliminar_venta(venta_id):
    try:
        supabase = get_supabase_client()
        supabase.table("ventas").delete().eq("id", venta_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}"); return False

# ==============================
# CREDITOS
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
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=["id","cliente","monto","fecha_credito","pagado","fecha_pago","asesor"])

def guardar_credito(cliente, monto, fecha, asesor):
    try:
        supabase = get_supabase_client()
        supabase.table("creditos").insert({"cliente": cliente, "monto": int(monto), "fecha_credito": fecha.strftime("%Y-%m-%d"), "pagado": False, "asesor": asesor}).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}"); return False

def marcar_credito_pagado(credito_id):
    try:
        supabase = get_supabase_client()
        supabase.table("creditos").update({"pagado": True, "fecha_pago": datetime.now().strftime("%Y-%m-%d")}).eq("id", credito_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}"); return False

# ==============================
# SESION
# ==============================
for k, v in [("authenticated", False), ("usuario", None), ("rol", None), ("nombre_usuario", None)]:
    if k not in st.session_state: st.session_state[k] = v

# ==============================
# LOGIN
# ==============================
if not st.session_state.authenticated:
    st.title("🏥 Surtidor Médico")
    st.subheader("Sistema de Gestión de Inventario")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
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
            if st.button("❌ Salir", use_container_width=True): st.info("Hasta luego")
        st.markdown("---")

else:
    ROL = st.session_state.rol
    USUARIO = st.session_state.usuario
    NOMBRE = st.session_state.nombre_usuario

    st.sidebar.title(f"👤 {NOMBRE}")
    st.sidebar.caption(f"{'🔑 Administrador' if ROL == 'admin' else '🧑‍💼 Asesor'}")
    st.sidebar.markdown(f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        for k in ["authenticated","usuario","rol","nombre_usuario"]:
            st.session_state[k] = False if k == "authenticated" else None
        st.rerun()
    st.sidebar.markdown("---")

    if ROL == "admin":
        menu = st.sidebar.radio("📋 MENÚ", [
            "📊 Dashboard", "👥 Clientes", "📦 Insumos (Cajas)",
            "🖥️ Equipos", "🔋 Baterías", "📋 Asignaciones",
            "🛒 Ventas", "💳 Créditos", "📜 Historial Asignaciones", "📈 Reportes"
        ])
    else:
        menu = st.sidebar.radio("📋 MENÚ", [
            "📊 Mi Resumen", "👥 Mis Clientes", "📦 Mis Insumos",
            "🖥️ Mis Equipos", "🛒 Registrar Venta", "💳 Mis Créditos"
        ])

    # ============================================================
    # ADMIN - DASHBOARD
    # ============================================================
    if menu == "📊 Dashboard" and ROL == "admin":
        st.title("📊 PANEL DE CONTROL — Surtidor Médico")
        ventas = cargar_ventas(); creditos = cargar_creditos()
        inventario = cargar_inventario(); clientes = cargar_clientes(); baterias = cargar_baterias()
        venta_total = ventas["monto"].sum() if not ventas.empty else 0
        cred_pend = creditos[creditos["pagado"] == False]["monto"].sum() if not creditos.empty else 0
        valor_inv = (inventario["Cantidad"] * inventario["Valor_Unitario"]).sum() if not inventario.empty else 0
        baterias_disp = len(baterias[baterias["estado"] == "Disponible"]) if not baterias.empty else 0
        col1,col2,col3,col4,col5 = st.columns(5)
        with col1: st.metric("👥 CLIENTES", len(clientes))
        with col2: st.metric("📦 VALOR INVENTARIO", f"${valor_inv:,.0f}")
        with col3: st.metric("💳 VENTA TOTAL", f"${venta_total:,.0f}")
        with col4: st.metric("⚠️ CRÉDITO PENDIENTE", f"${cred_pend:,.0f}")
        with col5: st.metric("🔋 BATERÍAS DISPONIBLES", baterias_disp)
        st.markdown("---")
        st.subheader("🔍 BUSCAR POR SERIAL")
        serial_buscar = st.text_input("Ingresa el serial (EQ-XXXXXX / INS-XXXXXX / BAT-XXXXXX)", placeholder="XXX-XXXXXX")
        if st.button("🔍 Buscar", key="btn_buscar_serial"):
            if serial_buscar:
                resultado = buscar_por_serial(serial_buscar.strip().upper())
                if resultado["equipo"]:
                    eq = resultado["equipo"]
                    st.success("✅ Equipo encontrado")
                    c1,c2,c3 = st.columns(3)
                    with c1:
                        st.write(f"**🖥️ Nombre:** {eq.get('Nombre','')}"); st.write(f"**📋 Serial:** {eq.get('Serial','')}"); st.write(f"**💰 Precio:** ${int(eq.get('Precio',0)):,.0f}")
                    with c2:
                        estado = eq.get('Estado',''); st.write(f"**{COLOR_ESTADO.get(estado,'⚪')} Estado:** {estado}"); st.write(f"**🧑‍💼 Asesor:** {eq.get('Asesor_Asignado','')}")
                    with c3:
                        st.write(f"**👤 Cliente:** {eq.get('Cliente_Asignado','')}"); st.write(f"**💬 Comentarios:** {eq.get('Comentarios','')}")
                    st.markdown("---"); st.markdown("**Asignar equipo:**")
                    asesores_list = obtener_asesores()
                    ca,cb,cc = st.columns(3)
                    with ca: nuevo_asesor_s = st.selectbox("Asesor", [""]+asesores_list, key="search_asesor")
                    with cb: nuevo_cliente_s = st.text_input("Cliente", value=eq.get('Cliente_Asignado',''), key="search_cliente")
                    with cc: nuevo_estado_s = st.selectbox("Estado", ESTADOS_EQUIPO, index=ESTADOS_EQUIPO.index(estado) if estado in ESTADOS_EQUIPO else 0, key="search_estado")
                    if st.button("💾 Guardar Asignación", key="search_guardar"):
                        campos = {"Estado": nuevo_estado_s, "Cliente_Asignado": nuevo_cliente_s}
                        if nuevo_asesor_s: campos["Asesor_Asignado"] = nuevo_asesor_s
                        if actualizar_equipo(int(eq["id"]), campos):
                            st.success("✅ Equipo actualizado"); st.rerun()
                elif resultado["insumo"]:
                    inv = resultado["insumo"]; st.success("✅ Insumo encontrado")
                    c1,c2,c3 = st.columns(3)
                    with c1: st.write(f"**📦 Caja:** {inv.get('Caja','')}"); st.write(f"**📋 Serial:** {inv.get('serial','')}")
                    with c2: st.write(f"**💰 Precio:** ${int(inv.get('Valor_Unitario',0)):,.0f}"); st.write(f"**📦 Stock:** {int(inv.get('Cantidad',0))}")
                    with c3: st.write(f"**📈 Total registrado:** {int(inv.get('Cantidad_Total',0))}")
                elif resultado["bateria"]:
                    bat = resultado["bateria"]; st.success("✅ Batería encontrada")
                    c1,c2,c3 = st.columns(3)
                    with c1:
                        st.write(f"**🔋 Nombre:** {bat.get('nombre','')}"); st.write(f"**📋 Serial:** {bat.get('serial','')}"); st.write(f"**🏭 Proveedor:** {bat.get('proveedor','')}")
                    with c2:
                        eb = bat.get('estado',''); st.write(f"**{COLOR_BATERIA.get(eb,'⚪')} Estado:** {eb}"); st.write(f"**⏱️ Horas uso:** {int(bat.get('tiempo_uso_horas',0))}"); st.write(f"**📅 F. compra:** {bat.get('fecha_compra','')}")
                    with c3:
                        st.write(f"**💰 Costo:** ${int(bat.get('costo',0)):,.0f}"); st.write(f"**🖥️ Equipo:** {bat.get('equipo_asignado','') or 'Sin asignar'}"); st.write(f"**💬 Notas:** {bat.get('notas','')}")
                else:
                    st.warning(f"⚠️ No se encontró ningún item con serial **{serial_buscar}**")
            else: st.warning("Ingresa un serial para buscar")
        st.markdown("---")
        if not ventas.empty:
            st.subheader("📊 Ventas por Asesor")
            va = ventas.groupby("asesor")["monto"].sum().reset_index()
            fig = px.bar(va, x="asesor", y="monto", color="monto", color_continuous_scale="Teal", labels={"monto":"Monto ($)","asesor":"Asesor"})
            st.plotly_chart(fig, use_container_width=True)
            st.subheader("📈 Ventas Últimos 30 Días")
            vc = ventas.copy(); vc["fecha"] = pd.to_datetime(vc["fecha"], errors="coerce").dt.date
            vc = vc.dropna(subset=["fecha"]); vc = vc[vc["fecha"] >= (datetime.now().date() - timedelta(days=30))]
            if not vc.empty:
                va2 = vc.groupby("fecha")["monto"].sum().sort_index()
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(x=va2.index, y=va2.values, marker_color="#16a085", text=[f"${v:,.0f}" for v in va2.values], textposition="outside"))
                fig2.add_trace(go.Scatter(x=va2.index, y=va2.values, mode="lines+markers", line=dict(color="#e74c3c", width=3)))
                fig2.update_layout(height=400, hovermode="x unified", showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)
            st.subheader("Últimas Ventas")
            vd = ventas.tail(15)[["fecha","asesor","cliente","caja","cantidad","monto"]].copy()
            vd["fecha"] = pd.to_datetime(vd["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")
            vd["monto"] = vd["monto"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(vd, use_container_width=True, hide_index=True)

    # ADMIN - CLIENTES
    elif menu == "👥 Clientes" and ROL == "admin":
        st.title("👥 GESTIÓN DE CLIENTES")
        clientes = cargar_clientes(); asesores = obtener_asesores()
        tab1, tab2 = st.tabs(["Ver Clientes", "Agregar Cliente"])
        with tab1:
            if not clientes.empty:
                st.dataframe(clientes[["nombre","cedula","telefono","asesor"]], use_container_width=True, hide_index=True)
                st.subheader("Eliminar Cliente")
                sel = st.selectbox("Selecciona cliente", clientes["nombre"].tolist())
                if st.button("🗑️ Eliminar"):
                    if eliminar_cliente(int(clientes[clientes["nombre"]==sel].iloc[0]["id"])): st.success("✅ Eliminado"); st.rerun()
            else: st.info("Sin clientes")
        with tab2:
            nombre = st.text_input("Nombre"); cedula = st.text_input("Cédula"); telefono = st.text_input("Teléfono")
            asesor_sel = st.selectbox("Asesor responsable", asesores)
            if st.button("💾 Guardar", use_container_width=True):
                if nombre and cedula:
                    if guardar_cliente(nombre, cedula, telefono, asesor_sel): st.success("✅ Cliente agregado"); st.rerun()
                else: st.error("Completa nombre y cédula")

    # ADMIN - INSUMOS
    elif menu == "📦 Insumos (Cajas)" and ROL == "admin":
        st.title("📦 GESTIÓN DE INSUMOS (CAJAS)")
        inventario = cargar_inventario()
        tab1, tab2, tab3 = st.tabs(["Ver Cajas", "Agregar Nueva Caja", "➕ Agregar Unidades"])
        with tab1:
            if not inventario.empty:
                for _, row in inventario.iterrows():
                    c1,c2,c3,c4,c5,c6 = st.columns([2,2,1.5,2,1.5,1])
                    with c1: st.write(f"**📦 {row['Caja']}**")
                    with c2: st.write(f"**💰 ${int(row['Valor_Unitario']):,.0f}**")
                    with c3:
                        cant = int(row["Cantidad"])
                        st.warning(f"⚠️ Stock: {cant}") if cant <= 2 else st.write(f"📦 Stock: {cant}")
                    with c4:
                        sv = row.get("serial","") or ""
                        st.write(f"**🔖 Serial:** `{sv}`" if sv else "**🔖 Serial:** Sin serial")
                    with c5: st.write(f"📈 Total: {int(row['Cantidad_Total'])}")
                    with c6:
                        if st.button("🗑️", key=f"di_{row['id']}"):
                            if eliminar_caja(int(row["id"])): st.success("✅"); st.rerun()
                    st.divider()
            else: st.info("Sin cajas")
        with tab2:
            caja = st.text_input("Nombre de la Caja")
            c1,c2 = st.columns(2)
            with c1: cantidad = st.number_input("Cantidad Inicial", min_value=1, value=1)
            with c2: valor = st.number_input("Valor Unitario ($)", min_value=0, value=0, step=1000)
            if st.button("💾 Guardar Caja", use_container_width=True):
                if caja and valor > 0:
                    ok, serial = guardar_caja_nueva(caja, cantidad, valor)
                    if ok: st.success(f"✅ Caja '{caja}' agregada"); st.info(f"📋 **Serial: `{serial}`**"); st.rerun()
                else: st.error("Completa todos los campos")
        with tab3:
            if not inventario.empty:
                opciones = [f"{row['Caja']} — Stock: {int(row['Cantidad'])}" for _, row in inventario.iterrows()]
                sel = st.selectbox("Selecciona Caja", opciones); idx = opciones.index(sel); row = inventario.iloc[idx]
                c1,c2 = st.columns(2)
                with c1: unidades = st.number_input("Unidades a agregar", min_value=1, value=1)
                with c2: np2 = st.number_input("Nuevo Precio ($)", min_value=0, value=int(row["Valor_Unitario"]), step=1000)
                st.info(f"Stock actual: {int(row['Cantidad'])} → Final: {int(row['Cantidad'])+unidades}")
                if st.button("💾 Guardar", use_container_width=True):
                    if actualizar_caja(int(row["id"]), {"Cantidad": int(row["Cantidad"])+unidades, "Cantidad_Total": int(row["Cantidad_Total"])+unidades, "Valor_Unitario": np2}):
                        st.success("✅ Actualizado"); st.rerun()

    # ADMIN - EQUIPOS
    elif menu == "🖥️ Equipos" and ROL == "admin":
        st.title("🖥️ GESTIÓN DE EQUIPOS")
        equipos = cargar_equipos(); asesores = obtener_asesores()
        tab1, tab2 = st.tabs(["Ver Equipos", "Agregar Equipo"])
        with tab1:
            if not equipos.empty:
                c1,c2 = st.columns(2)
                with c1: fe = st.selectbox("Filtrar estado", ["Todos"]+ESTADOS_EQUIPO)
                with c2: fa = st.selectbox("Filtrar asesor", ["Todos"]+asesores)
                ef = equipos.copy()
                if fe != "Todos": ef = ef[ef["Estado"]==fe]
                if fa != "Todos": ef = ef[ef["Asesor_Asignado"]==fa]
                st.markdown(f"**{len(ef)} equipo(s)**")
                for _, row in ef.iterrows():
                    with st.expander(f"{COLOR_ESTADO.get(row['Estado'],'⚪')} {row['Nombre']} | {row['Serial']} | {row['Estado']}"):
                        c1,c2,c3 = st.columns(3)
                        with c1: st.write(f"**💰** ${int(row.get('Precio',0)):,.0f}"); st.write(f"**🧑‍💼** {row.get('Asesor_Asignado','')}")
                        with c2: st.write(f"**👤** {row.get('Cliente_Asignado','')}")
                        with c3: st.write(f"**💬** {row.get('Comentarios','')}")
                        ce1,ce2,ce3 = st.columns(3)
                        with ce1:
                            idx_e = ESTADOS_EQUIPO.index(row["Estado"]) if row["Estado"] in ESTADOS_EQUIPO else 0
                            ne = st.selectbox("Estado", ESTADOS_EQUIPO, index=idx_e, key=f"e_{row['id']}")
                        with ce2:
                            oa = [""]+asesores; ia = oa.index(row.get("Asesor_Asignado","")) if row.get("Asesor_Asignado","") in oa else 0
                            na = st.selectbox("Asesor", oa, index=ia, key=f"a_{row['id']}")
                        with ce3:
                            nc = st.text_input("Comentario", value=str(row.get("Comentarios","")), key=f"c_{row['id']}")
                        ncli = st.text_input("Cliente", value=str(row.get("Cliente_Asignado","")), key=f"cl_{row['id']}")
                        b1,b2 = st.columns(2)
                        with b1:
                            if st.button("💾 Actualizar", key=f"u_{row['id']}"):
                                if actualizar_equipo(int(row["id"]), {"Estado":ne,"Asesor_Asignado":na,"Cliente_Asignado":ncli,"Comentarios":nc}): st.success("✅"); st.rerun()
                        with b2:
                            if st.button("🗑️ Eliminar", key=f"d_{row['id']}"):
                                if eliminar_equipo(int(row["id"])): st.success("✅"); st.rerun()
            else: st.info("Sin equipos")
        with tab2:
            c1,c2 = st.columns(2)
            with c1: ne2=st.text_input("Nombre del equipo"); se2=st.text_input("Serial / Código"); pe2=st.number_input("Precio ($)",min_value=0,value=0,step=1000)
            with c2: ee2=st.selectbox("Estado inicial",ESTADOS_EQUIPO); ae2=st.selectbox("Asesor asignado",[""]+asesores); ce2=st.text_input("Cliente (opcional)")
            come2 = st.text_area("Comentarios")
            if st.button("💾 Agregar Equipo", use_container_width=True):
                if ne2:
                    sf = se2 if se2 else generar_serial("EQ")
                    ok, sr = guardar_equipo_nuevo({"Nombre":ne2,"Serial":sf,"Estado":ee2,"Comentarios":come2,"Precio":int(pe2),"Asesor_Asignado":ae2,"Cliente_Asignado":ce2})
                    if ok: st.success(f"✅ Equipo '{ne2}' agregado"); st.info(f"📋 **Serial: `{sr}`**"); st.rerun()
                else: st.error("Completa el nombre del equipo")

    # ============================================================
    # ADMIN - BATERIAS (NUEVO)
    # ============================================================
    elif menu == "🔋 Baterías" and ROL == "admin":
        st.title("🔋 GESTIÓN DE BATERÍAS")
        baterias = cargar_baterias(); equipos_lista = cargar_equipos()
        if not baterias.empty:
            c1,c2,c3,c4 = st.columns(4)
            with c1: st.metric("🔋 Total", len(baterias))
            with c2: st.metric("🟢 Disponibles", len(baterias[baterias["estado"]=="Disponible"]))
            with c3: st.metric("🔵 En Uso", len(baterias[baterias["estado"]=="En uso"]))
            with c4: st.metric("🔴 Dañadas", len(baterias[baterias["estado"]=="Dañada"]))
            st.markdown("---")
        tab1,tab2,tab3 = st.tabs(["📋 Ver Baterías","➕ Agregar Batería","📊 Estadísticas"])

        with tab1:
            if not baterias.empty:
                cf1,cf2 = st.columns(2)
                with cf1: fb_est = st.selectbox("Filtrar estado", ["Todos"]+ESTADOS_BATERIA, key="f_bat_est")
                with cf2: fb_prov = st.text_input("Buscar proveedor", key="f_bat_prov")
                bf = baterias.copy()
                if fb_est != "Todos": bf = bf[bf["estado"]==fb_est]
                if fb_prov: bf = bf[bf["proveedor"].str.contains(fb_prov, case=False, na=False)]
                st.markdown(f"**{len(bf)} batería(s)**")
                for _, row in bf.iterrows():
                    eb = row.get("estado",""); cb2 = COLOR_BATERIA.get(eb,"⚪")
                    fc = row["fecha_compra"].strftime("%d/%m/%Y") if pd.notna(row.get("fecha_compra")) else "Sin fecha"
                    dias_uso = ""
                    if pd.notna(row.get("fecha_compra")):
                        delta = datetime.now().date() - row["fecha_compra"].date()
                        dias_uso = f"{delta.days} días desde compra"
                    with st.expander(f"{cb2} {row['nombre']} | {row['serial']} | {eb}"):
                        c1,c2,c3 = st.columns(3)
                        with c1:
                            st.write(f"**🏭 Proveedor:** {row.get('proveedor','')}"); st.write(f"**📅 Fecha compra:** {fc}"); st.write(f"**🗓️ Antigüedad:** {dias_uso}")
                        with c2:
                            st.write(f"**⏱️ Horas de uso:** {int(row.get('tiempo_uso_horas',0))}"); st.write(f"**💰 Costo:** ${int(row.get('costo',0)):,.0f}")
                        with c3:
                            st.write(f"**🖥️ Equipo asignado:** {row.get('equipo_asignado','') or 'Sin asignar'}"); st.write(f"**💬 Notas:** {row.get('notas','') or '—'}")
                        st.markdown("**Editar:**")
                        be1,be2,be3 = st.columns(3)
                        with be1:
                            idx_eb = ESTADOS_BATERIA.index(eb) if eb in ESTADOS_BATERIA else 0
                            neb = st.selectbox("Estado", ESTADOS_BATERIA, index=idx_eb, key=f"bst_{row['id']}")
                            ntu = st.number_input("Horas uso", min_value=0, value=int(row.get("tiempo_uso_horas",0)), key=f"btu_{row['id']}")
                        with be2:
                            eq_names = ["Sin asignar"]+(equipos_lista["Nombre"].tolist() if not equipos_lista.empty else [])
                            ea_val = row.get("equipo_asignado","") or "Sin asignar"
                            idx_eq = eq_names.index(ea_val) if ea_val in eq_names else 0
                            neq = st.selectbox("Equipo asignado", eq_names, index=idx_eq, key=f"beq_{row['id']}")
                        with be3:
                            nnot = st.text_area("Notas", value=str(row.get("notas","") or ""), key=f"bnot_{row['id']}", height=100)
                        b1,b2 = st.columns(2)
                        with b1:
                            if st.button("💾 Actualizar", key=f"bupd_{row['id']}"):
                                if actualizar_bateria(int(row["id"]), {"estado":neb,"tiempo_uso_horas":ntu,"equipo_asignado":neq if neq!="Sin asignar" else "","notas":nnot}):
                                    st.success("✅ Batería actualizada"); st.rerun()
                        with b2:
                            if st.button("🗑️ Eliminar", key=f"bdel_{row['id']}"):
                                if eliminar_bateria(int(row["id"])): st.success("✅ Eliminada"); st.rerun()
            else: st.info("No hay baterías registradas. Agrega la primera en ➕")

        with tab2:
            st.subheader("➕ Registrar nueva batería")
            c1,c2 = st.columns(2)
            with c1:
                nb_nombre = st.text_input("Nombre / Modelo", placeholder="Ej: Batería Li-Ion 12V 7Ah")
                nb_serial = st.text_input("Serial (vacío = autogenerar)", placeholder="BAT-XXXXXX")
                nb_proveedor = st.text_input("Proveedor", placeholder="Ej: Tecno Médica S.A.")
                nb_fecha = st.date_input("Fecha de compra", value=datetime.now().date())
            with c2:
                nb_tiempo = st.number_input("Horas de uso iniciales", min_value=0, value=0)
                nb_costo = st.number_input("Costo ($)", min_value=0, value=0, step=1000)
                nb_estado = st.selectbox("Estado inicial", ESTADOS_BATERIA)
                eq_new = ["Sin asignar"]+(equipos_lista["Nombre"].tolist() if not equipos_lista.empty else [])
                nb_equipo = st.selectbox("Equipo asignado (opcional)", eq_new)
            nb_notas = st.text_area("Notas", placeholder="Capacidad, ciclos de carga, observaciones...")
            if st.button("💾 Registrar Batería", use_container_width=True):
                if nb_nombre and nb_proveedor:
                    eq_final = nb_equipo if nb_equipo != "Sin asignar" else ""
                    ok, sb = guardar_bateria(nb_nombre, nb_proveedor, nb_fecha, nb_tiempo, nb_costo, nb_estado, eq_final, nb_notas, nb_serial)
                    if ok: st.success(f"✅ Batería '{nb_nombre}' registrada"); st.info(f"📋 **Serial: `{sb}`**"); st.rerun()
                else: st.error("❌ Completa nombre y proveedor")

        with tab3:
            if not baterias.empty:
                st.subheader("📊 Distribución por Estado")
                est_c = baterias["estado"].value_counts().reset_index(); est_c.columns=["Estado","Cantidad"]
                fig_b = px.pie(est_c, names="Estado", values="Cantidad", color_discrete_sequence=["#27ae60","#3498db","#e74c3c","#f39c12","#2c3e50"])
                st.plotly_chart(fig_b, use_container_width=True)
                st.subheader("🏭 Baterías por Proveedor")
                prov_c = baterias["proveedor"].value_counts().reset_index(); prov_c.columns=["Proveedor","Cantidad"]
                fig_p = px.bar(prov_c, x="Proveedor", y="Cantidad", color="Cantidad", color_continuous_scale="Teal")
                st.plotly_chart(fig_p, use_container_width=True)
                st.subheader("⏱️ Horas de Uso por Batería")
                bu = baterias[baterias["tiempo_uso_horas"]>0].sort_values("tiempo_uso_horas", ascending=False)
                if not bu.empty:
                    fig_u = px.bar(bu, x="nombre", y="tiempo_uso_horas", labels={"nombre":"Batería","tiempo_uso_horas":"Horas"}, color="tiempo_uso_horas", color_continuous_scale="Oranges")
                    st.plotly_chart(fig_u, use_container_width=True)
                st.subheader("📋 Tabla completa")
                ds = baterias[["nombre","serial","proveedor","fecha_compra","tiempo_uso_horas","costo","estado","equipo_asignado"]].copy()
                ds["fecha_compra"] = pd.to_datetime(ds["fecha_compra"], errors="coerce").dt.strftime("%d/%m/%Y")
                ds["costo"] = ds["costo"].apply(lambda x: f"${int(x):,.0f}")
                st.dataframe(ds, use_container_width=True, hide_index=True)
            else: st.info("Sin datos.")

    # ADMIN - ASIGNACIONES
    elif menu == "📋 Asignaciones" and ROL == "admin":
        st.title("📋 ASIGNACIONES DE INSUMOS A ASESORES")
        asesores = obtener_asesores(); asignaciones = cargar_asignaciones(); inventario = cargar_inventario()
        tab1, tab2 = st.tabs(["Ver Asignaciones", "Nueva Asignación"])
        with tab1:
            if not asignaciones.empty:
                ventas_asig = cargar_ventas()
                for asesor in asesores:
                    asig = asignaciones[asignaciones["asesor"]==asesor]
                    if not asig.empty:
                        with st.expander(f"🧑‍💼 {asesor} — {int(asig['cantidad'].sum())} unidades asignadas"):
                            for _, arow in asig.iterrows():
                                vc2 = ventas_asig[(ventas_asig["asesor"]==asesor)&(ventas_asig["caja"]==arow["caja"])] if not ventas_asig.empty else pd.DataFrame()
                                cant_a = int(arow["cantidad"]); cant_v = int(vc2["cantidad"].sum()) if not vc2.empty else 0; cant_s = max(cant_a-cant_v,0)
                                st.markdown(f"### 📦 {arow['caja']}")
                                ac1,ac2,ac3 = st.columns(3)
                                with ac1: st.metric("📦 Asignadas", cant_a)
                                with ac2: st.metric("✅ Vendidas", cant_v)
                                with ac3: st.metric("🟡 En Stock", cant_s)
                                fd = pd.to_datetime(arow["fecha"], errors="coerce")
                                st.caption(f"📅 {fd.strftime('%d/%m/%Y') if pd.notna(fd) else ''}")
                                if not vc2.empty:
                                    st.markdown("**🧾 Ventas:**")
                                    for _, vrow in vc2.iterrows():
                                        vcc1,vcc2,vcc3 = st.columns([3,2,2])
                                        with vcc1: st.write(f"👤 **{vrow['cliente']}**")
                                        with vcc2: st.write(f"📦 {int(vrow['cantidad'])} uds")
                                        with vcc3:
                                            fv = pd.to_datetime(vrow["fecha"], errors="coerce")
                                            st.write(f"📅 {fv.strftime('%d/%m/%Y') if pd.notna(fv) else ''}")
                                if st.button("🗑️ Eliminar asignación", key=f"del_asig_{arow['id']}"):
                                    try:
                                        supabase = get_supabase_client()
                                        supabase.table("asignaciones").delete().eq("id",int(arow["id"])).execute()
                                        inv_r = cargar_inventario(); caja_r = inv_r[inv_r["Caja"]==arow["caja"]]
                                        if not caja_r.empty: actualizar_caja(int(caja_r.iloc[0]["id"]), {"Cantidad":int(caja_r.iloc[0]["Cantidad"])+cant_s})
                                        registrar_historial_asignacion(asesor, arow["caja"], cant_s, "devolucion", f"Asignación eliminada — {cant_s} uds devueltas a bodega")
                                        st.success("✅ Asignación eliminada y stock restaurado"); st.rerun()
                                    except Exception as e: st.error(f"Error: {e}")
                                st.divider()
            else: st.info("Sin asignaciones")
        with tab2:
            if not inventario.empty:
                c1,c2,c3 = st.columns(3)
                with c1: ad = st.selectbox("Asesor destino", asesores)
                with c2: cs = st.selectbox("Caja", inventario["Caja"].tolist())
                with c3:
                    disp = int(inventario[inventario["Caja"]==cs].iloc[0]["Cantidad"]); st.metric("Stock disponible", disp)
                ca2 = st.number_input("Cantidad", min_value=1, max_value=disp if disp>0 else 1, value=1)
                fa2 = st.date_input("Fecha", value=datetime.now().date())
                if st.button("📋 Asignar", use_container_width=True):
                    if ca2 <= disp:
                        row_c = inventario[inventario["Caja"]==cs].iloc[0]
                        actualizar_caja(int(row_c["id"]), {"Cantidad":disp-ca2})
                        if guardar_asignacion(ad, cs, ca2, fa2): st.success(f"✅ {ca2} uds de '{cs}' → {ad}"); st.rerun()
                    else: st.error("Stock insuficiente")
            else: st.error("Sin cajas")

    # ADMIN - VENTAS
    elif menu == "🛒 Ventas" and ROL == "admin":
        st.title("🛒 VENTAS")
        inventario = cargar_inventario(); clientes = cargar_clientes(); asesores = obtener_asesores()
        tab1, tab2 = st.tabs(["Nueva Venta", "Historial"])
        with tab1:
            c1,c2 = st.columns(2)
            with c1: fecha = st.date_input("Fecha", value=datetime.now().date())
            with c2: av = st.selectbox("Asesor", asesores)
            cli_f = clientes[clientes["asesor"]==av] if not clientes.empty else pd.DataFrame()
            lcli = cli_f["nombre"].tolist() if not cli_f.empty else []
            cv = st.selectbox("Cliente", lcli if lcli else ["Sin clientes"])
            c3,c4 = st.columns(2)
            with c3: cajav = st.selectbox("Caja", inventario["Caja"].tolist() if not inventario.empty else ["Sin cajas"])
            with c4:
                if not inventario.empty and cajav != "Sin cajas": st.metric("Disponibles", int(inventario[inventario["Caja"]==cajav].iloc[0]["Cantidad"]))
            c5,c6 = st.columns(2)
            with c5: cantv = st.number_input("Cantidad", min_value=1, value=1)
            with c6:
                valu = int(inventario[inventario["Caja"]==cajav].iloc[0]["Valor_Unitario"]) if not inventario.empty and cajav!="Sin cajas" else 0
                st.metric("Valor Unitario", f"${valu:,.0f}")
            montov = cantv * valu; st.metric("Monto Total", f"${montov:,.0f}")
            ecv = st.checkbox("✅ Venta a Crédito")
            if st.button("💾 Guardar Venta", use_container_width=True):
                if cv != "Sin clientes" and cajav != "Sin cajas":
                    crow = inventario[inventario["Caja"]==cajav].iloc[0]; nc = int(crow["Cantidad"])-cantv
                    if nc < 0: st.error("❌ Stock insuficiente")
                    else:
                        actualizar_caja(int(crow["id"]), {"Cantidad":nc})
                        guardar_venta(fecha, cv, cajav, cantv, valu, montov, ecv, av)
                        if ecv: guardar_credito(cv, montov, fecha, av)
                        st.success("✅ Venta guardada"); st.rerun()
                else: st.error("Completa todos los campos")
        with tab2:
            ventas = cargar_ventas()
            if not ventas.empty:
                vd = ventas[["fecha","asesor","cliente","caja","cantidad","monto","es_credito"]].copy()
                vd["fecha"] = pd.to_datetime(vd["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")
                vd.insert(0, "Sel", False)
                edited = st.data_editor(vd, use_container_width=True, hide_index=True,
                                        column_config={"Sel":st.column_config.CheckboxColumn("✓",default=False,width="small"),"monto":st.column_config.NumberColumn("Monto ($)",format="$%d")},
                                        key="vh_admin")
                sel_idx = edited[edited["Sel"]].index.tolist()
                if sel_idx and st.button(f"🗑️ Eliminar {len(sel_idx)} venta(s)"): st.session_state["show_pwd"] = True
                if st.session_state.get("show_pwd", False):
                    pwd = st.text_input("🔑 Contraseña:", type="password", key="pwd_v")
                    b1,b2 = st.columns(2)
                    with b1:
                        if st.button("✅ Confirmar", key="conf_v"):
                            if pwd == "112915":
                                for i in sel_idx:
                                    v = ventas.iloc[i]; inv = cargar_inventario(); cr = inv[inv["Caja"]==v["caja"]]
                                    if not cr.empty: actualizar_caja(int(cr.iloc[0]["id"]), {"Cantidad":int(cr.iloc[0]["Cantidad"])+int(v["cantidad"])})
                                    eliminar_venta(int(v["id"]))
                                st.session_state["show_pwd"] = False; st.success("✅ Eliminadas"); st.rerun()
                            else: st.error("❌ Contraseña incorrecta")
                    with b2:
                        if st.button("❌ Cancelar", key="canc_v"): st.session_state["show_pwd"] = False; st.rerun()
            else: st.info("Sin ventas")

    # ADMIN - CREDITOS
    elif menu == "💳 Créditos" and ROL == "admin":
        st.title("💳 GESTIÓN DE CRÉDITOS")
        creditos = cargar_creditos(); asesores_cred = obtener_asesores()
        if not creditos.empty:
            pend = creditos[creditos["pagado"]==False]
            c1,c2,c3 = st.columns(3)
            with c1: st.metric("💳 TOTAL PENDIENTE", f"${pend['monto'].sum():,.0f}")
            with c2: st.metric("👥 CLIENTES CON DEUDA", pend["cliente"].nunique())
            with c3: st.metric("📋 REGISTROS", len(pend))
            st.markdown("---")
            filtro_ac = st.selectbox("🔍 Ver por asesor", ["Todos"]+asesores_cred, key="filtro_cred_asesor")
            for ac in (asesores_cred if filtro_ac=="Todos" else [filtro_ac]):
                ca = creditos[creditos["asesor"]==ac]
                if ca.empty: continue
                pa = ca[ca["pagado"]==False]
                with st.expander(f"🧑‍💼 {ac} — Pendiente: ${pa['monto'].sum():,.0f} ({len(pa)} registros)"):
                    for _, row in ca.iterrows():
                        c1,c2,c3,c4,c5 = st.columns([2,1.5,1.5,1.2,1.5])
                        with c1: st.write(f"**👤 {row['cliente']}**")
                        with c2: st.write(f"**💰 ${int(row['monto']):,.0f}**")
                        with c3:
                            fc = row["fecha_credito"].strftime("%d/%m/%Y") if pd.notna(row["fecha_credito"]) else ""
                            st.write(f"📅 {fc}")
                        with c4: st.success("✅ PAGADO") if row["pagado"] else st.error("❌ PENDIENTE")
                        with c5:
                            if not row["pagado"]:
                                if st.button("💰 Pagar", key=f"p_{row['id']}"):
                                    if marcar_credito_pagado(int(row["id"])): st.success("✅"); st.rerun()
                        st.divider()
        else: st.info("✅ Sin créditos")

    # ============================================================
    # ADMIN - HISTORIAL ASIGNACIONES (NUEVO)
    # ============================================================
    elif menu == "📜 Historial Asignaciones" and ROL == "admin":
        st.title("📜 HISTORIAL DE ASIGNACIONES Y MOVIMIENTOS")
        st.caption("🔒 Solo visible para administradores — registro completo de asignaciones, ventas y devoluciones.")
        asesores_h = obtener_asesores(); inventario_h = cargar_inventario()
        cf1,cf2,cf3,cf4 = st.columns(4)
        with cf1: fah = st.selectbox("Asesor", ["Todos"]+asesores_h, key="h_asesor")
        with cf2:
            cajas_h = ["Todas"]+(inventario_h["Caja"].tolist() if not inventario_h.empty else [])
            fch = st.selectbox("Caja / Insumo", cajas_h, key="h_caja")
        with cf3: fth = st.selectbox("Tipo", ["Todos","asignacion","venta","devolucion"], key="h_tipo")
        with cf4: frh = st.selectbox("Período", ["Todos","Últimos 7 días","Últimos 30 días","Últimos 90 días"], key="h_rango")
        asesor_q = None if fah=="Todos" else fah
        caja_q = None if fch=="Todas" else fch
        historial = cargar_historial_asignaciones(asesor=asesor_q, caja=caja_q)
        if not historial.empty:
            if fth != "Todos": historial = historial[historial["tipo"]==fth]
            if frh != "Todos":
                dm = {"Últimos 7 días":7,"Últimos 30 días":30,"Últimos 90 días":90}
                historial = historial[historial["fecha"] >= (datetime.now()-timedelta(days=dm[frh]))]
            st.markdown("---")
            m1,m2,m3,m4 = st.columns(4)
            with m1: st.metric("📋 Total registros", len(historial))
            with m2: st.metric("📦 Unidades asignadas", int(historial[historial["tipo"]=="asignacion"]["cantidad"].sum()))
            with m3: st.metric("✅ Unidades vendidas", int(historial[historial["tipo"]=="venta"]["cantidad"].sum()))
            with m4: st.metric("↩️ Devueltas", int(historial[historial["tipo"]=="devolucion"]["cantidad"].sum()))
            st.markdown("---")
            TIPO_COLOR = {"asignacion":"🟦","venta":"🟩","devolucion":"🟧"}
            st.subheader("📋 Registro de movimientos")
            for _, row in historial.iterrows():
                tc = TIPO_COLOR.get(row.get("tipo",""),"⚪")
                fs = row["fecha"].strftime("%d/%m/%Y %H:%M") if pd.notna(row["fecha"]) else "—"
                c1,c2,c3,c4,c5 = st.columns([1.5,2,2,1.8,3])
                with c1: st.write(f"**{fs}**")
                with c2: st.write(f"🧑‍💼 {row.get('asesor','')}")
                with c3: st.write(f"📦 {row.get('caja','')}")
                with c4: st.write(f"{tc} **{row.get('tipo','').capitalize()}** — {int(row.get('cantidad',0))} uds")
                with c5: st.write(f"💬 {row.get('nota','') or '—'}")
                st.divider()
            st.markdown("---")
            st.subheader("📊 Movimientos por Asesor")
            resumen = historial.groupby(["asesor","tipo"])["cantidad"].sum().reset_index()
            if not resumen.empty:
                fig_h = px.bar(resumen, x="asesor", y="cantidad", color="tipo", barmode="group",
                               labels={"cantidad":"Unidades","asesor":"Asesor","tipo":"Tipo"},
                               color_discrete_map={"asignacion":"#3498db","venta":"#27ae60","devolucion":"#e67e22"})
                st.plotly_chart(fig_h, use_container_width=True)
            st.subheader("📈 Movimientos en el tiempo")
            ht = historial.copy(); ht["fecha_dia"] = ht["fecha"].dt.date
            tl = ht.groupby(["fecha_dia","tipo"])["cantidad"].sum().reset_index()
            if not tl.empty:
                fig_t = px.line(tl, x="fecha_dia", y="cantidad", color="tipo",
                                labels={"fecha_dia":"Fecha","cantidad":"Unidades","tipo":"Tipo"},
                                color_discrete_map={"asignacion":"#3498db","venta":"#27ae60","devolucion":"#e67e22"})
                st.plotly_chart(fig_t, use_container_width=True)
            st.markdown("---")
            if st.button("📥 Exportar Historial a Excel", use_container_width=True):
                try:
                    archivo_h = f"Historial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    exp_df = historial.copy(); exp_df["fecha"] = exp_df["fecha"].dt.strftime("%d/%m/%Y %H:%M")
                    exp_df.to_excel(archivo_h, index=False); st.success(f"✅ {archivo_h}")
                except Exception as e: st.error(f"❌ {e}")
        else:
            st.info("📭 No hay registros para los filtros seleccionados.")
            st.caption("Los movimientos se registran automáticamente al crear asignaciones, eliminarlas o registrar ventas.")

    # ADMIN - REPORTES
    elif menu == "📈 Reportes" and ROL == "admin":
        st.title("📈 REPORTES Y ANÁLISIS")
        ventas=cargar_ventas(); creditos=cargar_creditos(); inventario=cargar_inventario()
        clientes=cargar_clientes(); equipos=cargar_equipos(); baterias=cargar_baterias()
        vt = ventas["monto"].sum() if not ventas.empty else 0
        cp = creditos[creditos["pagado"]==False]["monto"].sum() if not creditos.empty else 0
        vi = (inventario["Cantidad"]*inventario["Valor_Unitario"]).sum() if not inventario.empty else 0
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("💵 Valor Inventario", f"${vi:,.0f}")
        with c2: st.metric("💳 Venta Total", f"${vt:,.0f}")
        with c3: st.metric("⚠️ Crédito Pendiente", f"${cp:,.0f}")
        st.markdown("---")
        if not ventas.empty:
            st.subheader("📊 Ventas por Cliente")
            vpc = ventas.groupby("cliente").agg({"monto":"sum","cantidad":"sum"}).reset_index()
            vpc["total"] = vpc["monto"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(vpc[["cliente","total","cantidad"]].rename(columns={"total":"Total Vendido"}), use_container_width=True, hide_index=True)
            fig = px.bar(vpc, x="cliente", y="monto", color="monto", color_continuous_scale="Viridis")
            st.plotly_chart(fig, use_container_width=True)
        if not equipos.empty:
            st.markdown("---"); st.subheader("🖥️ Estado de Equipos")
            eq_e = equipos.groupby("Estado").size().reset_index(name="Cantidad")
            fig2 = px.pie(eq_e, names="Estado", values="Cantidad", color_discrete_sequence=["#f39c12","#3498db","#27ae60"])
            st.plotly_chart(fig2, use_container_width=True)
        if not baterias.empty:
            st.markdown("---"); st.subheader("🔋 Estado de Baterías")
            bat_e = baterias.groupby("estado").size().reset_index(name="Cantidad")
            fig_b = px.pie(bat_e, names="estado", values="Cantidad", color_discrete_sequence=["#27ae60","#3498db","#e74c3c","#f39c12","#2c3e50"])
            st.plotly_chart(fig_b, use_container_width=True)
        st.markdown("---")
        if st.button("📥 Descargar Excel", use_container_width=True):
            try:
                archivo = f"Reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                with pd.ExcelWriter(archivo, engine="openpyxl") as writer:
                    if not ventas.empty: ventas.to_excel(writer, index=False, sheet_name="Ventas")
                    if not inventario.empty: inventario.to_excel(writer, index=False, sheet_name="Insumos")
                    if not equipos.empty: equipos.to_excel(writer, index=False, sheet_name="Equipos")
                    if not clientes.empty: clientes.to_excel(writer, index=False, sheet_name="Clientes")
                    if not creditos.empty: creditos.to_excel(writer, index=False, sheet_name="Créditos")
                    if not baterias.empty: baterias.to_excel(writer, index=False, sheet_name="Baterías")
                st.success(f"✅ {archivo}")
            except Exception as e: st.error(f"❌ {e}")

    # ============================================================
    # ASESOR - MI RESUMEN
    # ============================================================
    elif menu == "📊 Mi Resumen" and ROL == "asesor":
        st.title(f"📊 MI RESUMEN — {NOMBRE}")
        mv=cargar_ventas(asesor=USUARIO); mc=cargar_creditos(asesor=USUARIO); mcli=cargar_clientes(asesor=USUARIO)
        pend = mc[mc["pagado"]==False] if not mc.empty else pd.DataFrame()
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("👥 MIS CLIENTES", len(mcli))
        with c2: st.metric("💳 MIS VENTAS", f"${mv['monto'].sum():,.0f}" if not mv.empty else "$0")
        with c3: st.metric("⚠️ CRÉDITO PENDIENTE", f"${pend['monto'].sum():,.0f}" if not pend.empty else "$0")
        if not mv.empty:
            st.markdown("---"); st.subheader("Mis Últimas Ventas")
            vd = mv.tail(10)[["fecha","cliente","caja","cantidad","monto"]].copy()
            vd["fecha"] = pd.to_datetime(vd["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")
            vd["monto"] = vd["monto"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(vd, use_container_width=True, hide_index=True)

    # ASESOR - MIS CLIENTES
    elif menu == "👥 Mis Clientes" and ROL == "asesor":
        st.title(f"👥 MIS CLIENTES — {NOMBRE}")
        mc = cargar_clientes(asesor=USUARIO)
        tab1, tab2 = st.tabs(["Ver Mis Clientes", "Agregar Cliente"])
        with tab1:
            if not mc.empty: st.dataframe(mc[["nombre","cedula","telefono"]], use_container_width=True, hide_index=True)
            else: st.info("No tienes clientes asignados")
        with tab2:
            nombre=st.text_input("Nombre"); cedula=st.text_input("Cédula"); telefono=st.text_input("Teléfono")
            if st.button("💾 Guardar", use_container_width=True):
                if nombre and cedula:
                    if guardar_cliente(nombre, cedula, telefono, USUARIO): st.success("✅ Cliente agregado"); st.rerun()
                else: st.error("Completa nombre y cédula")

    # ASESOR - MIS INSUMOS
    elif menu == "📦 Mis Insumos" and ROL == "asesor":
        st.title(f"📦 MIS INSUMOS — {NOMBRE}")
        ma = cargar_asignaciones(asesor=USUARIO)
        if not ma.empty:
            st.metric("Total unidades", int(ma["cantidad"].sum())); st.markdown("---")
            for _, row in ma.iterrows():
                c1,c2,c3 = st.columns([3,2,2])
                with c1: st.write(f"**📦 {row['caja']}**")
                with c2: st.write(f"**{int(row['cantidad'])} unidades**")
                with c3:
                    fd = pd.to_datetime(row["fecha"], errors="coerce")
                    st.write(f"📅 {fd.strftime('%d/%m/%Y') if pd.notna(fd) else ''}")
                st.divider()
        else: st.info("No tienes insumos asignados")

    # ASESOR - MIS EQUIPOS
    elif menu == "🖥️ Mis Equipos" and ROL == "asesor":
        st.title(f"🖥️ MIS EQUIPOS — {NOMBRE}")
        me = cargar_equipos(asesor=USUARIO)
        if not me.empty:
            fe = st.selectbox("Filtrar estado", ["Todos"]+ESTADOS_EQUIPO)
            if fe != "Todos": me = me[me["Estado"]==fe]
            st.markdown(f"**{len(me)} equipo(s)**")
            for _, row in me.iterrows():
                with st.expander(f"{COLOR_ESTADO.get(row['Estado'],'⚪')} {row['Nombre']} | {row['Serial']}"):
                    c1,c2 = st.columns(2)
                    with c1: st.write(f"**💰** ${int(row.get('Precio',0)):,.0f}"); st.write(f"**📋** {row['Estado']}")
                    with c2: st.write(f"**👤** {row.get('Cliente_Asignado','')}"); st.write(f"**💬** {row.get('Comentarios','')}")
                    ce1,ce2 = st.columns(2)
                    with ce1:
                        ie = ESTADOS_EQUIPO.index(row["Estado"]) if row["Estado"] in ESTADOS_EQUIPO else 0
                        ne = st.selectbox("Estado", ESTADOS_EQUIPO, index=ie, key=f"ea_{row['id']}")
                        ncli = st.text_input("Cliente", value=str(row.get("Cliente_Asignado","")), key=f"cla_{row['id']}")
                    with ce2:
                        ncom = st.text_area("Comentario", value=str(row.get("Comentarios","")), key=f"coa_{row['id']}")
                    if st.button("💾 Guardar", key=f"sa_{row['id']}"):
                        if actualizar_equipo(int(row["id"]), {"Estado":ne,"Cliente_Asignado":ncli,"Comentarios":ncom}): st.success("✅"); st.rerun()
        else: st.info("No tienes equipos asignados")

    # ASESOR - REGISTRAR VENTA
    elif menu == "🛒 Registrar Venta" and ROL == "asesor":
        st.title(f"🛒 REGISTRAR VENTA — {NOMBRE}")
        mcli=cargar_clientes(asesor=USUARIO); ma=cargar_asignaciones(asesor=USUARIO); inventario=cargar_inventario()
        c1,c2 = st.columns(2)
        with c1: fecha = st.date_input("Fecha", value=datetime.now().date())
        with c2:
            lcli = mcli["nombre"].tolist() if not mcli.empty else []
            cv = st.selectbox("Cliente", lcli if lcli else ["Sin clientes"])
        cajas_d = ma["caja"].unique().tolist() if not ma.empty else []
        c3,c4 = st.columns(2)
        with c3: cajav = st.selectbox("Caja", cajas_d if cajas_d else ["Sin cajas asignadas"])
        with c4:
            if cajas_d and not inventario.empty and cajav in inventario["Caja"].values:
                st.metric("Stock", int(inventario[inventario["Caja"]==cajav].iloc[0]["Cantidad"]))
        valu = int(inventario[inventario["Caja"]==cajav].iloc[0]["Valor_Unitario"]) if cajas_d and not inventario.empty and cajav in inventario["Caja"].values else 0
        c5,c6 = st.columns(2)
        with c5: cantv = st.number_input("Cantidad", min_value=1, value=1)
        with c6: st.metric("Valor Unitario", f"${valu:,.0f}")
        montov = cantv*valu; st.metric("Monto Total", f"${montov:,.0f}")
        ecv = st.checkbox("✅ Venta a Crédito")
        if st.button("💾 Guardar Venta", use_container_width=True):
            if cv != "Sin clientes" and cajav not in ["Sin cajas asignadas"]:
                crow = inventario[inventario["Caja"]==cajav].iloc[0]; nc = int(crow["Cantidad"])-cantv
                if nc < 0: st.error("❌ Stock insuficiente")
                else:
                    actualizar_caja(int(crow["id"]), {"Cantidad":nc})
                    guardar_venta(fecha, cv, cajav, cantv, valu, montov, ecv, USUARIO)
                    if ecv: guardar_credito(cv, montov, fecha, USUARIO)
                    st.success("✅ Venta registrada"); st.rerun()
            else: st.error("❌ Completa todos los campos")

    # ASESOR - MIS CREDITOS
    elif menu == "💳 Mis Créditos" and ROL == "asesor":
        st.title(f"💳 MIS CRÉDITOS — {NOMBRE}")
        mc = cargar_creditos(asesor=USUARIO)
        if not mc.empty:
            pend = mc[mc["pagado"]==False]
            c1,c2 = st.columns(2)
            with c1: st.metric("💳 PENDIENTE", f"${pend['monto'].sum():,.0f}" if not pend.empty else "$0")
            with c2: st.metric("📋 REGISTROS", len(pend))
            st.markdown("---")
            for _, row in mc.iterrows():
                c1,c2,c3,c4,c5 = st.columns([2,2,2,1.2,1.5])
                with c1: st.write(f"**👤 {row['cliente']}**")
                with c2: st.write(f"**💰 ${int(row['monto']):,.0f}**")
                with c3:
                    fc = row["fecha_credito"].strftime("%d/%m/%Y") if pd.notna(row["fecha_credito"]) else ""
                    st.write(f"📅 {fc}")
                with c4: st.success("✅") if row["pagado"] else st.error("❌")
                with c5:
                    if not row["pagado"]:
                        if st.button("💰 Pagado", key=f"pa_{row['id']}"):
                            if marcar_credito_pagado(int(row["id"])): st.success("✅"); st.rerun()
            st.divider()
        else: st.info("✅ Sin créditos")