import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
import hashlib

# ======================================
# CONFIG
# ======================================
st.set_page_config(page_title="Surtidor Médico PRO", layout="wide")

@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"]
    )

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ======================================
# AUTH
# ======================================
def login(usuario, password):
    sb = get_supabase()
    res = sb.table("usuarios").select("*").eq("usuario", usuario).execute()

    if not res.data:
        return None

    user = res.data[0]
    if user["contrasena"] == hash_password(password):
        return user

    return None

# ======================================
# CLIENTES
# ======================================
def get_clientes():
    return pd.DataFrame(get_supabase().table("clientes").select("*").execute().data)

def crear_cliente(nombre, cedula):
    get_supabase().table("clientes").insert({
        "nombre": nombre,
        "cedula": cedula
    }).execute()

# ======================================
# INVENTARIO
# ======================================
def get_inventario():
    return pd.DataFrame(get_supabase().table("inventario").select("*").execute().data)

# ======================================
# VENTAS (REFactor REAL)
# ======================================
def registrar_venta(cliente, caja, cantidad, precio, asesor):
    sb = get_supabase()

    monto = cantidad * precio

    sb.table("ventas").insert({
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "cliente": cliente,
        "caja": caja,
        "cantidad": int(cantidad),
        "valor_unitario": int(precio),
        "monto": int(monto),
        "asesor": asesor
    }).execute()

    # actualizar stock
    inv = sb.table("inventario").select("*").eq("Caja", caja).execute().data

    if inv:
        stock = inv[0]["Cantidad"]
        nuevo = stock - cantidad

        if nuevo < 0:
            st.error("Stock insuficiente")
            return False

        sb.table("inventario").update({
            "Cantidad": nuevo
        }).eq("id", inv[0]["id"]).execute()

    return True

# ======================================
# SESSION
# ======================================
if "user" not in st.session_state:
    st.session_state.user = None

# ======================================
# LOGIN UI
# ======================================
if not st.session_state.user:

    st.title("🔐 Login")

    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        user = login(u, p)

        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

# ======================================
# APP
# ======================================
else:
    user = st.session_state.user

    st.sidebar.write(f"👤 {user['nombre']}")
    menu = st.sidebar.radio("Menú", [
        "Dashboard",
        "Clientes",
        "Ventas",
        "Inventario"
    ])

    # ==================================
    # DASHBOARD
    # ==================================
    if menu == "Dashboard":
        st.title("📊 Dashboard")

        clientes = get_clientes()
        inventario = get_inventario()

        col1, col2 = st.columns(2)
        col1.metric("Clientes", len(clientes))
        col2.metric("Cajas", len(inventario))

    # ==================================
    # CLIENTES
    # ==================================
    elif menu == "Clientes":
        st.title("👥 Clientes")

        df = get_clientes()

        if not df.empty:
            st.dataframe(df)

        nombre = st.text_input("Nombre")
        cedula = st.text_input("Cédula")

        if st.button("Crear cliente"):
            if nombre and cedula:
                crear_cliente(nombre, cedula)
                st.success("Cliente creado")
                st.rerun()

    # ==================================
    # INVENTARIO
    # ==================================
    elif menu == "Inventario":
        st.title("📦 Inventario")

        df = get_inventario()

        if not df.empty:
            st.dataframe(df)

    # ==================================
    # VENTAS
    # ==================================
    elif menu == "Ventas":
        st.title("💰 Ventas")

        clientes = get_clientes()
        inventario = get_inventario()

        cliente = st.selectbox("Cliente", clientes["nombre"] if not clientes.empty else [])
        caja = st.selectbox("Caja", inventario["Caja"] if not inventario.empty else [])

        cantidad = st.number_input("Cantidad", min_value=1, value=1)
        precio = st.number_input("Precio", min_value=0, value=1000)

        if st.button("Registrar venta"):
            ok = registrar_venta(cliente, caja, cantidad, precio, user["usuario"])

            if ok:
                st.success("Venta registrada")
                st.rerun()