import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import io
import time

# --- APP CONFIGURATION ---
st.set_page_config(
    page_title="OgiWing Laboratory",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #020617; }
    [data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace; color: #60a5fa; font-size: 1.8rem; }
    [data-testid="stMetricLabel"] { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em; color: #94a3b8; }
    .stDownloadButton button { width: 100%; border-radius: 12px; font-weight: bold; background-color: #2563eb; color: white; border: none; }
    .stDownloadButton button:hover { background-color: #1d4ed8; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- CALCULATIONS ---
def calculate_x(y_val, b, cr, ct, p):
    eta = (2 * np.abs(y_val)) / b
    eta = np.clip(eta, 0, 1)
    term1 = np.power(eta, p)
    term2 = np.power(1 - eta, p)
    denominator = term1 + term2
    fraction = np.divide(term1, denominator, out=np.zeros_like(term1), where=denominator!=0)
    return (cr - ct) * fraction

def get_stats(params):
    b, cr, ct, p = params['b'], params['Cr'], params['Ct'], params['p']
    if b <= 0 or cr <= 0: return {"area": 0, "ar": 0, "taper": 0, "span": b}
    
    resolution = 500
    y_vals = np.linspace(0, b/2, resolution)
    x_vals = calculate_x(y_vals, b, cr, ct, p)
    chords = cr - x_vals
    
    # Manual trapezoidal integration for maximum compatibility
    dy = (b/2) / (resolution - 1)
    semi_area = np.sum((chords[:-1] + chords[1:]) / 2) * dy
    total_area = 2 * semi_area
    
    return {
        "area": total_area,
        "ar": (b * b) / total_area if total_area > 0 else 0,
        "taper": ct / cr if cr != 0 else 0,
        "span": b
    }

# --- STATE MANAGEMENT ---
if 'designs' not in st.session_state:
    st.session_state.designs = [{
        "id": "default", "name": "Leading Edge 1", "color": "#3b82f6", "visible": True,
        "params": {"b": 12000.0, "Cr": 8000.0, "Ct": 1200.0, "p": 2.5}
    }]
if 'active_id' not in st.session_state:
    st.session_state.active_id = "default"

# --- SIDEBAR ---
with st.sidebar:
    st.title("OgiWing")
    st.caption("Aerospace Spline Engine")
    
    if st.button("➕ New Spline", use_container_width=True):
        new_id = f"d_{int(time.time())}"
        active = next(d for d in st.session_state.designs if d['id'] == st.session_state.active_id)
        st.session_state.designs.append({
            "id": new_id, "name": f"Spline {len(st.session_state.designs)+1}",
            "color": f"hsl({(len(st.session_state.designs)*70)%360}, 80%, 60%)",
            "visible": True, "params": active['params'].copy()
        })
        st.session_state.active_id = new_id

    st.write("### Registry")
    for i, d in enumerate(st.session_state.designs):
        c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
        # Replaced the HTML circle with a simple emoji to avoid errors
        c1.write("📍") 
        if c2.button(d['name'], key=f"btn_{d['id']}", use_container_width=True):
            st.session_state.active_id = d['id']
        st.session_state.designs[i]['visible'] = c3.checkbox("", value=d['visible'], key=f"v_{d['id']}")

    st.divider()
    active_idx = next(i for i, d in enumerate(st.session_state.designs) if d['id'] == st.session_state.active_id)
    active = st.session_state.designs[active_idx]
    
    st.write(f"### Editor: {active['name']}")
    active['params']['b'] = st.number_input("Span (b) [mm]", value=float(active['params']['b']), step=100.0)
    active['params']['Cr'] = st.number_input("Root Chord (Cr) [mm]", value=float(active['params']['Cr']), step=100.0)
    active['params']['Ct'] = st.number_input("Tip Chord (Ct) [mm]", value=float(active['params']['Ct']), step=100.0)
    active['params']['p'] = st.number_input("Exponent (p)", value=float(active['params']['p']), step=0.1)

# --- MAIN DASHBOARD ---
stats = get_stats(active['params'])
m1, m2, m3, m4 = st.columns(4)
m1.metric("TAPER RATIO", f"{stats['taper']:.3f}")
m2.metric("ASPECT RATIO", f"{stats['ar']:.3f}")
m3.metric("WING AREA", f"{stats['area']:.0f} mm²")
m4.metric("SEMI-SPAN", f"{stats['span']/2:.0f} mm")

# Plot
fig = go.Figure()
for d in st.session_state.designs:
    if not d['visible']: continue
    y = np.linspace(0, d['params']['b']/2, 250)
    x = calculate_x(y, d['params']['b'], d['params']['Cr'], d['params']['Ct'], d['params']['p'])
    fig.add_trace(go.Scatter(x=x, y=y, name=d['name'], line=dict(color=d['color'], width=3)))

fig.update_layout(
    xaxis_title="Chord (x) [mm]", yaxis_title="Span (y) [mm]",
    template="plotly_dark", height=650, margin=dict(l=20, r=20, t=20, b=20),
    xaxis=dict(gridcolor='#1e293b', scaleanchor="y", scaleratio=1),
    yaxis=dict(gridcolor='#1e293b')
)
st.plotly_chart(fig, use_container_width=True)

# --- EXPORT ---
with st.expander("📥 Export Laboratory Data"):
    c1, c2, c3 = st.columns([2, 1, 1])
    target_name = c1.selectbox("Target", ["All"] + [d['name'] for d in st.session_state.designs])
    fmt = c2.radio("Format", ["CSV", "TXT"], horizontal=True)
    
    buf = io.StringIO()
    if target_name == "All":
        buf.write("spline,x_mm,y_mm\n")
        for d in st.session_state.designs:
            y_v = np.linspace(0, d['params']['b']/2, 500)
            x_v = calculate_x(y_v, d['params']['b'], d['params']['Cr'], d['params']['Ct'], d['params']['p'])
            for x_val, y_val in zip(x_v, y_v): buf.write(f"{d['name']},{x_val:.4f},{y_val:.4f}\n")
    else:
        t = next(d for d in st.session_state.designs if d['name'] == target_name)
        y_v = np.linspace(0, t['params']['b']/2, 500)
        x_v = calculate_x(y_v, t['params']['b'], t['params']['Cr'], t['params']['Ct'], t['params']['p'])
        buf.write("x_mm,y_mm\n" if fmt == "CSV" else f"{t['name']}\nX\tY\n")
        for x_val, y_val in zip(x_v, y_v): buf.write(f"{x_val:.4f},{y_val:.4f}\n" if fmt == "CSV" else f"{x_val:.4f}\t{y_val:.4f}\n")

    c3.download_button("Download", buf.getvalue(), f"ogiwing.{fmt.lower()}", "text/plain")