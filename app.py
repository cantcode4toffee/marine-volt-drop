import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Marine Volt Drop Calculator", page_icon="⚡", layout="wide")


@st.cache_data
def load_data():
    cables = pd.read_csv("data/cables.csv")
    std_limits = pd.read_csv("data/standards_limits.csv")
    circuit_types = pd.read_csv("data/circuit_types.csv")
    return cables, std_limits, circuit_types


cables, std_limits, circuit_types = load_data()


def calc_max_length(v_nom, current_a, r_ohm_per_km, limit_pct):
    """Max one-way circuit length (m) for given voltage drop limit. Returns None if undefined."""
    if current_a == 0 or r_ohm_per_km == 0:
        return None
    v_drop_max = v_nom * limit_pct / 100
    # V_drop = 2 * L(km) * r_ohm_per_km * I  →  L(m) = V_drop_max * 1000 / (2 * I * r_ohm_per_km)
    length_m = (v_drop_max * 1000) / (2 * current_a * r_ohm_per_km)
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

# ── Sidebar inputs ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Circuit parameters")

    v_nom = st.slider("System voltage (V)", min_value=9, max_value=36, value=12, step=1)
    st.caption(f"**{v_nom} V** — {nominal_label(v_nom)}")

    current_a = st.number_input(
        "Load current (A)", min_value=0.1, max_value=5000.0, value=10.0, step=0.5
    )

    csa_options = {f"{row.csa_mm2} mm²": row for _, row in cables.iterrows()}
    csa_label = st.selectbox(
        "Cable CSA", list(csa_options.keys()), index=7  # default 4 mm²
    )
    selected_cable = csa_options[csa_label]
    r_ohm_per_km = float(selected_cable["resistance_ohm_per_km"])

    circuit_type_options = {
        row.display_name: row for _, row in circuit_types.iterrows()
    }
    ct_label = st.selectbox("Circuit type", list(circuit_type_options.keys()))
    selected_ct = circuit_type_options[ct_label]
    limit_pct = int(selected_ct.limit_pct_abyc)
    st.caption(f"Voltage drop limit: **{limit_pct}%** (ABYC E-11 / ISO 13297)")

# ── Results ───────────────────────────────────────────────────────────────────
st.subheader("Results")

max_len = calc_max_length(v_nom, current_a, r_ohm_per_km, limit_pct)
one_way = max_len / 2 if max_len is not None else None
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Max circuit length", fmt_length(max_len))
with col2:
    st.metric("One-way distance", fmt_length(one_way))
with col3:
    st.metric("Cable CSA", f"{selected_cable['csa_mm2']} mm²")
with col4:
    st.metric("Resistance", f"{r_ohm_per_km} Ω/km")

st.divider()
st.markdown(f"""
**Voltage drop limits — {v_nom} V, {current_a} A, {selected_cable['csa_mm2']} mm² ({r_ohm_per_km} Ω/km)**

**3%:**  circuit = {fmt_length(calc_max_length(v_nom, current_a, r_ohm_per_km, 3))}
**10%:** circuit = {fmt_length(calc_max_length(v_nom, current_a, r_ohm_per_km, 10))}
""")

# ── Sweep chart ───────────────────────────────────────────────────────────────
st.divider()
st.subheader(f"Max circuit length vs cable CSA  ({v_nom} V, {current_a} A, {limit_pct}% limit)")

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
    yaxis_title="Max circuit length (m)",
    showlegend=False,
    height=420,
    margin=dict(t=20),
)
st.plotly_chart(fig, use_container_width=True)
st.caption(
    f"Showing 5 sizes either side of the selected {selected_cable['csa_mm2']} mm² cable "
    f"(highlighted in orange)."
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
    "Cable resistivity: H+S RADOX 125 DOC-0000317514 (27-Oct-2023) at 20°C · "
    "ABYC E-11 §11.15.1.2.7 · ISO 13297:2020 §5.5–5.6 + Annex A · ISO 16315:DIS 2023 §10.6"
)
