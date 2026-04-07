import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import random
import string
import plotly.graph_objects as go
import plotly.express as px
from supabase import create_client

# ==============================
# CONFIGURACIÓN GENERAL
# ==============================
st.set_page_config(
    page_title="Surtidor Médico",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# SUPABASE
# ==============================
@st.cache_resource
def get_supabase_client():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

# ==============================
# UTILIDADES
# ==============================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Usuarios del sistema: Lucy (admin), Daniel / Javier / Oscar (asesores)

ESTADOS_EQUIPO = ["Recién ingresado", "En proceso de venta", "Listo para vender", "Pendiente por repuesto"]
COLOR_ESTADO = {
    "Recién ingresado": "🟡",
    "En proceso de venta": "🔵",
    "Listo para vender": "🟢",
    "Pendiente por repuesto": "🔴"
}
# ==============================
# GENERADOR Y BUSCADOR DE SERIALES
# ==============================
def generar_serial(prefijo="SM"):
    chars = string.ascii_uppercase + string.digits
    codigo = "".join(random.choices(chars, k=6))
    return f"{prefijo}-{codigo}"

def buscar_por_serial(serial):
    try:
        supabase = get_supabase_client()
        resultado = {"equipo": None, "insumo": None}
        eq = supabase.table("equipos").select("*").eq("Serial", serial).execute()
        if eq.data:
            resultado["equipo"] = eq.data[0]
        inv = supabase.table("inventario").select("*").eq("serial", serial).execute()
        if inv.data:
            resultado["insumo"] = inv.data[0]
        return resultado
    except Exception as e:
        st.error(f"Error buscando serial: {e}")
        return {"equipo": None, "insumo": None}



# ==============================
# USUARIOS
# ==============================
def verificar_usuario(usuario, contraseña):
    if not usuario or not contraseña:
        return False, None, None
    try:
        supabase = get_supabase_client()
        resp = supabase.table("usuarios").select("*").eq("usuario", usuario).execute()
        if not resp.data:
            return False, None, None
        row = resp.data[0]
        if row["contrasena"] == hash_password(contraseña):
            return True, row["rol"], row["nombre"]
        return False, None, None
    except Exception as e:
        st.error(f"Error verificando usuario: {e}")
        return False, None, None

def obtener_asesores():
    try:
        supabase = get_supabase_client()
        resp = supabase.table("usuarios").select("usuario,nombre").eq("rol", "asesor").execute()
        return [r["usuario"] for r in (resp.data or [])]
    except:
        return []

# ==============================
# INVENTARIO
# ==============================
def cargar_inventario():
    try:
        supabase = get_supabase_client()
        resp = supabase.table("inventario").select("*").execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            for col in ["Valor_Unitario", "Cantidad", "Cantidad_Total"]:
                if col not in df.columns:
                    df[col] = 0
            return df
        return pd.DataFrame(columns=["id", "Caja", "Cantidad", "Valor_Unitario", "Cantidad_Total"])
    except Exception as e:
        st.error(f"Error cargando inventario: {e}")
        return pd.DataFrame(columns=["id", "Caja", "Cantidad", "Valor_Unitario", "Cantidad_Total"])

def guardar_caja_nueva(caja, cantidad, valor_unitario):
    try:
        supabase = get_supabase_client()
        serial = generar_serial("INS")
        supabase.table("inventario").insert({
            "Caja": caja, "Cantidad": int(cantidad),
            "Valor_Unitario": int(valor_unitario), "Cantidad_Total": int(cantidad),
            "serial": serial
        }).execute()
        return True, serial
    except Exception as e:
        st.error(f"Error: {e}")
        return False, None

def actualizar_caja(caja_id, campos):
    try:
        supabase = get_supabase_client()
        supabase.table("inventario").update(campos).eq("id", caja_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def eliminar_caja(caja_id):
    try:
        supabase = get_supabase_client()
        supabase.table("inventario").delete().eq("id", caja_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# ==============================
# EQUIPOS
# ==============================
def cargar_equipos(asesor=None):
    try:
        supabase = get_supabase_client()
        query = supabase.table("equipos").select("*")
        if asesor:
            query = query.eq("Asesor_Asignado", asesor)
        resp = query.execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            for col in ["Nombre", "Serial", "Estado", "Comentarios", "Asesor_Asignado", "Cliente_Asignado"]:
                if col not in df.columns:
                    df[col] = ""
            if "Precio" not in df.columns:
                df["Precio"] = 0
            return df
        return pd.DataFrame(columns=["id", "Nombre", "Serial", "Estado", "Comentarios", "Precio", "Asesor_Asignado", "Cliente_Asignado"])
    except Exception as e:
        st.error(f"Error cargando equipos: {e}")
        return pd.DataFrame(columns=["id", "Nombre", "Serial", "Estado", "Comentarios", "Precio", "Asesor_Asignado", "Cliente_Asignado"])

def guardar_equipo_nuevo(d):
    try:
        supabase = get_supabase_client()
        if not d.get("Serial"):
            d["Serial"] = generar_serial("EQ")
        supabase.table("equipos").insert(d).execute()
        return True, d["Serial"]
    except Exception as e:
        st.error(f"Error: {e}")
        return False, None

def actualizar_equipo(equipo_id, campos):
    try:
        supabase = get_supabase_client()
        supabase.table("equipos").update(campos).eq("id", equipo_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def eliminar_equipo(equipo_id):
    try:
        supabase = get_supabase_client()
        supabase.table("equipos").delete().eq("id", equipo_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# ==============================
# CLIENTES
# ==============================
def cargar_clientes(asesor=None):
    try:
        supabase = get_supabase_client()
        query = supabase.table("clientes").select("*")
        if asesor:
            query = query.eq("asesor", asesor)
        resp = query.execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            for col in ["nombre", "cedula", "telefono", "direccion", "asesor"]:
                if col not in df.columns:
                    df[col] = ""
            return df
        return pd.DataFrame(columns=["id", "nombre", "cedula", "telefono", "direccion", "asesor"])
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=["id", "nombre", "cedula", "telefono", "direccion", "asesor"])

def guardar_cliente(nombre, cedula, telefono, asesor):
    try:
        supabase = get_supabase_client()
        supabase.table("clientes").insert({
            "nombre": nombre, "cedula": cedula,
            "telefono": telefono, "asesor": asesor
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def eliminar_cliente(cliente_id):
    try:
        supabase = get_supabase_client()
        supabase.table("clientes").delete().eq("id", cliente_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# ==============================
# ASIGNACIONES
# ==============================
def cargar_asignaciones(asesor=None):
    try:
        supabase = get_supabase_client()
        query = supabase.table("asignaciones").select("*")
        if asesor:
            query = query.eq("asesor", asesor)
        resp = query.execute()
        if resp.data:
            return pd.DataFrame(resp.data)
        return pd.DataFrame(columns=["id", "asesor", "caja", "cantidad", "fecha"])
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=["id", "asesor", "caja", "cantidad", "fecha"])

def guardar_asignacion(asesor, caja, cantidad, fecha):
    try:
        supabase = get_supabase_client()
        supabase.table("asignaciones").insert({
            "asesor": asesor, "caja": caja,
            "cantidad": int(cantidad), "fecha": fecha.strftime("%Y-%m-%d")
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# ==============================
# VENTAS
# ==============================
def cargar_ventas(asesor=None):
    try:
        supabase = get_supabase_client()
        query = supabase.table("ventas").select("*")
        if asesor:
            query = query.eq("asesor", asesor)
        resp = query.execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            if "fecha" in df.columns:
                df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
            for col in ["cliente", "caja", "asesor"]:
                if col not in df.columns:
                    df[col] = ""
            for col in ["cantidad", "valor_unitario", "monto"]:
                if col not in df.columns:
                    df[col] = 0
            if "es_credito" not in df.columns:
                df["es_credito"] = False
            return df
        return pd.DataFrame(columns=["id", "fecha", "cliente", "caja", "cantidad", "valor_unitario", "monto", "es_credito", "asesor"])
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=["id", "fecha", "cliente", "caja", "cantidad", "valor_unitario", "monto", "es_credito", "asesor"])

def guardar_venta(fecha, cliente, caja, cantidad, valor_unitario, monto, es_credito, asesor):
    try:
        supabase = get_supabase_client()
        supabase.table("ventas").insert({
            "fecha": fecha.strftime("%Y-%m-%d"), "cliente": cliente, "caja": caja,
            "cantidad": int(cantidad), "valor_unitario": int(valor_unitario),
            "monto": int(monto), "es_credito": bool(es_credito), "asesor": asesor
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def eliminar_venta(venta_id):
    try:
        supabase = get_supabase_client()
        supabase.table("ventas").delete().eq("id", venta_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# ==============================
# CRÉDITOS
# ==============================
def cargar_creditos(asesor=None):
    try:
        supabase = get_supabase_client()
        query = supabase.table("creditos").select("*")
        if asesor:
            query = query.eq("asesor", asesor)
        resp = query.execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            for col in ["fecha_credito", "fecha_pago"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
            if "pagado" not in df.columns:
                df["pagado"] = False
            for col in ["cliente", "asesor"]:
                if col not in df.columns:
                    df[col] = ""
            if "monto" not in df.columns:
                df["monto"] = 0
            return df
        return pd.DataFrame(columns=["id", "cliente", "monto", "fecha_credito", "pagado", "fecha_pago", "asesor"])
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=["id", "cliente", "monto", "fecha_credito", "pagado", "fecha_pago", "asesor"])

def guardar_credito(cliente, monto, fecha, asesor):
    try:
        supabase = get_supabase_client()
        supabase.table("creditos").insert({
            "cliente": cliente, "monto": int(monto),
            "fecha_credito": fecha.strftime("%Y-%m-%d"),
            "pagado": False, "asesor": asesor
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def marcar_credito_pagado(credito_id):
    try:
        supabase = get_supabase_client()
        supabase.table("creditos").update({
            "pagado": True, "fecha_pago": datetime.now().strftime("%Y-%m-%d")
        }).eq("id", credito_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# ==============================
# SESIÓN
# ==============================
for k, v in [("authenticated", False), ("usuario", None), ("rol", None), ("nombre_usuario", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

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
            if st.button("❌ Salir", use_container_width=True):
                st.info("Hasta luego")
        st.markdown("---")

# ==============================
# APP PRINCIPAL
# ==============================
else:
    ROL = st.session_state.rol
    USUARIO = st.session_state.usuario
    NOMBRE = st.session_state.nombre_usuario

    st.sidebar.title(f"👤 {NOMBRE}")
    st.sidebar.caption(f"{'🔑 Administrador' if ROL == 'admin' else '🧑‍💼 Asesor'}")
    st.sidebar.markdown(f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        for k in ["authenticated", "usuario", "rol", "nombre_usuario"]:
            st.session_state[k] = False if k == "authenticated" else None
        st.rerun()
    st.sidebar.markdown("---")

    if ROL == "admin":
        menu = st.sidebar.radio("📋 MENÚ", [
            "📊 Dashboard", "👥 Clientes", "📦 Insumos (Cajas)",
            "🖥️ Equipos", "📋 Asignaciones", "🛒 Ventas", "💳 Créditos", "📈 Reportes"
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
        ventas = cargar_ventas()
        creditos = cargar_creditos()
        inventario = cargar_inventario()
        clientes = cargar_clientes()

        venta_total = ventas["monto"].sum() if not ventas.empty else 0
        cred_pend = creditos[creditos["pagado"] == False]["monto"].sum() if not creditos.empty else 0
        valor_inv = (inventario["Cantidad"] * inventario["Valor_Unitario"]).sum() if not inventario.empty else 0

        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("👥 CLIENTES", len(clientes))
        with col2: st.metric("📦 VALOR INVENTARIO", f"${valor_inv:,.0f}")
        with col3: st.metric("💳 VENTA TOTAL", f"${venta_total:,.0f}")
        with col4: st.metric("⚠️ CRÉDITO PENDIENTE", f"${cred_pend:,.0f}")

        st.markdown("---")
        st.subheader("🔍 BUSCAR POR SERIAL")
        serial_buscar = st.text_input("Ingresa el serial (ej: EQ-A3X9K o INS-B7Z2M)", placeholder="SM-XXXXXX")
        if st.button("🔍 Buscar", key="btn_buscar_serial"):
            if serial_buscar:
                resultado = buscar_por_serial(serial_buscar.strip().upper())
                if resultado["equipo"]:
                    eq = resultado["equipo"]
                    st.success(f"✅ Equipo encontrado")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**🖥️ Nombre:** {eq.get('Nombre','')}")
                        st.write(f"**📋 Serial:** {eq.get('Serial','')}")
                        st.write(f"**💰 Precio:** ${int(eq.get('Precio',0)):,.0f}")
                    with col2:
                        estado = eq.get('Estado','')
                        color = COLOR_ESTADO.get(estado, '⚪')
                        st.write(f"**{color} Estado:** {estado}")
                        st.write(f"**🧑‍💼 Asesor:** {eq.get('Asesor_Asignado','')}")
                    with col3:
                        st.write(f"**👤 Cliente:** {eq.get('Cliente_Asignado','')}")
                        st.write(f"**💬 Comentarios:** {eq.get('Comentarios','')}")
                    st.markdown("---")
                    st.markdown("**Asignar equipo:**")
                    asesores_list = obtener_asesores()
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        nuevo_asesor_s = st.selectbox("Asesor", [""] + asesores_list, key="search_asesor")
                    with col_b:
                        nuevo_cliente_s = st.text_input("Cliente", value=eq.get('Cliente_Asignado',''), key="search_cliente")
                    with col_c:
                        nuevo_estado_s = st.selectbox("Estado", ESTADOS_EQUIPO,
                                                       index=ESTADOS_EQUIPO.index(estado) if estado in ESTADOS_EQUIPO else 0,
                                                       key="search_estado")
                    if st.button("💾 Guardar Asignación", key="search_guardar"):
                        campos = {"Estado": nuevo_estado_s, "Cliente_Asignado": nuevo_cliente_s}
                        if nuevo_asesor_s:
                            campos["Asesor_Asignado"] = nuevo_asesor_s
                        if actualizar_equipo(int(eq["id"]), campos):
                            st.success("✅ Equipo actualizado y asignado")
                            st.rerun()
                elif resultado["insumo"]:
                    inv = resultado["insumo"]
                    st.success(f"✅ Insumo encontrado")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**📦 Caja:** {inv.get('Caja','')}")
                        st.write(f"**📋 Serial:** {inv.get('serial','')}")
                    with col2:
                        st.write(f"**💰 Precio:** ${int(inv.get('Valor_Unitario',0)):,.0f}")
                        st.write(f"**📦 Stock actual:** {int(inv.get('Cantidad',0))}")
                    with col3:
                        st.write(f"**📈 Total registrado:** {int(inv.get('Cantidad_Total',0))}")
                else:
                    st.warning(f"⚠️ No se encontró ningún item con serial **{serial_buscar}**")
            else:
                st.warning("Ingresa un serial para buscar")

        st.markdown("---")
        if not ventas.empty:
            st.subheader("📊 Ventas por Asesor")
            va = ventas.groupby("asesor")["monto"].sum().reset_index()
            fig = px.bar(va, x="asesor", y="monto", color="monto", color_continuous_scale="Teal",
                         labels={"monto": "Monto ($)", "asesor": "Asesor"})
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📈 Ventas Últimos 30 Días")
            vc = ventas.copy()
            vc["fecha"] = pd.to_datetime(vc["fecha"], errors="coerce").dt.date
            vc = vc.dropna(subset=["fecha"])
            vc = vc[vc["fecha"] >= (datetime.now().date() - timedelta(days=30))]
            if not vc.empty:
                va2 = vc.groupby("fecha")["monto"].sum().sort_index()
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(x=va2.index, y=va2.values, marker_color="#16a085",
                                      text=[f"${v:,.0f}" for v in va2.values], textposition="outside"))
                fig2.add_trace(go.Scatter(x=va2.index, y=va2.values, mode="lines+markers",
                                          line=dict(color="#e74c3c", width=3)))
                fig2.update_layout(height=400, hovermode="x unified", showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Últimas Ventas")
            vd = ventas.tail(15)[["fecha", "asesor", "cliente", "caja", "cantidad", "monto"]].copy()
            vd["fecha"] = pd.to_datetime(vd["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")
            vd["monto"] = vd["monto"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(vd, use_container_width=True, hide_index=True)

    # ADMIN - CLIENTES
    elif menu == "👥 Clientes" and ROL == "admin":
        st.title("👥 GESTIÓN DE CLIENTES")
        clientes = cargar_clientes()
        asesores = obtener_asesores()
        tab1, tab2 = st.tabs(["Ver Clientes", "Agregar Cliente"])
        with tab1:
            if not clientes.empty:
                st.dataframe(clientes[["nombre", "cedula", "telefono", "asesor"]], use_container_width=True, hide_index=True)
                st.subheader("Eliminar Cliente")
                sel = st.selectbox("Selecciona cliente", clientes["nombre"].tolist())
                if st.button("🗑️ Eliminar"):
                    cid = int(clientes[clientes["nombre"] == sel].iloc[0]["id"])
                    if eliminar_cliente(cid):
                        st.success("✅ Eliminado")
                        st.rerun()
            else:
                st.info("Sin clientes")
        with tab2:
            nombre = st.text_input("Nombre")
            cedula = st.text_input("Cédula")
            telefono = st.text_input("Teléfono")
            asesor_sel = st.selectbox("Asesor responsable", asesores)
            if st.button("💾 Guardar", use_container_width=True):
                if nombre and cedula:
                    if guardar_cliente(nombre, cedula, telefono, asesor_sel):
                        st.success("✅ Cliente agregado")
                        st.rerun()
                else:
                    st.error("Completa nombre y cédula")

    # ADMIN - INSUMOS
    elif menu == "📦 Insumos (Cajas)" and ROL == "admin":
        st.title("📦 GESTIÓN DE INSUMOS (CAJAS)")
        inventario = cargar_inventario()
        tab1, tab2, tab3 = st.tabs(["Ver Cajas", "Agregar Nueva Caja", "➕ Agregar Unidades"])
        with tab1:
            if not inventario.empty:
                for _, row in inventario.iterrows():
                    c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 1.5, 2, 1.5, 1])
                    with c1: st.write(f"**📦 {row['Caja']}**")
                    with c2: st.write(f"**💰 ${int(row['Valor_Unitario']):,.0f}**")
                    with c3:
                        cant = int(row["Cantidad"])
                        st.warning(f"⚠️ Stock: {cant}") if cant <= 2 else st.write(f"📦 Stock: {cant}")
                    with c4:
                        serial_val = row.get("serial", "") or ""
                        st.write(f"**🔖 Serial:** `{serial_val}`" if serial_val else "**🔖 Serial:** Sin serial")
                    with c5: st.write(f"📈 Total: {int(row['Cantidad_Total'])}")
                    with c6:
                        if st.button("🗑️", key=f"di_{row['id']}"):
                            if eliminar_caja(int(row["id"])):
                                st.success("✅")
                                st.rerun()
                    st.divider()
            else:
                st.info("Sin cajas")
        with tab2:
            caja = st.text_input("Nombre de la Caja")
            c1, c2 = st.columns(2)
            with c1: cantidad = st.number_input("Cantidad Inicial", min_value=1, value=1)
            with c2: valor = st.number_input("Valor Unitario ($)", min_value=0, value=0, step=1000)
            if st.button("💾 Guardar Caja", use_container_width=True):
                if caja and valor > 0:
                    ok, serial = guardar_caja_nueva(caja, cantidad, valor)
                    if ok:
                        st.success(f"✅ Caja '{caja}' agregada")
                        st.info(f"📋 **Serial asignado: `{serial}`** — Anótalo para búsquedas futuras")
                        st.rerun()
                else:
                    st.error("Completa todos los campos")
        with tab3:
            if not inventario.empty:
                opciones = [f"{row['Caja']} — Stock: {int(row['Cantidad'])}" for _, row in inventario.iterrows()]
                sel = st.selectbox("Selecciona Caja", opciones)
                idx = opciones.index(sel)
                row = inventario.iloc[idx]
                c1, c2 = st.columns(2)
                with c1: unidades = st.number_input("Unidades a agregar", min_value=1, value=1)
                with c2: np2 = st.number_input("Nuevo Precio ($)", min_value=0, value=int(row["Valor_Unitario"]), step=1000)
                st.info(f"Stock actual: {int(row['Cantidad'])} → Final: {int(row['Cantidad']) + unidades}")
                if st.button("💾 Guardar", use_container_width=True):
                    if actualizar_caja(int(row["id"]), {
                        "Cantidad": int(row["Cantidad"]) + unidades,
                        "Cantidad_Total": int(row["Cantidad_Total"]) + unidades,
                        "Valor_Unitario": np2
                    }):
                        st.success("✅ Actualizado")
                        st.rerun()

    # ADMIN - EQUIPOS
    elif menu == "🖥️ Equipos" and ROL == "admin":
        st.title("🖥️ GESTIÓN DE EQUIPOS")
        equipos = cargar_equipos()
        asesores = obtener_asesores()
        tab1, tab2 = st.tabs(["Ver Equipos", "Agregar Equipo"])
        with tab1:
            if not equipos.empty:
                c1, c2 = st.columns(2)
                with c1: fe = st.selectbox("Filtrar estado", ["Todos"] + ESTADOS_EQUIPO)
                with c2: fa = st.selectbox("Filtrar asesor", ["Todos"] + asesores)
                ef = equipos.copy()
                if fe != "Todos": ef = ef[ef["Estado"] == fe]
                if fa != "Todos": ef = ef[ef["Asesor_Asignado"] == fa]
                st.markdown(f"**{len(ef)} equipo(s)**")
                for _, row in ef.iterrows():
                    with st.expander(f"{COLOR_ESTADO.get(row['Estado'], '⚪')} {row['Nombre']} | {row['Serial']} | {row['Estado']}"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.write(f"**💰** ${int(row.get('Precio', 0)):,.0f}")
                            st.write(f"**🧑‍💼** {row.get('Asesor_Asignado', '')}")
                        with c2:
                            st.write(f"**👤** {row.get('Cliente_Asignado', '')}")
                        with c3:
                            st.write(f"**💬** {row.get('Comentarios', '')}")
                        ce1, ce2, ce3 = st.columns(3)
                        with ce1:
                            idx_e = ESTADOS_EQUIPO.index(row["Estado"]) if row["Estado"] in ESTADOS_EQUIPO else 0
                            ne = st.selectbox("Estado", ESTADOS_EQUIPO, index=idx_e, key=f"e_{row['id']}")
                        with ce2:
                            oa = [""] + asesores
                            ia = oa.index(row.get("Asesor_Asignado", "")) if row.get("Asesor_Asignado", "") in oa else 0
                            na = st.selectbox("Asesor", oa, index=ia, key=f"a_{row['id']}")
                        with ce3:
                            nc = st.text_input("Comentario", value=str(row.get("Comentarios", "")), key=f"c_{row['id']}")
                        ncli = st.text_input("Cliente", value=str(row.get("Cliente_Asignado", "")), key=f"cl_{row['id']}")
                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("💾 Actualizar", key=f"u_{row['id']}"):
                                if actualizar_equipo(int(row["id"]), {"Estado": ne, "Asesor_Asignado": na, "Cliente_Asignado": ncli, "Comentarios": nc}):
                                    st.success("✅")
                                    st.rerun()
                        with b2:
                            if st.button("🗑️ Eliminar", key=f"d_{row['id']}"):
                                if eliminar_equipo(int(row["id"])):
                                    st.success("✅")
                                    st.rerun()
            else:
                st.info("Sin equipos")
        with tab2:
            c1, c2 = st.columns(2)
            with c1:
                ne2 = st.text_input("Nombre del equipo")
                se2 = st.text_input("Serial / Código")
                pe2 = st.number_input("Precio ($)", min_value=0, value=0, step=1000)
            with c2:
                ee2 = st.selectbox("Estado inicial", ESTADOS_EQUIPO)
                ae2 = st.selectbox("Asesor asignado", [""] + asesores)
                ce2 = st.text_input("Cliente (opcional)")
            come2 = st.text_area("Comentarios")
            if st.button("💾 Agregar Equipo", use_container_width=True):
                if ne2:
                    serial_eq_final = se2 if se2 else generar_serial("EQ")
                    ok, serial_ret = guardar_equipo_nuevo({"Nombre": ne2, "Serial": serial_eq_final, "Estado": ee2,
                                            "Comentarios": come2, "Precio": int(pe2),
                                            "Asesor_Asignado": ae2, "Cliente_Asignado": ce2})
                    if ok:
                        st.success(f"✅ Equipo '{ne2}' agregado")
                        st.info(f"📋 **Serial asignado: `{serial_ret}`** — Anótalo para búsquedas futuras")
                        st.rerun()
                else:
                    st.error("Completa el nombre del equipo")

    # ADMIN - ASIGNACIONES
    elif menu == "📋 Asignaciones" and ROL == "admin":
        st.title("📋 ASIGNACIONES DE INSUMOS A ASESORES")
        asesores = obtener_asesores()
        asignaciones = cargar_asignaciones()
        inventario = cargar_inventario()
        tab1, tab2 = st.tabs(["Ver Asignaciones", "Nueva Asignación"])
        with tab1:
            if not asignaciones.empty:
                ventas_asig = cargar_ventas()
                for asesor in asesores:
                    asig = asignaciones[asignaciones["asesor"] == asesor]
                    if not asig.empty:
                        with st.expander(f"🧑‍💼 {asesor} — {int(asig['cantidad'].sum())} unidades asignadas"):
                            for _, arow in asig.iterrows():
                                # Buscar ventas de este asesor con esta caja
                                ventas_caja = ventas_asig[
                                    (ventas_asig["asesor"] == asesor) &
                                    (ventas_asig["caja"] == arow["caja"])
                                ] if not ventas_asig.empty else pd.DataFrame()

                                cant_asignada = int(arow["cantidad"])
                                cant_vendida = int(ventas_caja["cantidad"].sum()) if not ventas_caja.empty else 0
                                cant_en_stock = max(cant_asignada - cant_vendida, 0)

                                st.markdown(f"### 📦 {arow['caja']}")
                                ac1, ac2, ac3 = st.columns(3)
                                with ac1:
                                    st.metric("📦 Asignadas", cant_asignada)
                                with ac2:
                                    st.metric("✅ Vendidas", cant_vendida)
                                with ac3:
                                    st.metric("🟡 En Stock", cant_en_stock)

                                fd = pd.to_datetime(arow["fecha"], errors="coerce")
                                st.caption(f"📅 Fecha asignación: {fd.strftime('%d/%m/%Y') if pd.notna(fd) else ''}")

                                if not ventas_caja.empty:
                                    st.markdown("**🧾 Ventas realizadas:**")
                                    for _, vrow in ventas_caja.iterrows():
                                        vc1, vc2, vc3 = st.columns([3, 2, 2])
                                        with vc1: st.write(f"👤 **Cliente:** {vrow['cliente']}")
                                        with vc2: st.write(f"📦 {int(vrow['cantidad'])} unidades")
                                        with vc3:
                                            fv = pd.to_datetime(vrow["fecha"], errors="coerce")
                                            st.write(f"📅 {fv.strftime('%d/%m/%Y') if pd.notna(fv) else ''}")

                                if st.button("🗑️ Eliminar asignación", key=f"del_asig_{arow['id']}"):
                                    try:
                                        supabase = get_supabase_client()
                                        supabase.table("asignaciones").delete().eq("id", int(arow["id"])).execute()
                                        inv_r = cargar_inventario()
                                        caja_r = inv_r[inv_r["Caja"] == arow["caja"]]
                                        if not caja_r.empty:
                                            actualizar_caja(int(caja_r.iloc[0]["id"]),
                                                {"Cantidad": int(caja_r.iloc[0]["Cantidad"]) + cant_en_stock})
                                        st.success("✅ Asignación eliminada y stock en bodega restaurado")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                                st.divider()
            else:
                st.info("Sin asignaciones")
        with tab2:
            if not inventario.empty:
                c1, c2, c3 = st.columns(3)
                with c1: ad = st.selectbox("Asesor destino", asesores)
                with c2: cs = st.selectbox("Caja", inventario["Caja"].tolist())
                with c3:
                    disp = int(inventario[inventario["Caja"] == cs].iloc[0]["Cantidad"])
                    st.metric("Stock disponible", disp)
                ca2 = st.number_input("Cantidad", min_value=1, max_value=disp if disp > 0 else 1, value=1)
                fa2 = st.date_input("Fecha", value=datetime.now().date())
                if st.button("📋 Asignar", use_container_width=True):
                    if ca2 <= disp:
                        row_c = inventario[inventario["Caja"] == cs].iloc[0]
                        actualizar_caja(int(row_c["id"]), {"Cantidad": disp - ca2})
                        if guardar_asignacion(ad, cs, ca2, fa2):
                            st.success(f"✅ {ca2} uds de '{cs}' → {ad}")
                            st.rerun()
                    else:
                        st.error("Stock insuficiente")
            else:
                st.error("Sin cajas")

    # ADMIN - VENTAS
    elif menu == "🛒 Ventas" and ROL == "admin":
        st.title("🛒 VENTAS")
        inventario = cargar_inventario()
        clientes = cargar_clientes()
        asesores = obtener_asesores()
        tab1, tab2 = st.tabs(["Nueva Venta", "Historial"])
        with tab1:
            c1, c2 = st.columns(2)
            with c1: fecha = st.date_input("Fecha", value=datetime.now().date())
            with c2: av = st.selectbox("Asesor", asesores)
            cli_f = clientes[clientes["asesor"] == av] if not clientes.empty else pd.DataFrame()
            lcli = cli_f["nombre"].tolist() if not cli_f.empty else []
            cv = st.selectbox("Cliente", lcli if lcli else ["Sin clientes"])
            c3, c4 = st.columns(2)
            with c3: cajav = st.selectbox("Caja", inventario["Caja"].tolist() if not inventario.empty else ["Sin cajas"])
            with c4:
                if not inventario.empty and cajav != "Sin cajas":
                    st.metric("Disponibles", int(inventario[inventario["Caja"] == cajav].iloc[0]["Cantidad"]))
            c5, c6 = st.columns(2)
            with c5: cantv = st.number_input("Cantidad", min_value=1, value=1)
            with c6:
                valu = int(inventario[inventario["Caja"] == cajav].iloc[0]["Valor_Unitario"]) if not inventario.empty and cajav != "Sin cajas" else 0
                st.metric("Valor Unitario", f"${valu:,.0f}")
            montov = cantv * valu
            st.metric("Monto Total", f"${montov:,.0f}")
            ecv = st.checkbox("✅ Venta a Crédito")
            if st.button("💾 Guardar Venta", use_container_width=True):
                if cv != "Sin clientes" and cajav != "Sin cajas":
                    crow = inventario[inventario["Caja"] == cajav].iloc[0]
                    nc = int(crow["Cantidad"]) - cantv
                    if nc < 0:
                        st.error("❌ Stock insuficiente")
                    else:
                        actualizar_caja(int(crow["id"]), {"Cantidad": nc})
                        guardar_venta(fecha, cv, cajav, cantv, valu, montov, ecv, av)
                        if ecv: guardar_credito(cv, montov, fecha, av)
                        st.success("✅ Venta guardada")
                        st.rerun()
                else:
                    st.error("Completa todos los campos")
        with tab2:
            ventas = cargar_ventas()
            if not ventas.empty:
                vd = ventas[["fecha", "asesor", "cliente", "caja", "cantidad", "monto", "es_credito"]].copy()
                vd["fecha"] = pd.to_datetime(vd["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")
                vd.insert(0, "Sel", False)
                edited = st.data_editor(vd, use_container_width=True, hide_index=True,
                                        column_config={"Sel": st.column_config.CheckboxColumn("✓", default=False, width="small"),
                                                        "monto": st.column_config.NumberColumn("Monto ($)", format="$%d")},
                                        key="vh_admin")
                sel_idx = edited[edited["Sel"]].index.tolist()
                if sel_idx and st.button(f"🗑️ Eliminar {len(sel_idx)} venta(s)"):
                    st.session_state["show_pwd"] = True
                if st.session_state.get("show_pwd", False):
                    pwd = st.text_input("🔑 Contraseña:", type="password", key="pwd_v")
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("✅ Confirmar", key="conf_v"):
                            if pwd == "112915":
                                for i in sel_idx:
                                    v = ventas.iloc[i]
                                    inv = cargar_inventario()
                                    cr = inv[inv["Caja"] == v["caja"]]
                                    if not cr.empty:
                                        actualizar_caja(int(cr.iloc[0]["id"]), {"Cantidad": int(cr.iloc[0]["Cantidad"]) + int(v["cantidad"])})
                                    eliminar_venta(int(v["id"]))
                                st.session_state["show_pwd"] = False
                                st.success("✅ Eliminadas")
                                st.rerun()
                            else:
                                st.error("❌ Contraseña incorrecta")
                    with b2:
                        if st.button("❌ Cancelar", key="canc_v"):
                            st.session_state["show_pwd"] = False
                            st.rerun()
            else:
                st.info("Sin ventas")

    # ADMIN - CRÉDITOS
    elif menu == "💳 Créditos" and ROL == "admin":
        st.title("💳 GESTIÓN DE CRÉDITOS")
        creditos = cargar_creditos()
        asesores_cred = obtener_asesores()
        if not creditos.empty:
            pend = creditos[creditos["pagado"] == False]
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("💳 TOTAL PENDIENTE", f"${pend['monto'].sum():,.0f}")
            with c2: st.metric("👥 CLIENTES CON DEUDA", pend["cliente"].nunique())
            with c3: st.metric("📋 REGISTROS", len(pend))
            st.markdown("---")

            filtro_asesor_cred = st.selectbox("🔍 Ver créditos por asesor", ["Todos"] + asesores_cred, key="filtro_cred_asesor")

            for asesor_c in (asesores_cred if filtro_asesor_cred == "Todos" else [filtro_asesor_cred]):
                creds_asesor = creditos[creditos["asesor"] == asesor_c]
                if creds_asesor.empty:
                    continue
                pend_asesor = creds_asesor[creds_asesor["pagado"] == False]
                with st.expander(f"🧑‍💼 {asesor_c} — Pendiente: ${pend_asesor['monto'].sum():,.0f} ({len(pend_asesor)} registros)"):
                    for _, row in creds_asesor.iterrows():
                        c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 1.2, 1.5])
                        with c1: st.write(f"**👤 {row['cliente']}**")
                        with c2: st.write(f"**💰 ${int(row['monto']):,.0f}**")
                        with c3:
                            fc = row["fecha_credito"].strftime("%d/%m/%Y") if pd.notna(row["fecha_credito"]) else ""
                            st.write(f"📅 {fc}")
                        with c4:
                            if row["pagado"]:
                                st.success("✅ PAGADO")
                            else:
                                st.error("❌ PENDIENTE")
                        with c5:
                            if not row["pagado"]:
                                if st.button("💰 Pagar", key=f"p_{row['id']}"):
                                    if marcar_credito_pagado(int(row["id"])):
                                        st.success("✅")
                                        st.rerun()
                        st.divider()
        else:
            st.info("✅ Sin créditos")

    # ADMIN - REPORTES
    elif menu == "📈 Reportes" and ROL == "admin":
        st.title("📈 REPORTES Y ANÁLISIS")
        ventas = cargar_ventas()
        creditos = cargar_creditos()
        inventario = cargar_inventario()
        clientes = cargar_clientes()
        equipos = cargar_equipos()

        vt = ventas["monto"].sum() if not ventas.empty else 0
        cp = creditos[creditos["pagado"] == False]["monto"].sum() if not creditos.empty else 0
        vi = (inventario["Cantidad"] * inventario["Valor_Unitario"]).sum() if not inventario.empty else 0

        c1, c2, c3 = st.columns(3)
        with c1: st.metric("💵 Valor Inventario", f"${vi:,.0f}")
        with c2: st.metric("💳 Venta Total", f"${vt:,.0f}")
        with c3: st.metric("⚠️ Crédito Pendiente", f"${cp:,.0f}")

        st.markdown("---")
        if not ventas.empty:
            st.subheader("📊 Ventas por Cliente")
            vpc = ventas.groupby("cliente").agg({"monto": "sum", "cantidad": "sum"}).reset_index()
            vpc["total"] = vpc["monto"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(vpc[["cliente", "total", "cantidad"]].rename(columns={"total": "Total Vendido"}),
                         use_container_width=True, hide_index=True)
            fig = px.bar(vpc, x="cliente", y="monto", color="monto", color_continuous_scale="Viridis")
            st.plotly_chart(fig, use_container_width=True)

        if not equipos.empty:
            st.markdown("---")
            st.subheader("🖥️ Estado de Equipos")
            eq_e = equipos.groupby("Estado").size().reset_index(name="Cantidad")
            fig2 = px.pie(eq_e, names="Estado", values="Cantidad",
                          color_discrete_sequence=["#f39c12", "#3498db", "#27ae60"])
            st.plotly_chart(fig2, use_container_width=True)

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
                st.success(f"✅ {archivo}")
            except Exception as e:
                st.error(f"❌ {e}")

    # ============================================================
    # ASESOR - MI RESUMEN
    # ============================================================
    elif menu == "📊 Mi Resumen" and ROL == "asesor":
        st.title(f"📊 MI RESUMEN — {NOMBRE}")
        mv = cargar_ventas(asesor=USUARIO)
        mc = cargar_creditos(asesor=USUARIO)
        mcli = cargar_clientes(asesor=USUARIO)
        pend = mc[mc["pagado"] == False] if not mc.empty else pd.DataFrame()
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("👥 MIS CLIENTES", len(mcli))
        with c2: st.metric("💳 MIS VENTAS", f"${mv['monto'].sum():,.0f}" if not mv.empty else "$0")
        with c3: st.metric("⚠️ CRÉDITO PENDIENTE", f"${pend['monto'].sum():,.0f}" if not pend.empty else "$0")
        if not mv.empty:
            st.markdown("---")
            st.subheader("Mis Últimas Ventas")
            vd = mv.tail(10)[["fecha", "cliente", "caja", "cantidad", "monto"]].copy()
            vd["fecha"] = pd.to_datetime(vd["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")
            vd["monto"] = vd["monto"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(vd, use_container_width=True, hide_index=True)

    # ASESOR - MIS CLIENTES
    elif menu == "👥 Mis Clientes" and ROL == "asesor":
        st.title(f"👥 MIS CLIENTES — {NOMBRE}")
        mc = cargar_clientes(asesor=USUARIO)
        tab1, tab2 = st.tabs(["Ver Mis Clientes", "Agregar Cliente"])
        with tab1:
            if not mc.empty:
                st.dataframe(mc[["nombre", "cedula", "telefono"]], use_container_width=True, hide_index=True)
            else:
                st.info("No tienes clientes asignados")
        with tab2:
            nombre = st.text_input("Nombre")
            cedula = st.text_input("Cédula")
            telefono = st.text_input("Teléfono")
            if st.button("💾 Guardar", use_container_width=True):
                if nombre and cedula:
                    if guardar_cliente(nombre, cedula, telefono, USUARIO):
                        st.success("✅ Cliente agregado")
                        st.rerun()
                else:
                    st.error("Completa nombre y cédula")

    # ASESOR - MIS INSUMOS
    elif menu == "📦 Mis Insumos" and ROL == "asesor":
        st.title(f"📦 MIS INSUMOS — {NOMBRE}")
        ma = cargar_asignaciones(asesor=USUARIO)
        if not ma.empty:
            st.metric("Total unidades", int(ma["cantidad"].sum()))
            st.markdown("---")
            for _, row in ma.iterrows():
                c1, c2, c3 = st.columns([3, 2, 2])
                with c1: st.write(f"**📦 {row['caja']}**")
                with c2: st.write(f"**{int(row['cantidad'])} unidades**")
                with c3:
                    fd = pd.to_datetime(row["fecha"], errors="coerce")
                    st.write(f"📅 {fd.strftime('%d/%m/%Y') if pd.notna(fd) else ''}")
                st.divider()
        else:
            st.info("No tienes insumos asignados")

    # ASESOR - MIS EQUIPOS
    elif menu == "🖥️ Mis Equipos" and ROL == "asesor":
        st.title(f"🖥️ MIS EQUIPOS — {NOMBRE}")
        me = cargar_equipos(asesor=USUARIO)
        if not me.empty:
            fe = st.selectbox("Filtrar estado", ["Todos"] + ESTADOS_EQUIPO)
            if fe != "Todos": me = me[me["Estado"] == fe]
            st.markdown(f"**{len(me)} equipo(s)**")
            for _, row in me.iterrows():
                with st.expander(f"{COLOR_ESTADO.get(row['Estado'], '⚪')} {row['Nombre']} | {row['Serial']}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**💰** ${int(row.get('Precio', 0)):,.0f}")
                        st.write(f"**📋** {row['Estado']}")
                    with c2:
                        st.write(f"**👤** {row.get('Cliente_Asignado', '')}")
                        st.write(f"**💬** {row.get('Comentarios', '')}")
                    ce1, ce2 = st.columns(2)
                    with ce1:
                        ie = ESTADOS_EQUIPO.index(row["Estado"]) if row["Estado"] in ESTADOS_EQUIPO else 0
                        ne = st.selectbox("Estado", ESTADOS_EQUIPO, index=ie, key=f"ea_{row['id']}")
                        ncli = st.text_input("Cliente", value=str(row.get("Cliente_Asignado", "")), key=f"cla_{row['id']}")
                    with ce2:
                        ncom = st.text_area("Comentario", value=str(row.get("Comentarios", "")), key=f"coa_{row['id']}")
                    if st.button("💾 Guardar", key=f"sa_{row['id']}"):
                        if actualizar_equipo(int(row["id"]), {"Estado": ne, "Cliente_Asignado": ncli, "Comentarios": ncom}):
                            st.success("✅")
                            st.rerun()
        else:
            st.info("No tienes equipos asignados")

    # ASESOR - REGISTRAR VENTA
    elif menu == "🛒 Registrar Venta" and ROL == "asesor":
        st.title(f"🛒 REGISTRAR VENTA — {NOMBRE}")
        mcli = cargar_clientes(asesor=USUARIO)
        ma = cargar_asignaciones(asesor=USUARIO)
        inventario = cargar_inventario()
        c1, c2 = st.columns(2)
        with c1: fecha = st.date_input("Fecha", value=datetime.now().date())
        with c2:
            lcli = mcli["nombre"].tolist() if not mcli.empty else []
            cv = st.selectbox("Cliente", lcli if lcli else ["Sin clientes"])
        cajas_d = ma["caja"].unique().tolist() if not ma.empty else []
        c3, c4 = st.columns(2)
        with c3: cajav = st.selectbox("Caja", cajas_d if cajas_d else ["Sin cajas asignadas"])
        with c4:
            if cajas_d and not inventario.empty and cajav in inventario["Caja"].values:
                st.metric("Stock", int(inventario[inventario["Caja"] == cajav].iloc[0]["Cantidad"]))
        valu = int(inventario[inventario["Caja"] == cajav].iloc[0]["Valor_Unitario"]) if cajas_d and not inventario.empty and cajav in inventario["Caja"].values else 0
        c5, c6 = st.columns(2)
        with c5: cantv = st.number_input("Cantidad", min_value=1, value=1)
        with c6: st.metric("Valor Unitario", f"${valu:,.0f}")
        montov = cantv * valu
        st.metric("Monto Total", f"${montov:,.0f}")
        ecv = st.checkbox("✅ Venta a Crédito")
        if st.button("💾 Guardar Venta", use_container_width=True):
            if cv != "Sin clientes" and cajav not in ["Sin cajas asignadas"]:
                crow = inventario[inventario["Caja"] == cajav].iloc[0]
                nc = int(crow["Cantidad"]) - cantv
                if nc < 0:
                    st.error("❌ Stock insuficiente")
                else:
                    actualizar_caja(int(crow["id"]), {"Cantidad": nc})
                    guardar_venta(fecha, cv, cajav, cantv, valu, montov, ecv, USUARIO)
                    if ecv: guardar_credito(cv, montov, fecha, USUARIO)
                    st.success("✅ Venta registrada")
                    st.rerun()
            else:
                st.error("❌ Completa todos los campos")

    # ASESOR - MIS CRÉDITOS
    elif menu == "💳 Mis Créditos" and ROL == "asesor":
        st.title(f"💳 MIS CRÉDITOS — {NOMBRE}")
        mc = cargar_creditos(asesor=USUARIO)
        if not mc.empty:
            pend = mc[mc["pagado"] == False]
            c1, c2 = st.columns(2)
            with c1: st.metric("💳 PENDIENTE", f"${pend['monto'].sum():,.0f}" if not pend.empty else "$0")
            with c2: st.metric("📋 REGISTROS", len(pend))
            st.markdown("---")
            for _, row in mc.iterrows():
                c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1.2, 1.5])
                with c1: st.write(f"**👤 {row['cliente']}**")
                with c2: st.write(f"**💰 ${int(row['monto']):,.0f}**")
                with c3:
                    fc = row["fecha_credito"].strftime("%d/%m/%Y") if pd.notna(row["fecha_credito"]) else ""
                    st.write(f"📅 {fc}")
                with c4:
                    if row["pagado"]:
                        st.success("✅")
                    else:
                        st.error("❌")
                with c5:
                    if not row["pagado"]:
                        if st.button("💰 Pagado", key=f"pa_{row['id']}"):
                            if marcar_credito_pagado(int(row["id"])):
                                st.success("✅")
                                st.rerun()
            st.divider()
        else:
            st.info("✅ Sin créditos")