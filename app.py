import streamlit as st
import pandas as pd

st.set_page_config(page_title="Marine Volt Drop Calculator", page_icon="⚡", layout="wide")


@st.cache_data
def load_data():
    cables = pd.read_csv("data/cables.csv")
    std_limits = pd.read_csv("data/standards_limits.csv")
    circuit_types = pd.read_csv("data/circuit_types.csv")
    system_voltages = pd.read_csv("data/system_voltages.csv")
    return cables, std_limits, circuit_types, system_voltages


cables, std_limits, circuit_types, system_voltages = load_data()


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


st.title("⚡ Marine Volt Drop Calculator")
st.caption(
    "Standards-verified volt drop calculator for marine electrical systems · "
    "Part of the Vita electrical design toolset"
)

# ── Sidebar inputs ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Circuit parameters")

    voltage_options = {
        f"{row.voltage_v}V — {row.label}": row.voltage_v
        for _, row in system_voltages.iterrows()
    }
    v_label = st.selectbox("System voltage", list(voltage_options.keys()), index=1)
    v_nom = voltage_options[v_label]

    if v_nom >= 400:
        st.warning("⚠️ HV system — see standards note in main panel.")

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
    default_limit = int(selected_ct.limit_pct_abyc)

    limit_pct = st.radio(
        "Voltage drop limit",
        options=[3, 10],
        format_func=lambda x: f"{x}% ({'critical' if x == 3 else 'non-critical'})",
        index=0 if default_limit == 3 else 1,
    )

# ── HV out-of-scope banner ────────────────────────────────────────────────────
if v_nom >= 400:
    st.error(
        "**HV systems (≥400 V DC): outside the scope of ABYC E-11 and ISO 13297.**  \n"
        "ABYC E-11 and ISO 13297 cover systems up to 50 V DC (ELV) and standard LV AC. "
        "For propulsion bus voltages of 400 V–800 V DC, refer to the **IEC 60092-350 series** "
        "and your classification society rules (DNV, Lloyd's, BV, etc.).  \n"
        "Volt-drop figures shown below are indicative only and must not be used for HV design approval."
    )

# ── Results ───────────────────────────────────────────────────────────────────
st.subheader("Results")

max_len = calc_max_length(v_nom, current_a, r_ohm_per_km, limit_pct)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Max circuit length", fmt_length(max_len))
with col2:
    st.metric("Cable CSA", f"{selected_cable['csa_mm2']} mm²")
with col3:
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
sweep_data = [
    {
        "CSA (mm²)": r["csa_mm2"],
        "Max circuit (m)": round(calc_max_length(v_nom, current_a, r["resistance_ohm_per_km"], limit_pct), 1),
    }
    for _, r in cables.iterrows()
    if calc_max_length(v_nom, current_a, r["resistance_ohm_per_km"], limit_pct) is not None
]
st.bar_chart(
    pd.DataFrame(sweep_data).set_index("CSA (mm²)"),
    y="Max circuit (m)",
    use_container_width=True,
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
