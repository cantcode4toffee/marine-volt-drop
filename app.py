import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Marine Volt Drop Calculator", page_icon="⚡", layout="wide")

_ALPHA_CU = 0.00393
HOT_FACTOR = 1 + _ALPHA_CU * (90 - 20)  # = 1.2751


def check_password():
    def _verify():
        st.session_state["auth"] = (st.session_state.get("pwd") == "vita")

    if st.session_state.get("auth"):
        return True

    st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Barlow:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
      html, body, .stApp { font-family: 'Barlow', sans-serif !important; }
      .block-container { max-width: 420px !important; padding-top: 20vh !important; }
      .auth-logo  { font-size: 2rem; margin-bottom: 0.5rem; }
      .auth-title { font-family: 'Barlow', sans-serif; font-size: 1.15rem; font-weight: 700;
                    color: #e6edf3; letter-spacing: 0.03em; margin-bottom: 0.2rem; }
      .auth-sub   { font-family: 'Barlow', sans-serif; font-size: 0.8rem; color: #6e7681;
                    margin-bottom: 1.75rem; }
      .auth-error { border-left: 4px solid #f85149; background: rgba(248,81,73,0.07);
                    border-radius: 0 6px 6px 0; padding: 0.6rem 0.9rem; margin-top: 0.6rem;
                    font-family: 'Barlow', sans-serif; font-size: 0.84rem; color: #f85149; }
    </style>
    <div class="auth-logo">⚡</div>
    <div class="auth-title">Marine Volt Drop Calculator</div>
    <div class="auth-sub">Vita electrical design toolset · Enter password to continue</div>
    """, unsafe_allow_html=True)

    st.text_input("Password", type="password", on_change=_verify, key="pwd",
                  placeholder="Enter password", label_visibility="collapsed")

    if "auth" in st.session_state and not st.session_state["auth"]:
        st.markdown(
            '<div class="auth-error">Incorrect password.</div>',
            unsafe_allow_html=True,
        )
    return False


if not check_password():
    st.stop()


@st.cache_data
def load_data(schema_version=3):
    cables = pd.read_csv("data/cables.csv")
    std_limits = pd.read_csv("data/standards_limits.csv")
    circuit_types = pd.read_csv("data/circuit_types.csv")
    return cables, std_limits, circuit_types


cables, std_limits, circuit_types = load_data(schema_version=3)


def calc_volt_drop(current_a, r_ohm_per_km, run_length_m, hot=False):
    """Voltage drop (V) for a one-way run. Factor of 2 covers both conductors."""
    factor = HOT_FACTOR if hot else 1.0
    r_total = 2 * run_length_m * r_ohm_per_km / 1000 * factor
    return current_a * r_total


def calc_max_length(v_nom, current_a, r_ohm_per_km, limit_pct):
    """Max one-way run (m) at 90°C operating temp before voltage drop exceeds limit."""
    if current_a == 0 or r_ohm_per_km == 0:
        return None
    v_drop_max = v_nom * limit_pct / 100
    length_m = (v_drop_max * 1000) / (2 * current_a * r_ohm_per_km * HOT_FACTOR)
    return length_m if length_m > 0 else None


def fmt_length(length_m):
    if length_m is None:
        return "—"
    if length_m >= 1000:
        return f"{length_m / 1000:.2f} km"
    return f"{length_m:.1f} m"


def nominal_label(v):
    if v <= 14:
        return "12 V nominal"
    if v <= 28:
        return "24 V nominal"
    return "32 V nominal"


# ── Fonts + global CSS ─────────────────────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Barlow:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  html, body, .stApp { font-family: 'Barlow', sans-serif !important; }

  [data-testid="stSidebar"],
  [data-testid="collapsedControl"] { display: none !important; }

  .block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 1400px !important;
  }

  /* Title */
  .app-title {
    font-size: 1.3rem; font-weight: 700; color: #e6edf3; letter-spacing: 0.03em; margin: 0;
    font-family: 'Barlow', sans-serif;
  }
  .app-sub {
    font-size: 0.78rem; color: #6e7681; margin-top: 0.2rem; margin-bottom: 1.25rem;
    font-family: 'Barlow', sans-serif;
  }

  /* Zone label */
  .zone-label {
    font-family: 'Barlow', sans-serif;
    font-size: 0.62rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #6e7681;
    border-bottom: 1px solid #21262d;
    padding-bottom: 0.35rem; margin-bottom: 0.6rem;
  }

  /* Status banners */
  .status-banner {
    display: flex; align-items: flex-start; gap: 0.9rem;
    border-radius: 0 8px 8px 0;
    padding: 0.85rem 1.1rem;
    margin-bottom: 1rem;
  }
  .s-pass { border-left: 5px solid #3fb950; background: rgba(63,185,80,0.07); }
  .s-warn { border-left: 5px solid #d29922; background: rgba(210,153,34,0.07); }
  .s-fail { border-left: 5px solid #f85149; background: rgba(248,81,73,0.07); }

  .status-icon {
    font-family: 'Barlow', sans-serif;
    font-size: 1.4rem; font-weight: 800; line-height: 1; flex-shrink: 0; margin-top: 0.05rem;
  }
  .s-pass .status-icon { color: #3fb950; }
  .s-warn .status-icon { color: #d29922; }
  .s-fail .status-icon { color: #f85149; }

  .status-detail {
    font-size: 0.84rem; color: #8b949e; font-family: 'Barlow', sans-serif;
    margin-top: 0.25rem;
  }

  /* KPI tile grid */
  .kpi-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.65rem;
    margin-bottom: 0.75rem;
  }
  .kpi-tile {
    background: #0D1117; border: 1px solid #21262d; border-radius: 8px;
    padding: 0.7rem 0.9rem 0.65rem; position: relative;
  }
  .kpi-label {
    display: block; font-family: 'Barlow', sans-serif;
    font-size: 0.62rem; font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; color: #8b949e; margin-bottom: 0.28rem;
  }
  .kpi-value {
    display: block; font-family: 'IBM Plex Mono', monospace;
    font-size: 1.5rem; font-weight: 600; color: #e6edf3; line-height: 1;
  }
  .kpi-badge {
    position: absolute; top: 0.5rem; right: 0.6rem;
    font-family: 'Barlow', sans-serif;
    font-size: 0.58rem; font-weight: 700; letter-spacing: 0.06em;
    color: #6e7681; background: #21262d;
    padding: 0.1rem 0.35rem; border-radius: 3px; text-transform: uppercase;
  }

  /* Utilisation bar */
  .util-track {
    background: #21262d; border-radius: 3px; height: 6px;
    overflow: hidden; width: 100%; margin: 0.3rem 0 0.15rem;
  }
  .util-fill { height: 100%; border-radius: 3px; }
  .u-ok   { background: #3fb950; }
  .u-warn { background: #d29922; }
  .u-over { background: #f85149; }

  /* Max run grid */
  .maxrun-grid {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.6rem;
    margin: 0.4rem 0 0.8rem;
  }
  .maxrun-cell {
    background: #0D1117; border: 1px solid #21262d; border-radius: 7px;
    padding: 0.6rem 0.85rem;
  }
  .maxrun-label {
    font-family: 'Barlow', sans-serif;
    font-size: 0.62rem; font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; color: #8b949e;
  }
  .maxrun-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.1rem; font-weight: 600; color: #e6edf3; margin-top: 0.2rem;
  }

  /* Divider */
  .zone-div { border: none; border-top: 1px solid #21262d; margin: 1rem 0 1.1rem; }

  /* Footer */
  .footer-note {
    font-size: 0.72rem; color: #6e7681; font-family: 'Barlow', sans-serif;
    margin-top: 0.5rem;
  }
</style>
""", unsafe_allow_html=True)

# ── Title ──────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-title">⚡ Marine Volt Drop Calculator</div>'
    '<div class="app-sub">Standards-verified · ABYC E-11 / ISO 13297 · '
    'Part of the Vita electrical design toolset</div>',
    unsafe_allow_html=True,
)

# ── Zone 1: INPUTS ─────────────────────────────────────────────────────────────
st.markdown('<div class="zone-label">Inputs</div>', unsafe_allow_html=True)

csa_options = {f"{row.csa_mm2} mm²": row for _, row in cables.iterrows()}
circuit_type_options = {row.display_name: row for _, row in circuit_types.iterrows()}

c1, c2, c3, c4, c5 = st.columns([1.2, 1, 1, 1.2, 1.6])

with c1:
    v_nom = st.slider("System voltage (V)", min_value=9, max_value=36, value=13, step=1)
    st.caption(f"{v_nom} V · {nominal_label(v_nom)}")

with c2:
    current_a = st.number_input(
        "Load current (A)", min_value=0.1, max_value=5000.0, value=1.0, step=0.5
    )

with c3:
    run_length_m = st.number_input(
        "Cable run — one way (m)", min_value=0.1, max_value=5000.0, value=5.0, step=0.5
    )

with c4:
    csa_label = st.selectbox("Cable CSA", list(csa_options.keys()), index=2)
    selected_cable = csa_options[csa_label]
    r_ohm_per_km = float(selected_cable["resistance_ohm_per_km"])
    ampacity_a = float(selected_cable["ampacity_a"])

with c5:
    ct_label = st.selectbox("Circuit type", list(circuit_type_options.keys()), index=0)
    selected_ct = circuit_type_options[ct_label]
    limit_pct = int(selected_ct.limit_pct_abyc)
    st.caption(f"Limit: {limit_pct}% · ABYC E-11 / ISO 13297")

st.markdown('<hr class="zone-div">', unsafe_allow_html=True)

# ── Calculations ───────────────────────────────────────────────────────────────
v_drop_cold = calc_volt_drop(current_a, r_ohm_per_km, run_length_m, hot=False)
v_drop_hot  = calc_volt_drop(current_a, r_ohm_per_km, run_length_m, hot=True)
vd_pct_cold = v_drop_cold / v_nom * 100
vd_pct_hot  = v_drop_hot  / v_nom * 100
utilisation = current_a / ampacity_a * 100

# ── Zone 2: RESULTS — Volt Drop ────────────────────────────────────────────────
st.markdown('<div class="zone-label">Results — Volt Drop</div>', unsafe_allow_html=True)

if vd_pct_hot <= limit_pct:
    vd_cls, vd_icon = "s-pass", "✓ PASS"
    vd_detail = (
        f"{vd_pct_hot:.2f}% drop at 90°C is within the {limit_pct}% "
        f"{selected_ct.display_name} limit"
    )
elif vd_pct_cold <= limit_pct:
    vd_cls, vd_icon = "s-warn", "⚠ MARGINAL"
    vd_detail = (
        f"{vd_pct_cold:.2f}% at 20°C passes but {vd_pct_hot:.2f}% at 90°C exceeds "
        f"the {limit_pct}% limit — upsize CSA or shorten run"
    )
else:
    vd_cls, vd_icon = "s-fail", "✗ FAIL"
    vd_detail = (
        f"{vd_pct_cold:.2f}% drop exceeds the {limit_pct}% "
        f"{selected_ct.display_name} limit — increase CSA or reduce run length"
    )

st.markdown(f"""
<div class="status-banner {vd_cls}">
  <div class="status-icon">{vd_icon}</div>
  <div class="status-detail">{vd_detail}</div>
</div>
<div class="kpi-grid">
  <div class="kpi-tile">
    <span class="kpi-badge">20°C</span>
    <span class="kpi-label">Volt Drop %</span>
    <span class="kpi-value">{vd_pct_cold:.2f}%</span>
  </div>
  <div class="kpi-tile">
    <span class="kpi-badge">20°C</span>
    <span class="kpi-label">Volt Drop</span>
    <span class="kpi-value">{v_drop_cold:.3f} V</span>
  </div>
  <div class="kpi-tile">
    <span class="kpi-badge">20°C</span>
    <span class="kpi-label">Voltage at Load</span>
    <span class="kpi-value">{v_nom - v_drop_cold:.3f} V</span>
  </div>
  <div class="kpi-tile">
    <span class="kpi-badge">90°C</span>
    <span class="kpi-label">Volt Drop %</span>
    <span class="kpi-value">{vd_pct_hot:.2f}%</span>
  </div>
  <div class="kpi-tile">
    <span class="kpi-badge">90°C</span>
    <span class="kpi-label">Volt Drop</span>
    <span class="kpi-value">{v_drop_hot:.3f} V</span>
  </div>
  <div class="kpi-tile">
    <span class="kpi-badge">90°C</span>
    <span class="kpi-label">Voltage at Load</span>
    <span class="kpi-value">{v_nom - v_drop_hot:.3f} V</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Zone 2: RESULTS — Current Rating ──────────────────────────────────────────
st.markdown('<hr class="zone-div">', unsafe_allow_html=True)
st.markdown('<div class="zone-label">Results — Current Rating</div>', unsafe_allow_html=True)

if current_a > ampacity_a:
    cr_cls, cr_icon = "s-fail", "✗ OVERCURRENT"
    cr_detail = (
        f"{current_a:.1f} A exceeds the {ampacity_a:.0f} A cable rating "
        "— select a larger CSA"
    )
    util_bar_cls = "u-over"
elif utilisation > 80:
    cr_cls, cr_icon = "s-warn", "⚠ HIGH LOAD"
    cr_detail = (
        f"{utilisation:.0f}% utilisation — consider derating for engine space, "
        "heavy bundling, or elevated ambient temperature"
    )
    util_bar_cls = "u-warn"
else:
    cr_cls, cr_icon = "s-pass", "✓ PASS"
    cr_detail = (
        f"{current_a:.1f} A is within the {ampacity_a:.0f} A cable rating"
    )
    util_bar_cls = "u-ok"

util_w = min(100, utilisation)

st.markdown(f"""
<div class="status-banner {cr_cls}">
  <div class="status-icon">{cr_icon}</div>
  <div class="status-detail">{cr_detail}</div>
</div>
<div class="kpi-grid">
  <div class="kpi-tile">
    <span class="kpi-label">Cable Ampacity</span>
    <span class="kpi-value">{ampacity_a:.0f} A</span>
  </div>
  <div class="kpi-tile">
    <span class="kpi-label">Load Current</span>
    <span class="kpi-value">{current_a:.1f} A</span>
  </div>
  <div class="kpi-tile">
    <span class="kpi-label">Utilisation</span>
    <span class="kpi-value">{utilisation:.0f}%</span>
    <div class="util-track" style="margin-top:0.5rem">
      <div class="util-fill {util_bar_cls}" style="width:{util_w:.0f}%"></div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Zone 3: ANALYSIS — Maximum Run ────────────────────────────────────────────
st.markdown('<hr class="zone-div">', unsafe_allow_html=True)

max_len    = calc_max_length(v_nom, current_a, r_ohm_per_km, limit_pct)
total_cable = max_len * 2 if max_len is not None else None
max_len_3  = calc_max_length(v_nom, current_a, r_ohm_per_km, 3)
max_len_10 = calc_max_length(v_nom, current_a, r_ohm_per_km, 10)

st.markdown(
    f'<div class="zone-label">Analysis — Maximum Run ({limit_pct}% limit at 90°C)</div>',
    unsafe_allow_html=True,
)
st.markdown(f"""
<div class="maxrun-grid">
  <div class="maxrun-cell">
    <div class="maxrun-label">Max one-way run</div>
    <div class="maxrun-value">{fmt_length(max_len)}</div>
  </div>
  <div class="maxrun-cell">
    <div class="maxrun-label">Total cable (×2)</div>
    <div class="maxrun-value">{fmt_length(total_cable)}</div>
  </div>
  <div class="maxrun-cell">
    <div class="maxrun-label">At 3% limit</div>
    <div class="maxrun-value">{fmt_length(max_len_3)}</div>
  </div>
  <div class="maxrun-cell">
    <div class="maxrun-label">At 10% limit</div>
    <div class="maxrun-value">{fmt_length(max_len_10)}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Chart ──────────────────────────────────────────────────────────────────────
cable_labels = list(csa_options.keys())
sel_idx = cable_labels.index(csa_label)
lo = max(0, sel_idx - 5)
hi = min(len(cable_labels) - 1, sel_idx + 5)

sweep_rows = []
for lbl in cable_labels[lo : hi + 1]:
    row = csa_options[lbl]
    length = calc_max_length(v_nom, current_a, float(row["resistance_ohm_per_km"]), limit_pct)
    if length is not None:
        sweep_rows.append({
            "csa": str(row["csa_mm2"]),
            "length_m": round(length, 1),
            "selected": lbl == csa_label,
        })

df_sweep = pd.DataFrame(sweep_rows)
bar_colors = ["#D4A017" if sel else "#3A6EA5" for sel in df_sweep["selected"]]

fig = go.Figure(
    go.Bar(
        x=df_sweep["csa"],
        y=df_sweep["length_m"],
        marker_color=bar_colors,
        hovertemplate="%{x} mm²<br>%{y:.1f} m<extra></extra>",
    )
)
fig.update_layout(
    xaxis_title="Cable CSA (mm²)",
    yaxis_title="Max one-way run (m)",
    showlegend=False,
    height=360,
    margin=dict(t=8, b=50, l=60, r=20),
    paper_bgcolor="#0D1117",
    plot_bgcolor="#161B22",
    font=dict(family="Barlow, sans-serif", color="#8b949e", size=12),
    xaxis=dict(gridcolor="#21262d", linecolor="#30363d", tickfont=dict(color="#8b949e")),
    yaxis=dict(gridcolor="#21262d", linecolor="#30363d", tickfont=dict(color="#8b949e")),
)
st.plotly_chart(fig, use_container_width=True)
st.caption(
    f"5 sizes either side of selected {selected_cable['csa_mm2']} mm² (amber bar). "
    "Max run at 90°C conductor temperature."
)

# ── Reference tables ───────────────────────────────────────────────────────────
st.markdown('<hr class="zone-div">', unsafe_allow_html=True)

with st.expander("Standards reference"):
    st.dataframe(
        std_limits[["standard", "edition", "clause", "circuit_type", "limit_pct", "notes"]],
        use_container_width=True,
        hide_index=True,
    )
with st.expander("Cable data"):
    st.dataframe(cables, use_container_width=True, hide_index=True)

st.markdown(
    '<div class="footer-note">'
    "Resistance: H+S RADOX 125 DOC-0000317514 at 20°C (1.0 mm² = IEC 60228 Class 5 max) · "
    "Hot factor: α = 0.00393 /°C, T<sub>conductor</sub> = 90°C → ×1.2751 · "
    "Ampacity: IEC 60092-352:2005 Annex B (I = α·A^0.625, 90°C/45°C, ≤4 cables bunched) · "
    "Volt drop limits: ABYC E-11 §11.15.1.2.7 · ISO 13297:2020 §5.5–5.6 · ISO 16315:DIS 2023 §10.6"
    "</div>",
    unsafe_allow_html=True,
)
