import requests
from bs4 import BeautifulSoup
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
from plyer import notification
import winsound
import pandas as pd
import pandas as pd
import plotly.graph_objects as go
import os

# ==================================================
# CONFIGURACION PAGINA
# ==================================================

st.set_page_config(
    page_title="Monitor Divisas Tesorería",
    page_icon="💵",
    layout="wide"
)

# ==================================================
# AUTOREFRESH
# ==================================================

contador_refresh = st_autorefresh(
    interval=15000,
    key="refresh"
)

# ==================================================
# SESSION STATE
# ==================================================

if "alerta_compra" not in st.session_state:
    st.session_state.alerta_compra = False

if "alerta_venta" not in st.session_state:
    st.session_state.alerta_venta = False

if "historial" not in st.session_state:
    st.session_state.historial = []

if "ultimo_spot" not in st.session_state:
    st.session_state.ultimo_spot = None

if "historico_spot" not in st.session_state:
    st.session_state.historico_spot = []

# ==================================================
# NOTIFICACIONES
# ==================================================

def lanzar_alerta(tipo, precio):

    try:

        if tipo == "compra":

            st.toast("🔔 Nivel de compra alcanzado")

            winsound.Beep(
                1200,
                1000
            )

            notification.notify(
                title="💵 Monitor Divisas",
                message=f"Compra alcanzada - SPOT ${precio:,.2f}",
                timeout=10
            )

        elif tipo == "venta":

            st.toast("🚨 Nivel de venta alcanzado")

            winsound.Beep(
                1800,
                1000
            )

            notification.notify(
                title="💵 Monitor Divisas",
                message=f"Venta alcanzada - SPOT ${precio:,.2f}",
                timeout=10
            )

    except Exception as e:

        print(
            f"Error notificación: {e}"
        )

# ==================================================
# WILKINSON SPOT
# ==================================================

@st.cache_data(ttl=15)
def obtener_spot():

    try:

        url = (
            "https://dolar.wilkinsonpc.com.co/"
            "dolar-hoy-spot-minuto-a-minuto/"
        )

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        respuesta = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        soup = BeautifulSoup(
            respuesta.text,
            "html.parser"
        )

        valor = soup.select_one(
            "div.display-6.fw-bold.text-secondary.lh-1.my-1"
        )

        if valor:

            spot = float(
                valor.text
                .replace("$", "")
                .replace(",", "")
                .strip()
            )

            return spot, True

    except Exception as e:

        print(e)

    return 0.0, False

# ==================================================
# TRM OFICIAL
# ==================================================

@st.cache_data(ttl=3600)
def obtener_trm():

    try:

        url = (
            "https://www.datos.gov.co/resource/32sa-8pi3.json"
            "?$order=vigenciadesde DESC"
            "&$limit=1"
        )

        data = requests.get(
            url,
            timeout=20
        ).json()

        trm = float(
            data[0]["valor"]
        )

        fecha = (
            data[0]["vigenciadesde"]
            .split("T")[0]
        )

        return trm, fecha, True

    except Exception as e:

        print(e)

        return 0.0, "", False
# ==================================================
# DATOS
# ==================================================

spot, conectado = obtener_spot()
trm, fecha_trm, conectado_trm = obtener_trm()

archivo_historico = (
    f"historico_trm_{datetime.now().strftime('%Y%m%d')}.csv"
)

nuevo_registro = pd.DataFrame([
    {
        "hora": datetime.now(),
        "spot": spot,
        "apertura": trm,
        "diferencial": spot - trm
    }
])

if os.path.exists(archivo_historico):

    historico_csv = pd.read_csv(
        archivo_historico
    )

    ultimo_minuto = None

    if len(historico_csv) > 0:

        ultima_hora = pd.to_datetime(
            historico_csv.iloc[-1]["hora"]
        )

        ultimo_minuto = (
            ultima_hora.strftime("%Y-%m-%d %H:%M")
        )

    minuto_actual = (
        datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    if ultimo_minuto != minuto_actual:

        nuevo_registro.to_csv(
            archivo_historico,
            mode="a",
            header=False,
            index=False
        )

else:

    nuevo_registro.to_csv(
        archivo_historico,
        index=False
    )

st.session_state.historico_spot.append(
    {
        "hora": datetime.now(),
        "spot": spot
    }
)

if len(st.session_state.historico_spot) > 500:
    st.session_state.historico_spot = (
        st.session_state.historico_spot[-500:]
    )

if not conectado:

    st.error(
        "🔴 No fue posible conectar con Wilkinson Spot."
    )

    st.stop()

# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.title("⚙️ Configuración")

ajuste_banco = st.sidebar.number_input(
    "Ajuste Banco ($)",
    value=10
)

objetivo_compra = st.sidebar.number_input(
    "Nivel deseado de compra",
    value=0.0,
    step=1.0
)

objetivo_venta = st.sidebar.number_input(
    "Nivel deseado de venta",
    value=0.0,
    step=1.0
)

prealerta = st.sidebar.number_input(
    "Margen de prealerta ($)",
    value=20.0,
    min_value=1.0
)

activar_alertas = st.sidebar.checkbox(
    "Activar alertas",
    value=True
)

st.sidebar.divider()

if st.sidebar.button("🔔 Probar Notificación"):

    lanzar_alerta(
        "compra",
        spot
    )

# ==================================================
# CALCULOS
# ==================================================

tasa_banco = spot - ajuste_banco

if st.session_state.ultimo_spot is None:
    variacion = 0
else:
    variacion = spot - st.session_state.ultimo_spot

# ==================================================
# TITULO
# ==================================================

st.title("💵 Monitor Divisas Tesorería")

st.caption(
    f"Última actualización: "
    f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
)

st.caption(
    f"Refrescos realizados: {contador_refresh}"
)

st.success(
    "🟢 Fuente Wilkinson Trm del Día"
)

# ==================================================
# KPIs
# ==================================================

spread_trm = spot - trm

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric(
    "Tasa Apertura",
    f"${trm:,.2f}"
)

k2.metric(
    "TRM del Día",
    f"${spot:,.2f}",
    f"{variacion:+.2f}"
)

k3.metric(
    "Dif. Apertura",
    f"${spread_trm:,.2f}",
    f"{spread_trm:+.2f}"
)

k4.metric(
    "Compra",
    f"${objetivo_compra:,.0f}"
)

k5.metric(
    "Venta",
    f"${objetivo_venta:,.0f}"
)

# ==================================================
# GRAFICA INTRADIA
# ==================================================

st.divider()

st.subheader("📈 Comportamiendo Dolar")

archivo_historico = (
    f"historico_trm_{datetime.now().strftime('%Y%m%d')}.csv"
)

if os.path.exists(archivo_historico):

    df_grafica = pd.read_csv(
        archivo_historico
    )

    if len(df_grafica) > 1:

        df_grafica["hora"] = pd.to_datetime(
            df_grafica["hora"]
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Máximo",
            f"${df_grafica['spot'].max():,.2f}"
        )

        col2.metric(
            "Mínimo",
            f"${df_grafica['spot'].min():,.2f}"
        )

        col3.metric(
            "Rango",
            f"${df_grafica['spot'].max() - df_grafica['spot'].min():,.2f}"
        )

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df_grafica["hora"],
                y=df_grafica["spot"],
                mode="lines",
                name="TRM del Día",
                line=dict(
                    color="white",
                    width=3
                )
            )
        )

        fig.add_hline(
            y=trm,
            line_dash="dash",
            line_color="orange",
            annotation_text=f"Apertura ${trm:,.2f}"
        )

        fig.update_layout(
            height=450,
            template="plotly_dark",
            showlegend=False
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        st.info(
            "Esperando más lecturas para construir la gráfica."
        )

else:

    st.info(
        "Aún no existe histórico para hoy."
    )
# ==================================================
# SITUACION OPERATIVA
# ==================================================

st.divider()

st.subheader(
    "📍 Situación Operativa"
)

# ==================================================
# COMPRA
# ==================================================

if objetivo_compra > 0:

    st.markdown(
        "### 🟢 Compra"
    )

    diferencia_compra = (
        spot - objetivo_compra
    )

    if spot <= objetivo_compra:

        mejora = (
            objetivo_compra - spot
        )

        st.success(
            f"""
✅ Nivel de compra alcanzado

Objetivo: ${objetivo_compra:,.2f}

SPOT actual: ${spot:,.2f}

Mejora: ${mejora:,.2f}
"""
        )

        if not st.session_state.alerta_compra:

            if activar_alertas:

                lanzar_alerta(
                    "compra",
                    spot
                )

            st.session_state.historial.append(
                f"{datetime.now().strftime('%H:%M:%S')} - Compra alcanzada (${spot:,.2f})"
            )

            st.session_state.alerta_compra = True

    elif spot <= (
        objetivo_compra + prealerta
    ):

        st.warning(
            f"""
⚠️ Cerca del nivel de compra

Objetivo: ${objetivo_compra:,.2f}

SPOT: ${spot:,.2f}

Diferencia: ${diferencia_compra:,.2f}
"""
        )

        st.session_state.alerta_compra = False

    else:

        st.info(
            f"""
⚪ Compra pendiente

Objetivo: ${objetivo_compra:,.2f}

SPOT: ${spot:,.2f}

Diferencia: ${diferencia_compra:,.2f}
"""
        )

        st.session_state.alerta_compra = False

# ==================================================
# VENTA
# ==================================================

if objetivo_venta > 0:

    st.markdown(
        "### 🔴 Venta"
    )

    diferencia_venta = (
        objetivo_venta - spot
    )

    if spot >= objetivo_venta:

        mejora = (
            spot - objetivo_venta
        )

        st.error(
            f"""
🚨 Nivel de venta alcanzado

Objetivo: ${objetivo_venta:,.2f}

SPOT actual: ${spot:,.2f}

Mejora: ${mejora:,.2f}
"""
        )

        if not st.session_state.alerta_venta:

            if activar_alertas:

                lanzar_alerta(
                    "venta",
                    spot
                )

            st.session_state.historial.append(
                f"{datetime.now().strftime('%H:%M:%S')} - Venta alcanzada (${spot:,.2f})"
            )

            st.session_state.alerta_venta = True

    elif spot >= (
        objetivo_venta - prealerta
    ):

        st.warning(
            f"""
⚠️ Cerca del nivel de venta

Objetivo: ${objetivo_venta:,.2f}

SPOT: ${spot:,.2f}

Diferencia: ${diferencia_venta:,.2f}
"""
        )

        st.session_state.alerta_venta = False

    else:

        st.info(
            f"""
⚪ Venta pendiente

Objetivo: ${objetivo_venta:,.2f}

SPOT: ${spot:,.2f}

Diferencia: ${diferencia_venta:,.2f}
"""
        )

        st.session_state.alerta_venta = False

# ==================================================
# SIN OBJETIVOS
# ==================================================

if (
    objetivo_compra == 0
    and objetivo_venta == 0
):

    st.info(
        "Configure un objetivo de compra o venta."
    )

# ==================================================
# HISTORIAL
# ==================================================

st.divider()

st.subheader(
    "📋 Historial de Alertas"
)

if len(
    st.session_state.historial
) == 0:

    st.info(
        "No existen alertas registradas."
    )

else:

    for alerta in reversed(
        st.session_state.historial
    ):

        st.write(alerta)

# ==================================================
# FOOTER
# ==================================================

st.session_state.ultimo_spot = spot

st.divider()

st.caption(
    "Monitor Divisas Tesorería v12.0"
)