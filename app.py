import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Marine Volt Drop Calculator", page_icon="⚡", layout="wide")


def check_password():
    def _verify():
        st.session_state["auth"] = (st.session_state.get("pwd") == "vita")

    if st.session_state.get("auth"):
        return True
    st.text_input("Password", type="password", on_change=_verify, key="pwd")
    if "auth" in st.session_state and not st.session_state["auth"]:
        st.error("Incorrect password.")
    return False


if not check_password():
    st.stop()

# Copper temperature coefficient — IEC 60092-352 / standard copper resistivity
_ALPHA_CU = 0.00393  # per °C
# Resistance multiplier at 90°C conductor operating temp vs 20°C datasheet datum
HOT_FACTOR = 1 + _ALPHA_CU * (90 - 20)  # = 1.2751


@st.cache_data
def load_data(schema_version=3):  # bump when CSV columns change
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
    # Use hot resistance so the result is the true design limit at operating temperature
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
        return "12 V nominal system"
    if v <= 28:
        return "24 V nominal system"
    return "32 V nominal system"


st.title("⚡ Marine Volt Drop Calculator")
st.caption(
    "Standards-verified volt drop calculator for marine electrical systems · "
    "Part of the Vita electrical design toolset"
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Circuit parameters")

    v_nom = st.slider("System voltage (V)", min_value=9, max_value=36, value=13, step=1)
    st.caption(f"**{v_nom} V** — {nominal_label(v_nom)}")

    current_a = st.number_input(
        "Load current (A)", min_value=0.1, max_value=5000.0, value=1.0, step=0.5
    )

    run_length_m = st.number_input(
        "Cable run — one way (m)", min_value=0.1, max_value=5000.0, value=5.0, step=0.5
    )

    csa_options = {f"{row.csa_mm2} mm²": row for _, row in cables.iterrows()}
    csa_label = st.selectbox(
        "Cable CSA", list(csa_options.keys()), index=2  # default 0.5 mm²
    )
    selected_cable = csa_options[csa_label]
    r_ohm_per_km = float(selected_cable["resistance_ohm_per_km"])
    ampacity_a = float(selected_cable["ampacity_a"])

    circuit_type_options = {
        row.display_name: row for _, row in circuit_types.iterrows()
    }
    ct_label = st.selectbox("Circuit type", list(circuit_type_options.keys()), index=0)
    selected_ct = circuit_type_options[ct_label]
    limit_pct = int(selected_ct.limit_pct_abyc)
    st.caption(f"Voltage drop limit: **{limit_pct}%** (ABYC E-11 / ISO 13297)")

# ── Voltage drop — forward calculation ───────────────────────────────────────
st.subheader(f"Voltage drop — {run_length_m:.1f} m one-way run")

v_drop_cold = calc_volt_drop(current_a, r_ohm_per_km, run_length_m, hot=False)
v_drop_hot  = calc_volt_drop(current_a, r_ohm_per_km, run_length_m, hot=True)
vd_pct_cold = v_drop_cold / v_nom * 100
vd_pct_hot  = v_drop_hot  / v_nom * 100

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Drop % · 20°C", f"{vd_pct_cold:.2f}%",
          help="Conductor at datasheet reference temperature (20°C)")
c2.metric("Drop V · 20°C", f"{v_drop_cold:.3f} V")
c3.metric("V at load · 20°C", f"{v_nom - v_drop_cold:.3f} V")
c4.metric("Drop % · 90°C", f"{vd_pct_hot:.2f}%",
          help="Conductor at operating temperature (90°C) — design case")
c5.metric("Drop V · 90°C", f"{v_drop_hot:.3f} V")
c6.metric("V at load · 90°C", f"{v_nom - v_drop_hot:.3f} V")

# Pass/fail on the hot (design) value
if vd_pct_hot <= limit_pct:
    st.success(
        f"PASS — {vd_pct_hot:.2f}% drop at 90°C is within the {limit_pct}% "
        f"{selected_ct.display_name} limit."
    )
elif vd_pct_cold <= limit_pct:
    st.warning(
        f"MARGINAL — {vd_pct_cold:.2f}% at 20°C passes, but {vd_pct_hot:.2f}% at "
        f"90°C exceeds the {limit_pct}% limit. Upsize CSA or shorten run."
    )
else:
    st.error(
        f"FAIL — {vd_pct_cold:.2f}% drop exceeds the {limit_pct}% "
        f"{selected_ct.display_name} limit. Increase CSA or reduce run length."
    )

# ── Current rating ────────────────────────────────────────────────────────────
st.divider()
st.subheader("Current rating")

utilisation = current_a / ampacity_a * 100
ca, cb, cc = st.columns(3)
ca.metric(
    "Cable ampacity",
    f"{ampacity_a:.0f} A",
    help=(
        "IEC 60092-352:2005 Annex B — formula I = α × A^0.625, "
        "90°C conductor / 45°C ambient / up to 4 cables bunched. "
        "Apply 0.85 derating for >6 cables bunched."
    ),
)
cb.metric("Load current", f"{current_a:.1f} A")
cc.metric("Utilisation", f"{utilisation:.0f}%")

if current_a > ampacity_a:
    st.error(
        f"OVERCURRENT — {current_a:.1f} A exceeds the {ampacity_a:.0f} A cable rating. "
        "Select a larger CSA."
    )
elif utilisation > 80:
    st.warning(
        f"HIGH LOAD — {utilisation:.0f}% utilisation. Consider derating for engine space, "
        "heavy bundling, or elevated ambient temperature."
    )
else:
    st.success(f"PASS — {current_a:.1f} A is within the {ampacity_a:.0f} A cable rating.")

# ── Maximum run ───────────────────────────────────────────────────────────────
st.divider()
st.subheader(f"Maximum run — {limit_pct}% limit")

max_len = calc_max_length(v_nom, current_a, r_ohm_per_km, limit_pct)
total_cable = max_len * 2 if max_len is not None else None

d1, d2, d3, d4 = st.columns(4)
d1.metric("Max one-way run", fmt_length(max_len),
          help="At 90°C conductor temp — guaranteed to pass limit at operating temperature")
d2.metric("Total cable needed", fmt_length(total_cable), help="Both conductors — 2 × one-way run")
d3.metric("Cable CSA", f"{selected_cable['csa_mm2']} mm²")
d4.metric("Resistance", f"{r_ohm_per_km} Ω/km")


def _ref(pct):
    ml = calc_max_length(v_nom, current_a, r_ohm_per_km, pct)
    tc = ml * 2 if ml else None
    return f"max one-way = {fmt_length(ml)} · total cable = {fmt_length(tc)}"


st.markdown(f"**3%:** {_ref(3)}  \n**10%:** {_ref(10)}")

# ── Sweep chart ───────────────────────────────────────────────────────────────
st.divider()
st.subheader(f"Max one-way run vs cable CSA  ({v_nom} V, {current_a} A, {limit_pct}% limit)")

cable_labels = list(csa_options.keys())
sel_idx = cable_labels.index(csa_label)
lo = max(0, sel_idx - 5)
hi = min(len(cable_labels) - 1, sel_idx + 5)
slice_labels = cable_labels[lo : hi + 1]

sweep_rows = []
for lbl in slice_labels:
    row = csa_options[lbl]
    length = calc_max_length(v_nom, current_a, float(row["resistance_ohm_per_km"]), limit_pct)
    if length is not None:
        sweep_rows.append({
            "csa": str(row["csa_mm2"]),
            "length_m": round(length, 1),
            "selected": lbl == csa_label,
        })

df_sweep = pd.DataFrame(sweep_rows)
bar_colors = ["#FF6B35" if sel else "#4A90D9" for sel in df_sweep["selected"]]

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
    height=420,
    margin=dict(t=20),
)
st.plotly_chart(fig, use_container_width=True)
st.caption(
    f"Showing 5 sizes either side of the selected {selected_cable['csa_mm2']} mm² cable "
    "(highlighted in orange)."
)

# ── Reference tables ──────────────────────────────────────────────────────────
with st.expander("📋 Standards reference"):
    st.dataframe(
        std_limits[["standard", "edition", "clause", "circuit_type", "limit_pct", "notes"]],
        use_container_width=True,
        hide_index=True,
    )
with st.expander("📋 Cable data"):
    st.dataframe(cables, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "Resistance: H+S RADOX 125 DOC-0000317514 at 20°C (1.0 mm² = IEC 60228 Class 5 max) · "
    "Hot factor: α = 0.00393 /°C, T_conductor = 90°C → ×1.2751 · "
    "Ampacity: IEC 60092-352:2005 Annex B (I = α·A^0.625, 90°C/45°C, ≤4 cables bunched) · "
    "Volt drop limits: ABYC E-11 §11.15.1.2.7 · ISO 13297:2020 §5.5–5.6 · ISO 16315:DIS 2023 §10.6"
)
