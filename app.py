import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import io
import time

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="OgiWing Laboratory",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CUSTOM CSS (The "Crafted" Look) ---
st.markdown("""
    <style>
    /* Main Background */
    .stApp { background-color: #020617; color: #e2e8f0; }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }
    
    /* Metric Cards */
    [data-testid="stMetric"] {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    [data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace; color: #ffffff; font-size: 1.5rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.7rem !important; font-weight: 700; letter-spacing: 0.1em; color: #64748b; text-transform: uppercase; }
    
    /* Buttons */
    .stButton button { width: 100%; border-radius: 10px; border: 1px solid #1e293b; transition: all 0.2s; }
    .stButton button:hover { border-color: #3b82f6; color: #3b82f6; }
    
    /* Inputs */
    input { background-color: #020617 !important; border-color: #1e293b !important; color: #f8fafc !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CORE MATH ENGINE ---
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
    
    y_vals = np.linspace(0, b/2, 500)
    chords = cr - calculate_x(y_vals, b, cr, ct, p)
    total_area = 2 * np.trapz(chords, y_vals)
    
    return {
        "area": total_area,
        "ar": (b * b) / total_area if total_area > 0 else 0,
        "taper": ct / cr if cr != 0 else 0,
        "span": b
    }

# --- 4. STATE MANAGEMENT ---
if 'designs' not in st.session_state:
    st.session_state.designs = [{
        "id": "default", "name": "Leading Edge 1", "color": "#3b82f6", "visible": True,
        "params": {"b": 12000.0, "Cr": 8000.0, "Ct": 1200.0, "p": 2.5}
    }]
if 'active_id' not in st.session_state:
    st.session_state.active_id = "default"

# --- 5. SIDEBAR (Registry & Editor) ---
with st.sidebar:
    st.markdown("<h1 style='color:white; margin-bottom:0;'>OgiWing</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#3b82f6; font-size:0.7rem; font-weight:bold; text-transform:uppercase; margin-bottom:20px;'>Metric Spline Engine</p>", unsafe_allow_html=True)
    
    # Registry Section
    st.markdown("### Spline Registry")
    if st.button("➕ Add New Spline"):
        new_id = f"d_{int(time.time())}"
        active = next(d for d in st.session_state.designs if d['id'] == st.session_state.active_id)
        st.session_state.designs.append({
            "id": new_id, "name": f"Spline {len(st.session_state.designs)+1}",
            "color": f"hsl({(len(st.session_state.designs)*75)%360}, 70%, 50%)",
            "visible": True, "params": active['params'].copy()
        })
        st.session_state.active_id = new_id

    # List of Splines
    for i, d in enumerate(st.session_state.designs):
        cols = st.columns([0.1, 0.7, 0.2])
        cols[0].markdown(f"<div style='background:{d['color']}; width:10px; height:10px; border-radius:50%; margin-top:12px;'></div>", unsafe_allow_html=True)
        if cols[1].button(d['name'], key=f"sel_{d['id']}", use_container_width=True):
            st.session_state.active_id = d['id']
        st.session_state.designs[i]['visible'] = cols[2].checkbox("", value=d['visible'], key=f"v_{d['id']}")

    st.divider()
    
    # Editor Section
    active_idx = next(i for i, d in enumerate(st.session_state.designs) if d['id'] == st.session_state.active_id)
    active = st.session_state.designs[active_idx]
    st.markdown(f"### Editor: {active['name']}")
    
    active['params']['b'] = st.number_input("Total Span (b) [mm]", value=float(active['params']['b']), step=100.0)
    active['params']['Cr'] = st.number_input("Root Chord (Cr) [mm]", value=float(active['params']['Cr']), step=100.0)
    active['params']['Ct'] = st.number_input("Tip Chord (Ct) [mm]", value=float(active['params']['Ct']), step=100.0)
    active['params']['p'] = st.number_input("Shape Exponent (p)", value=float(active['params']['p']), step=0.1)

# --- 6. MAIN CONTENT ---
# Metrics Row
stats = get_stats(active['params'])
m1, m2, m3, m4 = st.columns(4)
m1.metric("Taper Ratio", f"{stats['taper']:.3f}")
m2.metric("Aspect Ratio", f"{stats['ar']:.3f}")
m3.metric("Wing Area (S)", f"{stats['area']:.0f} mm²")
m4.metric("Semi-Span (b/2)", f"{stats['span']/2:.0f} mm")

# Plot Area
fig = go.Figure()
for d in st.session_state.designs:
    if not d['visible']: continue
    y = np.linspace(0, d['params']['b']/2, 250)
    x = calculate_x(y, d['params']['b'], d['params']['Cr'], d['params']['Ct'], d['params']['p'])
    
    fig.add_trace(go.Scatter(
        x=x, y=y, 
        name=d['name'], 
        line=dict(color=d['color'], width=3),
        hovertemplate="X: %{x:.1f} mm<br>Y: %{y:.1f} mm<extra></extra>"
    ))

fig.update_layout(
    xaxis_title="Chord Depth (x) [mm]",
    yaxis_title="Semi-Span (y) [mm]",
    template="plotly_dark",
    height=700,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(gridcolor='#1e293b', zerolinecolor='#475569', scaleanchor="y", scaleratio=1),
    yaxis=dict(gridcolor='#1e293b', zerolinecolor='#475569'),
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
)
st.plotly_chart(fig, use_container_width=True)

# Export Section
with st.expander("📥 Export Laboratory Data"):
    c1, c2, c3 = st.columns([2, 1, 1])
    target = c1.selectbox("Target Spline", ["All Splines"] + [d['name'] for d in st.session_state.designs])
    fmt = c2.radio("Format", ["CSV", "TXT"], horizontal=True)
    
    buf = io.StringIO()
    if target == "All Splines":
        buf.write("spline,x_mm,y_mm\n")
        for d in st.session_state.designs:
            y_v = np.linspace(0, d['params']['b']/2, 500)
            x_v = calculate_x(y_v, d['params']['b'], d['params']['Cr'], d['params']['Ct'], d['params']['p'])
            for xv, yv in zip(x_v, y_v): buf.write(f"{d['name']},{xv:.4f},{yv:.4f}\n")
    else:
        t = next(d for d in st.session_state.designs if d['name'] == target)
        y_v = np.linspace(0, t['params']['b']/2, 500)
        x_v = calculate_x(y_v, t['params']['b'], t['params']['Cr'], t['params']['Ct'], t['params']['p'])
        buf.write("x_mm,y_mm\n" if fmt == "CSV" else f"{t['name']}\nX\tY\n")
        for xv, yv in zip(x_v, y_v): buf.write(f"{xv:.4f},{yv:.4f}\n" if fmt == "CSV" else f"{xv:.4f}\t{yv:.4f}\n")
    
    c3.markdown("<br>", unsafe_allow_html=True)
    c3.download_button(f"Download {fmt}", buf.getvalue(), f"ogiwing_export.{fmt.lower()}", use_container_width=True)

st.markdown("<p style='text-align:center; color:#475569; font-size:0.7rem; margin-top:50px;'>Aerospace Design Studio &copy; 2024</p>", unsafe_allow_html=True)