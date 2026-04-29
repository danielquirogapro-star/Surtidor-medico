import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib, random, string, unicodedata
import plotly.express as px
from supabase import create_client

st.set_page_config(page_title="Surtidor Médico", layout="wide", initial_sidebar_state="expanded")

# ══════════════════════════════════════════════
# ESTILOS PROFESIONALES
# ══════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background-color: #0f1117; }
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#151822 0%,#0f1117 100%);
    border-right: 1px solid #1e2333;
}
section[data-testid="stSidebar"] * { color: #c9d1e8 !important; }
h1 { color:#e8ecf7!important;font-weight:700!important;letter-spacing:-0.5px!important; }
h2,h3 { color:#c9d1e8!important;font-weight:600!important; }
[data-testid="metric-container"] {
    background:#151822;border:1px solid #1e2333;border-radius:12px;padding:16px 20px!important;
}
[data-testid="metric-container"]:hover { border-color:#3b82f6; }
[data-testid="stMetricLabel"] { color:#6b7a9e!important;font-size:0.75rem!important;text-transform:uppercase;letter-spacing:0.5px; }
[data-testid="stMetricValue"] { color:#e8ecf7!important;font-size:1.6rem!important;font-weight:700!important; }
.stTabs [data-baseweb="tab-list"] {
    background:#151822;border-radius:10px;padding:4px;gap:4px;border:1px solid #1e2333;
}
.stTabs [data-baseweb="tab"] {
    background:transparent;border-radius:8px;color:#6b7a9e!important;
    font-weight:500;font-size:0.85rem;padding:8px 16px;border:none!important;
}
.stTabs [aria-selected="true"] { background:#1e2d4a!important;color:#60a5fa!important; }
.stTextInput>div>div>input,
.stNumberInput>div>div>input,
.stSelectbox>div>div {
    background:#151822!important;border:1px solid #1e2333!important;
    border-radius:8px!important;color:#e8ecf7!important;
}
.stTextInput>div>div>input:focus { border-color:#3b82f6!important; }
.stButton>button {
    background:#1e2d4a!important;color:#60a5fa!important;border:1px solid #2a3f6b!important;
    border-radius:8px!important;font-weight:600!important;font-size:0.83rem!important;
    padding:8px 18px!important;transition:all .2s!important;
}
.stButton>button:hover {
    background:#2a3f6b!important;border-color:#3b82f6!important;
    transform:translateY(-1px);box-shadow:0 4px 12px rgba(59,130,246,.2)!important;
}
.streamlit-expanderHeader {
    background:#151822!important;border:1px solid #1e2333!important;
    border-radius:10px!important;color:#c9d1e8!important;font-weight:500!important;
}
.streamlit-expanderContent {
    background:#11141f!important;border:1px solid #1e2333!important;
    border-top:none!important;border-radius:0 0 10px 10px!important;
}
[data-testid="stDataFrame"] { border:1px solid #1e2333!important;border-radius:10px!important;overflow:hidden; }
.stSuccess>div { background:#0d2818!important;border-color:#22c55e!important;color:#4ade80!important;border-radius:8px!important; }
.stError>div   { background:#2d0f0f!important;border-color:#ef4444!important;color:#f87171!important;border-radius:8px!important; }
.stWarning>div { background:#2d1f0a!important;border-color:#f59e0b!important;color:#fbbf24!important;border-radius:8px!important; }
.stInfo>div    { background:#0d1a2d!important;border-color:#3b82f6!important;color:#93c5fd!important;border-radius:8px!important; }
hr { border-color:#1e2333!important; }
.stCaption { color:#6b7a9e!important; }
label { color:#8892aa!important;font-size:0.83rem!important;font-weight:500!important; }
::-webkit-scrollbar { width:5px;height:5px; }
::-webkit-scrollbar-track { background:#0f1117; }
::-webkit-scrollbar-thumb { background:#1e2333;border-radius:3px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# CACHE & CONFIG
# ══════════════════════════════════════════════
@st.cache_resource
def get_supabase_client():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

@st.cache_data(ttl=300)
def get_cached_inventario():   return cargar_inventario()
@st.cache_data(ttl=300)
def get_cached_asesores():     return obtener_asesores()
@st.cache_data(ttl=300)
def get_cached_clientes():     return cargar_clientes()
@st.cache_data(ttl=120)
def get_cached_asignaciones(): return cargar_asignaciones()
@st.cache_data(ttl=120)
def get_cached_ventas():       return cargar_ventas()
@st.cache_data(ttl=120)
def get_cached_creditos():     return cargar_creditos()

def clear_all_cache(): st.cache_data.clear()

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

def generar_serial(pref="SM"):
    return f"{pref}-{''.join(random.choices(string.ascii_uppercase+string.digits, k=6))}"

def normalizar(s):
    s = str(s).lower()
    return ''.join(c for c in unicodedata.normalize('NFD',s) if unicodedata.category(c)!='Mn')

ESTADOS_EQUIPO  = ["Recién ingresado","En proceso de venta","Listo para vender","Pendiente por repuesto"]
COLOR_ESTADO    = {"Recién ingresado":"🟡","En proceso de venta":"🔵","Listo para vender":"🟢","Pendiente por repuesto":"🔴"}
ESTADOS_BATERIA = ["Disponible","En uso","Dañada","En mantenimiento","Baja de inventario"]
COLOR_BATERIA   = {"Disponible":"🟢","En uso":"🔵","Dañada":"🔴","En mantenimiento":"🟡","Baja de inventario":"⚫"}

# ══════════════════════════════════════════════
# DATA FUNCTIONS
# ══════════════════════════════════════════════
def verificar_usuario(usuario, contraseña):
    if not usuario or not contraseña: return False,None,None
    try:
        resp = get_supabase_client().table("usuarios").select("*").eq("usuario",usuario).execute()
        if not resp.data: return False,None,None
        row = resp.data[0]
        if row["contrasena"]==hash_password(contraseña): return True,row["rol"],row["nombre"]
        return False,None,None
    except Exception as e: st.error(f"Error: {e}"); return False,None,None

def obtener_asesores():
    try:
        resp = get_supabase_client().table("usuarios").select("usuario,nombre").eq("rol","asesor").execute()
        return [r["usuario"] for r in (resp.data or [])]
    except: return []

def cargar_clientes(asesor=None):
    try:
        q = get_supabase_client().table("clientes").select("*")
        if asesor: q = q.eq("asesor",asesor)
        resp = q.execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            for c in ["nombre","cedula","telefono","direccion","asesor"]:
                if c not in df.columns: df[c]=""
            return df
        return pd.DataFrame(columns=["id","nombre","cedula","telefono","direccion","asesor"])
    except Exception as e: st.error(f"Error:{e}"); return pd.DataFrame(columns=["id","nombre","cedula","telefono","direccion","asesor"])

def guardar_cliente(nombre,cedula,telefono,asesor):
    try: get_supabase_client().table("clientes").insert({"nombre":nombre,"cedula":cedula,"telefono":telefono,"asesor":asesor}).execute(); return True
    except Exception as e: st.error(f"Error:{e}"); return False

def eliminar_cliente(cid):
    try: get_supabase_client().table("clientes").delete().eq("id",cid).execute(); return True
    except Exception as e: st.error(f"Error:{e}"); return False

def cargar_inventario():
    try:
        resp = get_supabase_client().table("inventario").select("*").execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            for c in ["Cantidad","Cantidad_Total"]:
                if c not in df.columns: df[c]=0
            return df
        return pd.DataFrame(columns=["id","Caja","Cantidad","Cantidad_Total","serial"])
    except Exception as e: st.error(f"Error:{e}"); return pd.DataFrame(columns=["id","Caja","Cantidad","Cantidad_Total","serial"])

def guardar_caja_nueva(caja):
    try:
        serial=generar_serial("INS")
        get_supabase_client().table("inventario").insert({"Caja":caja,"Cantidad":0,"Cantidad_Total":0,"serial":serial}).execute()
        return True,serial
    except Exception as e: st.error(f"Error:{e}"); return False,None

def actualizar_caja(caja_id,campos):
    try: get_supabase_client().table("inventario").update(campos).eq("id",caja_id).execute(); return True
    except Exception as e: st.error(f"Error:{e}"); return False

def renombrar_caja(caja_id,nuevo_nombre):
    try: get_supabase_client().table("inventario").update({"Caja":nuevo_nombre}).eq("id",caja_id).execute(); return True
    except Exception as e: st.error(f"Error:{e}"); return False

def eliminar_caja(caja_id):
    try:
        sb=get_supabase_client()
        sb.table("items_caja").delete().eq("caja_id",caja_id).execute()
        sb.table("inventario").delete().eq("id",caja_id).execute()
        return True
    except Exception as e: st.error(f"Error:{e}"); return False

def cargar_items_caja(caja_id):
    try:
        resp = get_supabase_client().table("items_caja").select("*").eq("caja_id",caja_id).order("id").execute()
        if resp.data:
            df=pd.DataFrame(resp.data)
            for c in ["nombre","descripcion"]:
                if c not in df.columns: df[c]=""
            for c in ["cantidad","precio_unitario"]:
                if c not in df.columns: df[c]=0
            return df
        return pd.DataFrame(columns=["id","caja_id","nombre","descripcion","cantidad","precio_unitario","serial_item"])
    except Exception as e: st.error(f"Error:{e}"); return pd.DataFrame(columns=["id","caja_id","nombre","descripcion","cantidad","precio_unitario","serial_item"])

def guardar_item_caja(caja_id,nombre,descripcion,cantidad,precio_unitario):
    try:
        s=generar_serial("ITM")
        get_supabase_client().table("items_caja").insert({"caja_id":int(caja_id),"nombre":nombre,"descripcion":descripcion,"cantidad":int(cantidad),"precio_unitario":int(precio_unitario),"serial_item":s}).execute()
        return True,s
    except Exception as e: st.error(f"Error:{e}"); return False,None

def actualizar_item_caja(item_id,campos):
    try: get_supabase_client().table("items_caja").update(campos).eq("id",item_id).execute(); return True
    except Exception as e: st.error(f"Error:{e}"); return False

def eliminar_item_caja(item_id):
    try: get_supabase_client().table("items_caja").delete().eq("id",item_id).execute(); return True
    except Exception as e: st.error(f"Error:{e}"); return False

def calcular_valor_caja(df):
    if df.empty: return 0
    return int((df["cantidad"]*df["precio_unitario"]).sum())

def cargar_equipos(asesor=None):
    try:
        q=get_supabase_client().table("equipos").select("*")
        if asesor: q=q.eq("Asesor_Asignado",asesor)
        resp=q.execute()
        if resp.data:
            df=pd.DataFrame(resp.data)
            for c in ["Nombre","Serial","Estado","Comentarios","Asesor_Asignado","Cliente_Asignado"]:
                if c not in df.columns: df[c]=""
            if "Precio" not in df.columns: df["Precio"]=0
            return df
        return pd.DataFrame(columns=["id","Nombre","Serial","Estado","Comentarios","Precio","Asesor_Asignado","Cliente_Asignado"])
    except Exception as e: st.error(f"Error:{e}"); return pd.DataFrame(columns=["id","Nombre","Serial","Estado","Comentarios","Precio","Asesor_Asignado","Cliente_Asignado"])

def guardar_equipo_nuevo(d):
    try:
        if not d.get("Serial"): d["Serial"]=generar_serial("EQ")
        get_supabase_client().table("equipos").insert(d).execute()
        return True,d["Serial"]
    except Exception as e: st.error(f"Error:{e}"); return False,None

def actualizar_equipo(eid,campos):
    try: get_supabase_client().table("equipos").update(campos).eq("id",eid).execute(); return True
    except Exception as e: st.error(f"Error:{e}"); return False

def eliminar_equipo(eid):
    try: get_supabase_client().table("equipos").delete().eq("id",eid).execute(); return True
    except Exception as e: st.error(f"Error:{e}"); return False

def cargar_baterias():
    try:
        resp=get_supabase_client().table("baterias").select("*").execute()
        if resp.data:
            df=pd.DataFrame(resp.data)
            for c in ["nombre","serial","proveedor","estado","equipo_asignado","notas"]:
                if c not in df.columns: df[c]=""
            for c in ["tiempo_uso_horas","costo"]:
                if c not in df.columns: df[c]=0
            if "fecha_compra" in df.columns: df["fecha_compra"]=pd.to_datetime(df["fecha_compra"],errors="coerce")
            return df
        return pd.DataFrame(columns=["id","nombre","serial","proveedor","fecha_compra","tiempo_uso_horas","costo","estado","equipo_asignado","notas"])
    except Exception as e: st.error(f"Error:{e}"); return pd.DataFrame(columns=["id","nombre","serial","proveedor","fecha_compra","tiempo_uso_horas","costo","estado","equipo_asignado","notas"])

def guardar_bateria(nombre,proveedor,fc,horas,costo,estado,equipo,notas,serial_m=""):
    try:
        s=serial_m or generar_serial("BAT")
        get_supabase_client().table("baterias").insert({"nombre":nombre,"serial":s,"proveedor":proveedor,"fecha_compra":fc.strftime("%Y-%m-%d"),"tiempo_uso_horas":int(horas),"costo":int(costo),"estado":estado,"equipo_asignado":equipo,"notas":notas}).execute()
        return True,s
    except Exception as e: st.error(f"Error:{e}"); return False,None

def actualizar_bateria(bid,campos):
    try: get_supabase_client().table("baterias").update(campos).eq("id",bid).execute(); return True
    except Exception as e: st.error(f"Error:{e}"); return False

def registrar_historial(asesor,caja,cantidad,tipo,nota=""):
    if tipo=="credito": return
    try:
        get_supabase_client().table("historial_asignaciones").insert({"asesor":asesor,"caja":caja,"cantidad":int(cantidad),"tipo":tipo,"nota":nota,"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}).execute()
    except: pass

def cargar_historial_asignaciones(asesor=None,caja=None):
    try:
        q=get_supabase_client().table("historial_asignaciones").select("*")
        if asesor: q=q.eq("asesor",asesor)
        if caja:   q=q.eq("caja",caja)
        resp=q.order("fecha",desc=True).execute()
        if resp.data:
            df=pd.DataFrame(resp.data)
            df["fecha"]=pd.to_datetime(df["fecha"],errors="coerce")
            for c in ["asesor","caja","tipo","nota"]:
                if c not in df.columns: df[c]=""
            if "cantidad" not in df.columns: df["cantidad"]=0
            return df[df["tipo"]!="credito"]
        return pd.DataFrame(columns=["id","asesor","caja","cantidad","tipo","nota","fecha"])
    except Exception as e: st.error(f"Error:{e}"); return pd.DataFrame(columns=["id","asesor","caja","cantidad","tipo","nota","fecha"])

def cargar_asignaciones(asesor=None):
    try:
        q=get_supabase_client().table("asignaciones").select("*")
        if asesor: q=q.eq("asesor",asesor)
        resp=q.execute()
        if resp.data:
            df=pd.DataFrame(resp.data)
            if "comentario" not in df.columns: df["comentario"]=""
            return df
        return pd.DataFrame(columns=["id","asesor","caja","cantidad","fecha","comentario"])
    except Exception as e: st.error(f"Error:{e}"); return pd.DataFrame(columns=["id","asesor","caja","cantidad","fecha","comentario"])

def guardar_asignacion(asesor,caja,cantidad,fecha,comentario=""):
    try:
        get_supabase_client().table("asignaciones").insert({"asesor":asesor,"caja":caja,"cantidad":int(cantidad),"fecha":fecha.strftime("%Y-%m-%d"),"comentario":comentario}).execute()
        nota=f"Asignación {cantidad} uds '{caja}' → {asesor}"
        if comentario: nota+=f" — {comentario}"
        registrar_historial(asesor,caja,cantidad,"asignacion",nota)
        return True
    except Exception as e: st.error(f"Error:{e}"); return False

def cargar_ventas(asesor=None):
    try:
        q=get_supabase_client().table("ventas").select("*")
        if asesor: q=q.eq("asesor",asesor)
        resp=q.execute()
        if resp.data:
            df=pd.DataFrame(resp.data)
            if "fecha" in df.columns: df["fecha"]=pd.to_datetime(df["fecha"],errors="coerce")
            for c in ["cliente","caja","asesor"]:
                if c not in df.columns: df[c]=""
            for c in ["cantidad","valor_unitario","monto"]:
                if c not in df.columns: df[c]=0
            if "es_credito" not in df.columns: df["es_credito"]=False
            return df
        return pd.DataFrame(columns=["id","fecha","cliente","caja","cantidad","valor_unitario","monto","es_credito","asesor"])
    except Exception as e: st.error(f"Error:{e}"); return pd.DataFrame(columns=["id","fecha","cliente","caja","cantidad","valor_unitario","monto","es_credito","asesor"])

def guardar_venta(fecha,cliente,caja,cantidad,valor_unitario,monto,es_credito,asesor):
    try:
        get_supabase_client().table("ventas").insert({"fecha":fecha.strftime("%Y-%m-%d"),"cliente":cliente,"caja":caja,"cantidad":int(cantidad),"valor_unitario":int(valor_unitario),"monto":int(monto),"es_credito":es_credito,"asesor":asesor}).execute()
        registrar_historial(asesor,caja,cantidad,"venta",f"Venta {cantidad} uds → '{cliente}'")
        return True
    except Exception as e: st.error(f"Error:{e}"); return False

def cargar_creditos(asesor=None):
    try:
        q=get_supabase_client().table("creditos").select("*")
        if asesor: q=q.eq("asesor",asesor)
        resp=q.execute()
        if resp.data:
            df=pd.DataFrame(resp.data)
            for c in ["fecha_credito","fecha_pago"]:
                if c in df.columns: df[c]=pd.to_datetime(df[c],errors="coerce")
            if "pagado" not in df.columns: df["pagado"]=False
            for c in ["cliente","asesor"]:
                if c not in df.columns: df[c]=""
            if "monto" not in df.columns: df["monto"]=0
            return df
        return pd.DataFrame(columns=["id","cliente","monto","fecha_credito","pagado","fecha_pago","asesor"])
    except Exception as e: st.error(f"Error:{e}"); return pd.DataFrame(columns=["id","cliente","monto","fecha_credito","pagado","fecha_pago","asesor"])

def guardar_credito(cliente,monto,fecha,asesor):
    try: get_supabase_client().table("creditos").insert({"cliente":cliente,"monto":int(monto),"fecha_credito":fecha.strftime("%Y-%m-%d"),"pagado":False,"asesor":asesor}).execute(); return True
    except Exception as e: st.error(f"Error:{e}"); return False

def marcar_credito_pagado(cid):
    try: get_supabase_client().table("creditos").update({"pagado":True,"fecha_pago":datetime.now().strftime("%Y-%m-%d")}).eq("id",cid).execute(); return True
    except Exception as e: st.error(f"Error:{e}"); return False

def buscar_por_serial(serial):
    try:
        sb=get_supabase_client(); res={"equipo":None,"insumo":None,"bateria":None}
        eq=sb.table("equipos").select("*").eq("Serial",serial).execute()
        if eq.data: res["equipo"]=eq.data[0]
        inv=sb.table("inventario").select("*").eq("serial",serial).execute()
        if inv.data: res["insumo"]=inv.data[0]
        bat=sb.table("baterias").select("*").eq("serial",serial).execute()
        if bat.data: res["bateria"]=bat.data[0]
        return res
    except: return {"equipo":None,"insumo":None,"bateria":None}

# ══════════════════════════════════════════════
# SESIÓN
# ══════════════════════════════════════════════
for k,v in [("authenticated",False),("usuario",None),("rol",None),("nombre_usuario",None)]:
    if k not in st.session_state: st.session_state[k]=v

# ══════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════
if not st.session_state.authenticated:
    col1,col2,col3 = st.columns([1,1.2,1])
    with col2:
        st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center;margin-bottom:32px;'>
            <div style='font-size:2.8rem;'>🏥</div>
            <h1 style='color:#e8ecf7;font-size:1.8rem;margin:8px 0 4px;'>Surtidor Médico</h1>
            <p style='color:#6b7a9e;font-size:0.85rem;'>Sistema de Gestión de Inventario</p>
        </div>
        """, unsafe_allow_html=True)
        usuario   = st.text_input("Usuario",    placeholder="Tu usuario")
        contraseña = st.text_input("Contraseña", type="password", placeholder="Tu contraseña")
        if st.button("Iniciar sesión →", use_container_width=True):
            ok,rol,nombre = verificar_usuario(usuario,contraseña)
            if ok:
                st.session_state.authenticated=True
                st.session_state.usuario=usuario
                st.session_state.rol=rol
                st.session_state.nombre_usuario=nombre
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")

else:
    ROL     = st.session_state.rol
    USUARIO = st.session_state.usuario
    NOMBRE  = st.session_state.nombre_usuario

    # ── SIDEBAR ──
    with st.sidebar:
        st.markdown(f"""
        <div style='padding:16px 0 8px;'>
            <div style='font-size:1.05rem;font-weight:700;color:#e8ecf7;'>{NOMBRE}</div>
            <div style='font-size:0.72rem;color:#3b82f6;margin-top:2px;'>
                {'🔑 Administrador' if ROL=='admin' else '🧑‍💼 Asesor'}
            </div>
            <div style='font-size:0.7rem;color:#4b5673;margin-top:4px;'>
                {datetime.now().strftime('%d %b %Y — %H:%M')}
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        if st.button("Cerrar Sesión", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
        st.markdown("---")
        if ROL=="admin":
            menu = st.radio("MENÚ",[
                "Dashboard","Clientes","Insumos","Equipos","Baterías",
                "Asignaciones","Ventas","Créditos","Historial","Reportes"
            ])
        else:
            menu = st.radio("MENÚ",[
                "Mi Resumen","Mis Clientes","Mis Insumos",
                "Mis Equipos","Registrar Venta","Mis Créditos"
            ])

    # ════════════════════════════════════════
    # ADMIN — DASHBOARD
    # ════════════════════════════════════════
    if menu=="Dashboard" and ROL=="admin":
        st.title("Panel de Control")
        clientes_df = get_cached_clientes()
        inventario  = get_cached_inventario()
        ventas      = get_cached_ventas()
        creditos    = get_cached_creditos()
        baterias    = cargar_baterias()
        cred_pend   = creditos[creditos["pagado"]==False]["monto"].sum() if not creditos.empty else 0
        bats_disp   = len(baterias[baterias["estado"]=="Disponible"]) if not baterias.empty else 0

        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: st.metric("Clientes",      len(clientes_df))
        with c2: st.metric("Cajas",         len(inventario))
        with c3: st.metric("Ventas",        f"${ventas['monto'].sum():,.0f}" if not ventas.empty else "$0")
        with c4: st.metric("Pendiente",     f"${cred_pend:,.0f}")
        with c5: st.metric("Baterías disp", bats_disp)

        st.markdown("---")
        cl, cr = st.columns(2)
        with cl:
            st.subheader("🔍 Buscar por Serial")
            sq = st.text_input("Serial", placeholder="EQ-XXXXX / INS-XXXXX / BAT-XXXXX", label_visibility="collapsed")
            if st.button("Buscar", use_container_width=True) and sq:
                res = buscar_por_serial(sq.strip().upper())
                if res["equipo"]:
                    eq=res["equipo"]; st.success(f"🖥️ **{eq.get('Nombre','')}** | {eq.get('Serial','')} | {eq.get('Estado','')}")
                elif res["insumo"]:
                    inv=res["insumo"]; st.success(f"📦 **{inv.get('Caja','')}** | Stock: {int(inv.get('Cantidad',0))}")
                elif res["bateria"]:
                    bat=res["bateria"]; st.success(f"🔋 **{bat.get('nombre','')}** | {bat.get('serial','')}")
                else:
                    st.warning(f"No encontrado: {sq}")
        with cr:
            if not ventas.empty:
                st.subheader("Últimas Ventas")
                vd=ventas.tail(8)[["fecha","asesor","cliente","monto"]].copy()
                vd["fecha"]=pd.to_datetime(vd["fecha"],errors="coerce").dt.strftime("%d/%m")
                vd["monto"]=vd["monto"].apply(lambda x:f"${x:,.0f}")
                st.dataframe(vd, use_container_width=True, hide_index=True)

    # ════════════════════════════════════════
    # ADMIN — CLIENTES
    # ════════════════════════════════════════
    elif menu=="Clientes" and ROL=="admin":
        st.title("Clientes")
        clientes=get_cached_clientes(); asesores=get_cached_asesores()
        tab1,tab2 = st.tabs(["Ver todos","Agregar"])
        with tab1:
            if not clientes.empty:
                fa=st.selectbox("Filtrar asesor",["Todos"]+asesores)
                df_s=clientes if fa=="Todos" else clientes[clientes["asesor"]==fa]
                st.dataframe(df_s[["nombre","cedula","telefono","asesor"]], use_container_width=True, hide_index=True)
                st.markdown("---")
                c1,c2=st.columns(2)
                with c1: sel=st.selectbox("Eliminar cliente",clientes["nombre"].tolist())
                with c2:
                    st.markdown("<div style='height:28px'></div>",unsafe_allow_html=True)
                    if st.button("Eliminar",use_container_width=True):
                        if eliminar_cliente(int(clientes[clientes["nombre"]==sel].iloc[0]["id"])):
                            st.success("Eliminado"); clear_all_cache(); st.rerun()
            else: st.info("Sin clientes registrados")
        with tab2:
            c1,c2=st.columns(2)
            with c1: nombre=st.text_input("Nombre completo"); telefono=st.text_input("Teléfono")
            with c2: cedula=st.text_input("Cédula"); asesor_s=st.selectbox("Asesor",asesores)
            if st.button("Guardar cliente",use_container_width=True):
                if nombre and cedula:
                    if guardar_cliente(nombre,cedula,telefono,asesor_s):
                        st.success("Cliente agregado"); clear_all_cache(); st.rerun()
                else: st.error("Nombre y cédula son obligatorios")

    # ════════════════════════════════════════
    # ADMIN — INSUMOS
    # ════════════════════════════════════════
    elif menu=="Insumos" and ROL=="admin":
        st.title("Insumos — Cajas")
        inventario=get_cached_inventario()
        tab1,tab2,tab3=st.tabs(["🔍 Buscar Items","➕ Nueva Caja","📝 Gestionar Items"])

        with tab1:
            busq=st.text_input("Buscar por nombre, descripción o serial",placeholder="Sensor, SPO2, ITM-ABC123…")
            if not inventario.empty:
                todos=[]
                for _,ri in inventario.iterrows():
                    its=cargar_items_caja(int(ri["id"]))
                    if not its.empty:
                        its=its.copy(); its["nombre_caja"]=ri["Caja"]; todos.append(its)
                if todos:
                    df_t=pd.concat(todos,ignore_index=True)
                    if busq.strip():
                        bn=normalizar(busq)
                        mask=(df_t["nombre"].apply(normalizar).str.contains(bn,na=False)|
                              df_t["descripcion"].apply(normalizar).str.contains(bn,na=False)|
                              df_t.get("serial_item",pd.Series([""]*len(df_t))).apply(normalizar).str.contains(bn,na=False))
                        df_r=df_t[mask]
                    else: df_r=df_t
                    st.caption(f"{'🔎 '+str(len(df_r))+' resultado(s)' if busq.strip() else str(len(df_r))+' items totales'}")
                    if not df_r.empty:
                        for cn in df_r["nombre_caja"].unique():
                            ic=df_r[df_r["nombre_caja"]==cn]; val=calcular_valor_caja(ic)
                            with st.expander(f"📦  {cn}   ·   {len(ic)} item(s)   ·   ${val:,.0f}"):
                                rc=inventario[inventario["Caja"]==cn].iloc[0]
                                c1,c2,c3=st.columns([3,1,1])
                                with c1: nn=st.text_input("Nombre caja",value=str(rc["Caja"]),key=f"rn_{rc['id']}")
                                with c2:
                                    st.markdown("<div style='height:28px'></div>",unsafe_allow_html=True)
                                    if st.button("✏️",key=f"rb_{rc['id']}",use_container_width=True):
                                        if nn and nn!=rc["Caja"]:
                                            if renombrar_caja(int(rc["id"]),nn): clear_all_cache(); st.rerun()
                                with c3:
                                    st.markdown("<div style='height:28px'></div>",unsafe_allow_html=True)
                                    if st.button("🗑️",key=f"dc_{rc['id']}",use_container_width=True):
                                        if eliminar_caja(int(rc["id"])): clear_all_cache(); st.rerun()
                                d=ic[["nombre","descripcion","cantidad","precio_unitario"]].copy()
                                d["subtotal"]=(ic["cantidad"]*ic["precio_unitario"]).apply(lambda x:f"${x:,.0f}")
                                d["cantidad"]=d["cantidad"].apply(lambda x:f"{x} uds")
                                d["precio_unitario"]=d["precio_unitario"].apply(lambda x:f"${x:,.0f}")
                                st.dataframe(d,use_container_width=True,hide_index=True)
                    else: st.warning(f"Sin resultados para '{busq}'")
                else: st.info("No hay items registrados aún")
            else: st.info("Sin cajas")

        with tab2:
            cn2=st.text_input("Nombre de la caja",placeholder="Ej: Sensores SpO2 Adulto")
            if st.button("Crear caja",use_container_width=True):
                if cn2:
                    ok,ser=guardar_caja_nueva(cn2)
                    if ok: st.success(f"Caja creada — Serial: `{ser}`"); clear_all_cache(); st.rerun()
                else: st.error("Ingresa un nombre")

        with tab3:
            if not inventario.empty:
                cs2=st.selectbox("Caja a gestionar",inventario["Caja"].tolist())
                cid=int(inventario[inventario["Caja"]==cs2].iloc[0]["id"])
                items=cargar_items_caja(cid)
                st.markdown("---")
                if not items.empty:
                    st.markdown(f"**Items en '{cs2}'**")
                    for _,item in items.iterrows():
                        with st.expander(f"🔸 {item['nombre']}  ·  x{int(item['cantidad'])}  ·  ${int(item['precio_unitario']):,.0f}/u"):
                            c1,c2=st.columns(2)
                            with c1:
                                nn_i=st.text_input("Nombre",value=str(item["nombre"]),key=f"en_{item['id']}")
                                nd_i=st.text_input("Desc",value=str(item["descripcion"]),key=f"ed_{item['id']}")
                            with c2:
                                nc_i=st.number_input("Cantidad",value=int(item["cantidad"]),min_value=0,key=f"ec_{item['id']}")
                                np_i=st.number_input("Precio",value=int(item["precio_unitario"]),step=100,key=f"ep_{item['id']}")
                            cs3,cd=st.columns(2)
                            with cs3:
                                if st.button("Guardar",key=f"si_{item['id']}",use_container_width=True):
                                    if actualizar_item_caja(int(item["id"]),{"nombre":nn_i,"descripcion":nd_i,"cantidad":int(nc_i),"precio_unitario":int(np_i)}):
                                        st.success("Actualizado"); st.rerun()
                            with cd:
                                if st.button("Eliminar",key=f"di_{item['id']}",use_container_width=True):
                                    if eliminar_item_caja(int(item["id"])): st.rerun()
                    st.markdown("---")
                st.markdown("**Agregar item**")
                c1,c2=st.columns(2)
                with c1:
                    i_n=st.text_input("Nombre",placeholder="Sensor SpO2",key=f"in_{cid}")
                    i_d=st.text_input("Descripción",placeholder="Adulto reutilizable",key=f"id_{cid}")
                with c2:
                    i_c=st.number_input("Cantidad",min_value=1,value=1,key=f"ic_{cid}")
                    i_p=st.number_input("Precio ($)",min_value=0,value=1000,step=100,key=f"ip_{cid}")
                if st.button("Agregar item",use_container_width=True):
                    if i_n and i_p>0:
                        ok,_=guardar_item_caja(cid,i_n,i_d,i_c,i_p)
                        if ok: st.success("Item agregado"); st.rerun()
                    else: st.error("Nombre y precio son obligatorios")
            else: st.warning("Crea una caja primero")

    # ════════════════════════════════════════
    # ADMIN — EQUIPOS
    # ════════════════════════════════════════
    elif menu=="Equipos" and ROL=="admin":
        st.title("Equipos")
        equipos=cargar_equipos(); asesores=get_cached_asesores()
        tab1,tab2=st.tabs(["Ver equipos","Agregar"])
        with tab1:
            if not equipos.empty:
                fe=st.selectbox("Estado",["Todos"]+ESTADOS_EQUIPO)
                ef=equipos if fe=="Todos" else equipos[equipos["Estado"]==fe]
                for _,row in ef.iterrows():
                    with st.expander(f"{COLOR_ESTADO.get(row['Estado'],'⚪')}  {row['Nombre']}   |   {row['Serial']}"):
                        c1,c2=st.columns(2)
                        with c1: st.caption("Precio"); st.write(f"${int(row.get('Precio',0)):,.0f}")
                        with c2: st.caption("Cliente"); st.write(row.get("Cliente_Asignado","—"))
                        idx_e=ESTADOS_EQUIPO.index(row["Estado"]) if row["Estado"] in ESTADOS_EQUIPO else 0
                        ne=st.selectbox("Estado",ESTADOS_EQUIPO,index=idx_e,key=f"e_{row['id']}")
                        oa=[""]+asesores; ia=oa.index(row.get("Asesor_Asignado","")) if row.get("Asesor_Asignado","") in oa else 0
                        na=st.selectbox("Asesor",oa,index=ia,key=f"a_{row['id']}")
                        nc=st.text_input("Comentario",value=str(row.get("Comentarios","")),key=f"c_{row['id']}")
                        ca,cb=st.columns(2)
                        with ca:
                            if st.button("Guardar",key=f"u_{row['id']}",use_container_width=True):
                                if actualizar_equipo(int(row["id"]),{"Estado":ne,"Asesor_Asignado":na,"Comentarios":nc}):
                                    st.success("Actualizado"); st.rerun()
                        with cb:
                            if st.button("Eliminar",key=f"d_{row['id']}",use_container_width=True):
                                if eliminar_equipo(int(row["id"])): st.rerun()
            else: st.info("Sin equipos")
        with tab2:
            c1,c2=st.columns(2)
            with c1: ne2=st.text_input("Nombre"); se2=st.text_input("Serial (opcional)")
            with c2: pe2=st.number_input("Precio ($)",min_value=0,value=0,step=1000); ee2=st.selectbox("Estado inicial",ESTADOS_EQUIPO)
            ae2=st.selectbox("Asesor",[""])
            ce2=st.text_input("Cliente (opcional)")
            if st.button("Agregar equipo",use_container_width=True):
                if ne2:
                    sf=se2 or generar_serial("EQ")
                    ok,sr=guardar_equipo_nuevo({"Nombre":ne2,"Serial":sf,"Estado":ee2,"Precio":int(pe2),"Asesor_Asignado":ae2,"Cliente_Asignado":ce2})
                    if ok: st.success(f"Equipo agregado — Serial: `{sr}`"); st.rerun()
                else: st.error("El nombre es obligatorio")

    # ════════════════════════════════════════
    # ADMIN — BATERÍAS
    # ════════════════════════════════════════
    elif menu=="Baterías" and ROL=="admin":
        st.title("Baterías")
        baterias=cargar_baterias()
        if not baterias.empty:
            c1,c2,c3,c4=st.columns(4)
            with c1: st.metric("Total",len(baterias))
            with c2: st.metric("Disponibles",len(baterias[baterias["estado"]=="Disponible"]))
            with c3: st.metric("En Uso",len(baterias[baterias["estado"]=="En uso"]))
            with c4: st.metric("Dañadas",len(baterias[baterias["estado"]=="Dañada"]))
            st.markdown("---")
        tab1,tab2,tab3=st.tabs(["Ver","Agregar","Estadísticas"])
        with tab1:
            if not baterias.empty:
                fb=st.selectbox("Estado",["Todos"]+ESTADOS_BATERIA)
                bf=baterias if fb=="Todos" else baterias[baterias["estado"]==fb]
                for _,row in bf.iterrows():
                    eb=row.get("estado","")
                    with st.expander(f"{COLOR_BATERIA.get(eb,'⚪')}  {row['nombre']}   |   {row['serial']}"):
                        c1,c2=st.columns(2)
                        with c1: st.write(f"**Proveedor:** {row.get('proveedor','—')}")
                        with c2: st.write(f"**Costo:** ${int(row.get('costo',0)):,.0f}")
                        idx_eb=ESTADOS_BATERIA.index(eb) if eb in ESTADOS_BATERIA else 0
                        neb=st.selectbox("Estado",ESTADOS_BATERIA,index=idx_eb,key=f"bst_{row['id']}")
                        if st.button("Actualizar",key=f"bupd_{row['id']}",use_container_width=True):
                            if actualizar_bateria(int(row["id"]),{"estado":neb}):
                                st.success("Actualizado"); st.rerun()
            else: st.info("Sin baterías")
        with tab2:
            c1,c2=st.columns(2)
            with c1: nb_n=st.text_input("Nombre / Modelo"); nb_p=st.text_input("Proveedor")
            with c2: nb_c=st.number_input("Costo ($)",min_value=0,value=0,step=1000); nb_e=st.selectbox("Estado",ESTADOS_BATERIA)
            if st.button("Registrar batería",use_container_width=True):
                if nb_n and nb_p:
                    ok,sb_s=guardar_bateria(nb_n,nb_p,datetime.now().date(),0,nb_c,nb_e,"","","")
                    if ok: st.success(f"Registrada — Serial: `{sb_s}`"); st.rerun()
                else: st.error("Nombre y proveedor son obligatorios")
        with tab3:
            if not baterias.empty:
                ec=baterias["estado"].value_counts()
                fig=px.pie(values=ec.values,names=ec.index,color_discrete_sequence=["#3b82f6","#22c55e","#ef4444","#f59e0b","#6b7280"])
                fig.update_layout(paper_bgcolor="#151822",plot_bgcolor="#151822",font_color="#c9d1e8")
                st.plotly_chart(fig,use_container_width=True)

    # ════════════════════════════════════════
    # ADMIN — ASIGNACIONES (+ comentario + auto-asignación)
    # ════════════════════════════════════════
    elif menu=="Asignaciones" and ROL=="admin":
        st.title("Asignaciones")
        asesores=get_cached_asesores(); inventario=get_cached_inventario()
        tab1,tab2=st.tabs(["Ver asignaciones","Nueva asignación"])

        with tab1:
            asignaciones=get_cached_asignaciones()
            if not asignaciones.empty:
                fas=st.selectbox("Filtrar asesor",["Todos"]+asesores)
                df_as=asignaciones if fas=="Todos" else asignaciones[asignaciones["asesor"]==fas]
                lista_a=asesores if fas=="Todos" else [fas]
                for asesor in lista_a:
                    asig=df_as[df_as["asesor"]==asesor]
                    if asig.empty: continue
                    with st.expander(f"🧑‍💼  {asesor}   ·   {int(asig['cantidad'].sum())} uds   ·   {len(asig)} registro(s)"):
                        for _,arow in asig.iterrows():
                            c1,c2,c3,c4=st.columns([2,1,3,1])
                            with c1: st.write(f"📦 **{arow['caja']}**")
                            with c2: st.write(f"{int(arow['cantidad'])} uds")
                            with c3:
                                com=arow.get("comentario","") or ""
                                if com: st.caption(f"💬 {com}")
                            with c4:
                                if st.button("Eliminar",key=f"da_{arow['id']}",use_container_width=True):
                                    try:
                                        get_supabase_client().table("asignaciones").delete().eq("id",int(arow["id"])).execute()
                                        clear_all_cache(); st.rerun()
                                    except Exception as e: st.error(e)
            else: st.info("Sin asignaciones registradas")

        with tab2:
            if not inventario.empty:
                c1,c2=st.columns(2)
                with c1:
                    # ✅ Cualquier asesor se puede asignar a sí mismo o a otro
                    ad=st.selectbox("Asesor destinatario",asesores,key="na_asesor")
                with c2:
                    cs_a=st.selectbox("Caja",inventario["Caja"].tolist(),key="na_caja")
                disp=int(inventario[inventario["Caja"]==cs_a].iloc[0]["Cantidad"])
                c3,c4=st.columns(2)
                with c3: ca2=st.number_input("Cantidad",min_value=1,max_value=max(disp,1),value=1)
                with c4: st.metric("Stock disponible",disp)
                fa2=st.date_input("Fecha")
                # ✅ Comentario en la asignación
                com2=st.text_input("Comentario (opcional)",placeholder="Ej: Ruta norte, reponer stock…")
                if st.button("Asignar",use_container_width=True):
                    if ca2<=disp:
                        rc=inventario[inventario["Caja"]==cs_a].iloc[0]
                        actualizar_caja(int(rc["id"]),{"Cantidad":disp-ca2})
                        if guardar_asignacion(ad,cs_a,ca2,fa2,com2):
                            st.success(f"✅ {ca2} uds de '{cs_a}' asignadas a {ad}")
                            clear_all_cache(); st.rerun()
                    else: st.error("Stock insuficiente")
            else: st.error("No hay cajas registradas")

    # ════════════════════════════════════════
    # ADMIN — VENTAS
    # ════════════════════════════════════════
    elif menu=="Ventas" and ROL=="admin":
        st.title("Ventas")
        inventario=get_cached_inventario(); clientes=get_cached_clientes(); asesores=get_cached_asesores()
        tab1,tab2=st.tabs(["Nueva venta","Historial"])
        with tab1:
            c1,c2=st.columns(2)
            with c1: fecha=st.date_input("Fecha")
            with c2: av=st.selectbox("Asesor",asesores)
            cli_f=clientes[clientes["asesor"]==av] if not clientes.empty else pd.DataFrame()
            lcli=cli_f["nombre"].tolist() if not cli_f.empty else []
            cv=st.selectbox("Cliente",lcli if lcli else ["Sin clientes"])
            c3,c4=st.columns(2)
            with c3: cajav=st.selectbox("Caja",inventario["Caja"].tolist() if not inventario.empty else ["Sin cajas"])
            with c4:
                if not inventario.empty and cajav!="Sin cajas":
                    st.metric("Stock",int(inventario[inventario["Caja"]==cajav].iloc[0]["Cantidad"]))
            c5,c6=st.columns(2)
            with c5: cantv=st.number_input("Cantidad",min_value=1,value=1)
            with c6:
                valu=0
                if not inventario.empty and cajav!="Sin cajas":
                    cid4=int(inventario[inventario["Caja"]==cajav].iloc[0]["id"])
                    itms=cargar_items_caja(cid4)
                    valu=int(itms["precio_unitario"].mean()) if not itms.empty else 0
                st.metric("Precio unitario",f"${valu:,.0f}")
            montov=cantv*valu; st.metric("Monto total",f"${montov:,.0f}")
            ecv=st.checkbox("Venta a crédito")
            if st.button("Registrar venta",use_container_width=True):
                if cv!="Sin clientes" and cajav!="Sin cajas":
                    crow=inventario[inventario["Caja"]==cajav].iloc[0]
                    nc=int(crow["Cantidad"])-cantv
                    if nc<0: st.error("Stock insuficiente")
                    else:
                        actualizar_caja(int(crow["id"]),{"Cantidad":nc})
                        guardar_venta(fecha,cv,cajav,cantv,valu,montov,ecv,av)
                        if ecv: guardar_credito(cv,montov,fecha,av)
                        st.success("Venta registrada"); clear_all_cache(); st.rerun()
                else: st.error("Completa todos los campos")
        with tab2:
            ventas=get_cached_ventas()
            if not ventas.empty:
                vd=ventas[["fecha","asesor","cliente","caja","cantidad","monto"]].copy()
                vd["fecha"]=pd.to_datetime(vd["fecha"],errors="coerce").dt.strftime("%d/%m/%Y")
                vd["monto"]=vd["monto"].apply(lambda x:f"${x:,.0f}")
                st.dataframe(vd,use_container_width=True,hide_index=True)
            else: st.info("Sin ventas")

    # ════════════════════════════════════════
    # ADMIN — CRÉDITOS
    # ════════════════════════════════════════
    elif menu=="Créditos" and ROL=="admin":
        st.title("Créditos")
        creditos=get_cached_creditos(); asesores_c=get_cached_asesores()
        if not creditos.empty:
            pend=creditos[creditos["pagado"]==False]
            c1,c2,c3=st.columns(3)
            with c1: st.metric("Monto pendiente",f"${pend['monto'].sum():,.0f}")
            with c2: st.metric("Clientes con deuda",pend["cliente"].nunique())
            with c3: st.metric("Registros",len(pend))
            st.markdown("---")
            filtro=st.selectbox("Filtrar asesor",["Todos"]+asesores_c)
            for ac in (asesores_c if filtro=="Todos" else [filtro]):
                ca=creditos[creditos["asesor"]==ac]
                if ca.empty: continue
                tot=ca[ca["pagado"]==False]["monto"].sum()
                with st.expander(f"🧑‍💼  {ac}   ·   Pendiente: ${tot:,.0f}"):
                    for _,row in ca.iterrows():
                        c1,c2,c3,c4=st.columns([2,1.5,1.5,1])
                        with c1: st.write(f"👤 {row['cliente']}")
                        with c2: st.write(f"${int(row['monto']):,.0f}")
                        with c3:
                            fc=row["fecha_credito"].strftime("%d/%m/%Y") if pd.notna(row["fecha_credito"]) else "—"
                            st.write(fc)
                        with c4:
                            if row["pagado"]: st.caption("✓")
                            else:
                                if st.button("Pagar",key=f"p_{row['id']}",use_container_width=True):
                                    if marcar_credito_pagado(int(row["id"])): clear_all_cache(); st.rerun()
        else: st.info("Sin créditos")

    # ════════════════════════════════════════
    # ADMIN — HISTORIAL
    # ════════════════════════════════════════
    elif menu=="Historial" and ROL=="admin":
        st.title("Historial de Movimientos")
        st.caption("Asignaciones y ventas — los créditos tienen su propio módulo.")
        historial=cargar_historial_asignaciones()
        if not historial.empty:
            c1,c2,c3=st.columns(3)
            with c1: st.metric("Total registros",len(historial))
            with c2: st.metric("Ventas",len(historial[historial["tipo"]=="venta"]))
            with c3: st.metric("Asignaciones",len(historial[historial["tipo"]=="asignacion"]))
            st.markdown("---")
            cf1,cf2,cf3=st.columns(3)
            with cf1: ft=st.selectbox("Tipo",["Todos"]+historial["tipo"].unique().tolist())
            with cf2: fa=st.selectbox("Asesor",["Todos"]+historial["asesor"].unique().tolist())
            with cf3: fn=st.selectbox("Mostrar",[20,50,100,200],index=0)
            hf=historial.copy()
            if ft!="Todos": hf=hf[hf["tipo"]==ft]
            if fa!="Todos": hf=hf[hf["asesor"]==fa]
            hs=hf.head(fn)[["fecha","asesor","tipo","caja","cantidad","nota"]].copy()
            hs["fecha"]=hs["fecha"].dt.strftime("%d/%m/%Y %H:%M")
            st.dataframe(hs,use_container_width=True,hide_index=True)
        else: st.info("Sin registros aún")

    # ════════════════════════════════════════
    # ADMIN — REPORTES
    # ════════════════════════════════════════
    elif menu=="Reportes" and ROL=="admin":
        st.title("Reportes")
        ventas=get_cached_ventas()
        if not ventas.empty:
            c1,c2,c3=st.columns(3)
            with c1: st.metric("Ventas totales",f"${ventas['monto'].sum():,.0f}")
            with c2: st.metric("Nº de ventas",len(ventas))
            with c3: st.metric("Ticket promedio",f"${ventas['monto'].mean():,.0f}")
            st.markdown("---")
            cl,cr=st.columns(2)
            with cl:
                st.subheader("Ventas por Asesor")
                va=ventas.groupby("asesor")["monto"].sum().reset_index()
                fig1=px.bar(va,x="asesor",y="monto",color="monto",color_continuous_scale=["#1e2d4a","#3b82f6"])
                fig1.update_layout(paper_bgcolor="#151822",plot_bgcolor="#151822",font_color="#c9d1e8",showlegend=False)
                st.plotly_chart(fig1,use_container_width=True)
            with cr:
                st.subheader("Evolución de Ventas")
                ventas["mes"]=pd.to_datetime(ventas["fecha"],errors="coerce").dt.to_period("M").astype(str)
                vm=ventas.groupby("mes")["monto"].sum().reset_index()
                fig2=px.line(vm,x="mes",y="monto",markers=True,color_discrete_sequence=["#3b82f6"])
                fig2.update_layout(paper_bgcolor="#151822",plot_bgcolor="#151822",font_color="#c9d1e8")
                st.plotly_chart(fig2,use_container_width=True)
        else: st.info("Sin datos de ventas aún")

    # ════════════════════════════════════════════════════
    # ASESOR — helper selector
    # ════════════════════════════════════════════════════
    # ✅ Cada módulo del asesor tiene selector de asesor
    # → por defecto apunta al usuario logueado
    # → puede seleccionar a cualquier otro asesor
    # → así Oscar se asigna a sí mismo, Lucy también,
    #   y pueden verse/asignarse entre ellos

    elif menu=="Mi Resumen" and ROL=="asesor":
        todos=get_cached_asesores()
        av=st.selectbox("Ver como",todos,index=todos.index(USUARIO) if USUARIO in todos else 0,key="res_av")
        st.title(f"Resumen — {av}")
        mv=cargar_ventas(asesor=av); mc=cargar_creditos(asesor=av); mcli=cargar_clientes(asesor=av)
        pend=mc[mc["pagado"]==False] if not mc.empty else pd.DataFrame()
        c1,c2,c3=st.columns(3)
        with c1: st.metric("Clientes",len(mcli))
        with c2: st.metric("Ventas",f"${mv['monto'].sum():,.0f}" if not mv.empty else "$0")
        with c3: st.metric("Crédito pendiente",f"${pend['monto'].sum():,.0f}" if not pend.empty else "$0")
        if not mv.empty:
            st.markdown("---"); st.subheader("Últimas ventas")
            vd=mv.tail(8)[["fecha","cliente","caja","monto"]].copy()
            vd["fecha"]=pd.to_datetime(vd["fecha"],errors="coerce").dt.strftime("%d/%m/%Y")
            vd["monto"]=vd["monto"].apply(lambda x:f"${x:,.0f}")
            st.dataframe(vd,use_container_width=True,hide_index=True)

    elif menu=="Mis Clientes" and ROL=="asesor":
        todos=get_cached_asesores()
        av=st.selectbox("Asesor",todos,index=todos.index(USUARIO) if USUARIO in todos else 0,key="cli_av")
        st.title(f"Clientes — {av}")
        mc=cargar_clientes(asesor=av)
        tab1,tab2=st.tabs(["Ver","Agregar"])
        with tab1:
            if not mc.empty: st.dataframe(mc[["nombre","cedula","telefono"]],use_container_width=True,hide_index=True)
            else: st.info("Sin clientes")
        with tab2:
            nombre=st.text_input("Nombre")
            c1,c2=st.columns(2)
            with c1: cedula=st.text_input("Cédula")
            with c2: telefono=st.text_input("Teléfono")
            if st.button("Guardar cliente",use_container_width=True):
                if nombre and cedula:
                    if guardar_cliente(nombre,cedula,telefono,av):
                        st.success("Guardado"); clear_all_cache(); st.rerun()
                else: st.error("Nombre y cédula son obligatorios")

    elif menu=="Mis Insumos" and ROL=="asesor":
        todos=get_cached_asesores()
        av=st.selectbox("Asesor",todos,index=todos.index(USUARIO) if USUARIO in todos else 0,key="ins_av")
        st.title(f"Insumos — {av}")
        ma=cargar_asignaciones(asesor=av)
        if not ma.empty:
            st.metric("Total unidades",int(ma["cantidad"].sum()))
            st.markdown("---")
            for _,arow in ma.iterrows():
                c1,c2,c3=st.columns([2,1,3])
                with c1: st.write(f"📦 **{arow['caja']}**")
                with c2: st.write(f"{int(arow['cantidad'])} uds")
                with c3:
                    com=arow.get("comentario","") or ""
                    if com: st.caption(f"💬 {com}")
        else: st.info("Sin insumos asignados")

    elif menu=="Mis Equipos" and ROL=="asesor":
        todos=get_cached_asesores()
        av=st.selectbox("Asesor",todos,index=todos.index(USUARIO) if USUARIO in todos else 0,key="eq_av")
        st.title(f"Equipos — {av}")
        me=cargar_equipos(asesor=av)
        if not me.empty:
            for _,row in me.iterrows():
                with st.expander(f"{COLOR_ESTADO.get(row['Estado'],'⚪')}  {row['Nombre']}"):
                    c1,c2=st.columns(2)
                    with c1: st.write(f"**Precio:** ${int(row.get('Precio',0)):,.0f}")
                    with c2: st.write(f"**Cliente:** {row.get('Cliente_Asignado','—')}")
        else: st.info("Sin equipos asignados")

    elif menu=="Registrar Venta" and ROL=="asesor":
        st.title("Registrar Venta")
        todos=get_cached_asesores()
        av=st.selectbox("Asesor de la venta",todos,index=todos.index(USUARIO) if USUARIO in todos else 0,key="vta_av")
        inventario=get_cached_inventario(); mcli=cargar_clientes(asesor=av); ma=cargar_asignaciones(asesor=av)
        c1,c2=st.columns(2)
        with c1: fecha=st.date_input("Fecha")
        with c2:
            lcli=mcli["nombre"].tolist() if not mcli.empty else []
            cv=st.selectbox("Cliente",lcli if lcli else ["Sin clientes"])
        cajas_d=ma["caja"].unique().tolist() if not ma.empty else []
        c3,c4=st.columns(2)
        with c3: cajav=st.selectbox("Caja",cajas_d if cajas_d else ["Sin cajas"])
        with c4:
            if cajas_d and not inventario.empty and cajav in inventario["Caja"].values:
                st.metric("Stock",int(inventario[inventario["Caja"]==cajav].iloc[0]["Cantidad"]))
        c5,c6=st.columns(2)
        with c5: cantv=st.number_input("Cantidad",min_value=1,value=1)
        with c6:
            valu=0
            if cajas_d and not inventario.empty and cajav in inventario["Caja"].values:
                cid5=int(inventario[inventario["Caja"]==cajav].iloc[0]["id"])
                itms=cargar_items_caja(cid5)
                valu=int(itms["precio_unitario"].mean()) if not itms.empty else 0
            st.metric("Precio",f"${valu:,.0f}")
        montov=cantv*valu; st.metric("Total",f"${montov:,.0f}")
        ecv=st.checkbox("Venta a crédito")
        if st.button("Registrar venta",use_container_width=True):
            if cv!="Sin clientes" and cajav!="Sin cajas":
                crow=inventario[inventario["Caja"]==cajav].iloc[0]
                nc=int(crow["Cantidad"])-cantv
                if nc<0: st.error("Stock insuficiente")
                else:
                    actualizar_caja(int(crow["id"]),{"Cantidad":nc})
                    guardar_venta(fecha,cv,cajav,cantv,valu,montov,ecv,av)
                    if ecv: guardar_credito(cv,montov,fecha,av)
                    st.success("Venta registrada"); clear_all_cache(); st.rerun()
            else: st.error("Completa todos los campos")

    elif menu=="Mis Créditos" and ROL=="asesor":
        todos=get_cached_asesores()
        av=st.selectbox("Asesor",todos,index=todos.index(USUARIO) if USUARIO in todos else 0,key="cred_av")
        st.title(f"Créditos — {av}")
        mc=cargar_creditos(asesor=av)
        if not mc.empty:
            pend=mc[mc["pagado"]==False]
            c1,c2=st.columns(2)
            with c1: st.metric("Pendiente",f"${pend['monto'].sum():,.0f}" if not pend.empty else "$0")
            with c2: st.metric("Registros",len(pend))
            st.markdown("---")
            for _,row in mc.iterrows():
                c1,c2,c3,c4=st.columns([2,1.5,1.5,1])
                with c1: st.write(f"👤 {row['cliente']}")
                with c2: st.write(f"${int(row['monto']):,.0f}")
                with c3:
                    fc=row["fecha_credito"].strftime("%d/%m/%Y") if pd.notna(row["fecha_credito"]) else "—"
                    st.write(fc)
                with c4:
                    if row["pagado"]: st.caption("✓")
                    else:
                        if st.button("Pagar",key=f"pa_{row['id']}",use_container_width=True):
                            if marcar_credito_pagado(int(row["id"])): clear_all_cache(); st.rerun()
        else: st.info("Sin créditos")