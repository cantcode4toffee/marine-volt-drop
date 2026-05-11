import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Marine Volt Drop Calculator", page_icon="⚡", layout="wide")

_ALPHA_CU = 0.00393
HOT_FACTOR = 1 + _ALPHA_CU * (90 - 20)  # = 1.2751

_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600'
    '&family=Barlow:wght@400;500;600;700&display=swap" rel="stylesheet">'
)


def check_password():
    def _verify():
        st.session_state["auth"] = (st.session_state.get("pwd") == "vita")

    if st.session_state.get("auth"):
        return True

    st.markdown(_FONTS, unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown(
            '<div style="text-align:center;padding:2rem 0 1.5rem;">'
            '<div style="font-size:2.5rem;margin-bottom:0.75rem;">⚡</div>'
            '<div style="font-family:\'Barlow\',sans-serif;font-size:1.2rem;font-weight:700;'
            'color:#e6edf3;letter-spacing:0.03em;margin-bottom:0.3rem;">'
            'Marine Volt Drop Calculator</div>'
            '<div style="font-family:\'Barlow\',sans-serif;font-size:0.8rem;color:#6e7681;'
            'margin-bottom:1.75rem;">Vita electrical design toolset · Enter password to continue</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.text_input("Password", type="password", on_change=_verify, key="pwd",
                      placeholder="Enter password", label_visibility="collapsed")
        if "auth" in st.session_state and not st.session_state["auth"]:
            st.markdown(
                '<div style="border-left:4px solid #f85149;background:rgba(248,81,73,0.07);'
                'border-radius:0 6px 6px 0;padding:0.6rem 0.9rem;margin-top:0.6rem;'
                'font-family:\'Barlow\',sans-serif;font-size:0.84rem;color:#f85149;">'
                'Incorrect password.</div>',
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


# ── HTML helpers (inline styles — no <style> injection needed) ─────────────────
_STATE_COLORS = {
    "pass": ("#3fb950", "rgba(63,185,80,0.07)"),
    "warn": ("#d29922", "rgba(210,153,34,0.07)"),
    "fail": ("#f85149", "rgba(248,81,73,0.07)"),
}
_BAR_COLORS = {"pass": "#3fb950", "warn": "#d29922", "fail": "#f85149"}

_S_TILE = (
    "background:#0D1117;border:1px solid #21262d;border-radius:8px;"
    "padding:0.7rem 0.9rem 0.65rem;position:relative;"
)
_S_LABEL = (
    "display:block;font-family:'Barlow',sans-serif;font-size:0.62rem;"
    "font-weight:600;letter-spacing:0.1em;text-transform:uppercase;"
    "color:#8b949e;margin-bottom:0.28rem;"
)
_S_VALUE = (
    "display:block;font-family:'IBM Plex Mono',monospace;"
    "font-size:1.5rem;font-weight:600;color:#e6edf3;line-height:1;"
)
_S_BADGE = (
    "position:absolute;top:0.5rem;right:0.6rem;"
    "font-family:'Barlow',sans-serif;font-size:0.58rem;font-weight:700;"
    "letter-spacing:0.06em;color:#6e7681;background:#21262d;"
    "padding:0.1rem 0.35rem;border-radius:3px;text-transform:uppercase;"
)
_S_GRID = (
    "display:grid;grid-template-columns:repeat(3,1fr);gap:0.65rem;margin-bottom:0.75rem;"
)


def kpi_tile(label, value, badge=None, extra=""):
    b = f'<span style="{_S_BADGE}">{badge}</span>' if badge else ""
    return (
        f'<div style="{_S_TILE}">{b}'
        f'<span style="{_S_LABEL}">{label}</span>'
        f'<span style="{_S_VALUE}">{value}</span>'
        f'{extra}</div>'
    )


def kpi_grid(*tiles):
    return f'<div style="{_S_GRID}">{"".join(tiles)}</div>'


def status_banner(state, icon, detail):
    color, bg = _STATE_COLORS[state]
    return (
        f'<div style="display:flex;align-items:flex-start;gap:0.9rem;'
        f'border-left:5px solid {color};background:{bg};'
        f'border-radius:0 8px 8px 0;padding:0.85rem 1.1rem;margin-bottom:1rem;">'
        f'<div style="font-family:\'Barlow\',sans-serif;font-size:1.4rem;'
        f'font-weight:800;color:{color};flex-shrink:0;">{icon}</div>'
        f'<div style="font-size:0.84rem;color:#8b949e;font-family:\'Barlow\',sans-serif;'
        f'margin-top:0.25rem;">{detail}</div></div>'
    )


def zone_label(text):
    return (
        f'<div style="font-family:\'Barlow\',sans-serif;font-size:0.62rem;font-weight:700;'
        f'letter-spacing:0.14em;text-transform:uppercase;color:#6e7681;'
        f'border-bottom:1px solid #21262d;padding-bottom:0.35rem;margin-bottom:0.6rem;">'
        f'{text}</div>'
    )


def zone_div():
    return '<hr style="border:none;border-top:1px solid #21262d;margin:1rem 0 1.1rem;">'


def maxrun_cell(label, value):
    return (
        '<div style="background:#0D1117;border:1px solid #21262d;border-radius:7px;padding:0.6rem 0.85rem;">'
        f'<div style="font-family:\'Barlow\',sans-serif;font-size:0.62rem;font-weight:600;'
        f'letter-spacing:0.1em;text-transform:uppercase;color:#8b949e;">{label}</div>'
        f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:1.1rem;font-weight:600;'
        f'color:#e6edf3;margin-top:0.2rem;">{value}</div></div>'
    )


def maxrun_grid(*cells):
    return (
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.6rem;'
        'margin:0.4rem 0 0.8rem;">' + "".join(cells) + "</div>"
    )


def util_bar(pct, state):
    color = _BAR_COLORS[state]
    w = min(100, pct)
    return (
        f'<div style="background:#21262d;border-radius:3px;height:6px;overflow:hidden;'
        f'width:100%;margin:0.45rem 0 0.1rem;">'
        f'<div style="height:100%;border-radius:3px;background:{color};width:{w:.0f}%;"></div>'
        f'</div>'
    )


# ── Font injection ─────────────────────────────────────────────────────────────
st.markdown(_FONTS, unsafe_allow_html=True)

# ── Title ──────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-size:1.3rem;font-weight:700;color:#e6edf3;letter-spacing:0.03em;'
    'font-family:\'Barlow\',sans-serif;margin-bottom:0.2rem;">⚡ Marine Volt Drop Calculator</div>'
    '<div style="font-size:0.78rem;color:#6e7681;margin-bottom:1.25rem;'
    'font-family:\'Barlow\',sans-serif;">Standards-verified · ABYC E-11 / ISO 13297 · '
    'Part of the Vita electrical design toolset</div>',
    unsafe_allow_html=True,
)

# ── Zone 1: INPUTS ─────────────────────────────────────────────────────────────
st.markdown(zone_label("Inputs"), unsafe_allow_html=True)

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

st.markdown(zone_div(), unsafe_allow_html=True)

# ── Calculations ───────────────────────────────────────────────────────────────
v_drop_cold = calc_volt_drop(current_a, r_ohm_per_km, run_length_m, hot=False)
v_drop_hot  = calc_volt_drop(current_a, r_ohm_per_km, run_length_m, hot=True)
vd_pct_cold = v_drop_cold / v_nom * 100
vd_pct_hot  = v_drop_hot  / v_nom * 100
utilisation = current_a / ampacity_a * 100

# ── Zone 2: RESULTS — Volt Drop ────────────────────────────────────────────────
st.markdown(zone_label("Results — Volt Drop"), unsafe_allow_html=True)

if vd_pct_hot <= limit_pct:
    vd_state, vd_icon = "pass", "✓ PASS"
    vd_detail = (
        f"{vd_pct_hot:.2f}% drop at 90°C is within the {limit_pct}% "
        f"{selected_ct.display_name} limit"
    )
elif vd_pct_cold <= limit_pct:
    vd_state, vd_icon = "warn", "⚠ MARGINAL"
    vd_detail = (
        f"{vd_pct_cold:.2f}% at 20°C passes but {vd_pct_hot:.2f}% at 90°C exceeds "
        f"the {limit_pct}% limit — upsize CSA or shorten run"
    )
else:
    vd_state, vd_icon = "fail", "✗ FAIL"
    vd_detail = (
        f"{vd_pct_cold:.2f}% drop exceeds the {limit_pct}% "
        f"{selected_ct.display_name} limit — increase CSA or reduce run length"
    )

st.markdown(
    status_banner(vd_state, vd_icon, vd_detail)
    + kpi_grid(
        kpi_tile("Volt Drop %",     f"{vd_pct_cold:.2f}%",         badge="20°C"),
        kpi_tile("Volt Drop",       f"{v_drop_cold:.3f} V",         badge="20°C"),
        kpi_tile("Voltage at Load", f"{v_nom - v_drop_cold:.3f} V", badge="20°C"),
        kpi_tile("Volt Drop %",     f"{vd_pct_hot:.2f}%",           badge="90°C"),
        kpi_tile("Volt Drop",       f"{v_drop_hot:.3f} V",          badge="90°C"),
        kpi_tile("Voltage at Load", f"{v_nom - v_drop_hot:.3f} V",  badge="90°C"),
    ),
    unsafe_allow_html=True,
)

# ── Zone 2: RESULTS — Current Rating ──────────────────────────────────────────
st.markdown(zone_div(), unsafe_allow_html=True)
st.markdown(zone_label("Results — Current Rating"), unsafe_allow_html=True)

if current_a > ampacity_a:
    cr_state, cr_icon = "fail", "✗ OVERCURRENT"
    cr_detail = (
        f"{current_a:.1f} A exceeds the {ampacity_a:.0f} A cable rating "
        "— select a larger CSA"
    )
    bar_state = "fail"
elif utilisation > 80:
    cr_state, cr_icon = "warn", "⚠ HIGH LOAD"
    cr_detail = (
        f"{utilisation:.0f}% utilisation — consider derating for engine space, "
        "heavy bundling, or elevated ambient temperature"
    )
    bar_state = "warn"
else:
    cr_state, cr_icon = "pass", "✓ PASS"
    cr_detail = f"{current_a:.1f} A is within the {ampacity_a:.0f} A cable rating"
    bar_state = "pass"

st.markdown(
    status_banner(cr_state, cr_icon, cr_detail)
    + kpi_grid(
        kpi_tile("Cable Ampacity", f"{ampacity_a:.0f} A"),
        kpi_tile("Load Current",   f"{current_a:.1f} A"),
        kpi_tile("Utilisation",    f"{utilisation:.0f}%",
                 extra=util_bar(utilisation, bar_state)),
    ),
    unsafe_allow_html=True,
)

# ── Zone 3: ANALYSIS ──────────────────────────────────────────────────────────
st.markdown(zone_div(), unsafe_allow_html=True)

max_len     = calc_max_length(v_nom, current_a, r_ohm_per_km, limit_pct)
total_cable = max_len * 2 if max_len is not None else None
max_len_3   = calc_max_length(v_nom, current_a, r_ohm_per_km, 3)
max_len_10  = calc_max_length(v_nom, current_a, r_ohm_per_km, 10)

st.markdown(
    zone_label(f"Analysis — Maximum Run ({limit_pct}% limit at 90°C)")
    + maxrun_grid(
        maxrun_cell("Max one-way run",  fmt_length(max_len)),
        maxrun_cell("Total cable (×2)", fmt_length(total_cable)),
        maxrun_cell("At 3% limit",      fmt_length(max_len_3)),
        maxrun_cell("At 10% limit",     fmt_length(max_len_10)),
    ),
    unsafe_allow_html=True,
)

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
st.markdown(zone_div(), unsafe_allow_html=True)

with st.expander("Standards reference"):
    st.dataframe(
        std_limits[["standard", "edition", "clause", "circuit_type", "limit_pct", "notes"]],
        use_container_width=True,
        hide_index=True,
    )
with st.expander("Cable data"):
    st.dataframe(cables, use_container_width=True, hide_index=True)

st.markdown(
    '<div style="font-size:0.72rem;color:#6e7681;font-family:\'Barlow\',sans-serif;margin-top:0.5rem;">'
    "Resistance: H+S RADOX 125 DOC-0000317514 at 20°C (1.0 mm² = IEC 60228 Class 5 max) · "
    "Hot factor: α = 0.00393 /°C, T<sub>conductor</sub> = 90°C → ×1.2751 · "
    "Ampacity: IEC 60092-352:2005 Annex B (I = α·A^0.625, 90°C/45°C, ≤4 cables bunched) · "
    "Volt drop limits: ABYC E-11 §11.15.1.2.7 · ISO 13297:2020 §5.5–5.6 · ISO 16315:DIS 2023 §10.6"
    "</div>",
    unsafe_allow_html=True,
)
