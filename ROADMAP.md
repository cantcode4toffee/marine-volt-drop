# Feature Roadmap — Marine Volt Drop / Electrical Design Tool

## Where we are

Single-circuit volt drop checker for 9–36 V DC marine systems. Calculates:
- Voltage drop at 20°C (datasheet) and 90°C (operating temp), with pass/fail vs ABYC E-11 / ISO 13297 limits
- Max one-way run at the selected limit (calculated at 90°C so it's a true design guarantee)
- Ampacity check against IEC 60092-352:2005 Annex B (formula `I = α × A^0.625`, 90°C/45°C, ≤4 cables bunched)
- CSA sweep chart showing ±5 sizes around the selected cable

Cable resistance data: H+S RADOX 125 DOC-0000317514 at 20°C.
Standards: ABYC E-11 §11.15.1.2.7, ISO 13297:2020 §5.5–5.6, IEC 60092-352:2005.

---

## Priority 1 — Cable Sizing Auto-Recommendation

**What:** Inverse calculation — given current, run length, voltage, and circuit type, return the
minimum CSA that passes both volt drop and ampacity simultaneously.

**Why first:** Removes the manual trial-and-error of trying CSA sizes one at a time.

**How:**
- New toggle in sidebar: "Size for me" mode vs manual mode
- Iterate `cables.csv` smallest-first; return first row where:
  - `calc_max_length(v_nom, I, r, limit_pct) >= run_length_m` (VD passes at 90°C)
  - `ampacity_a >= current_a` (current rating passes)
- Show: recommended CSA, next size up for margin, and why each failing size was rejected
- Reuses existing `calc_max_length()` and `calc_volt_drop()` — no new formula needed

---

## Priority 2 — Installation Derating for Ampacity

**What:** Allow actual ambient temperature and cable group size as inputs so ampacity reflects
real installation conditions (engine rooms, dense cable trays).

**Why second:** Fixed 45°C/4-cable assumption is dangerously optimistic for engine space wiring.

**How:**
- Two new sidebar inputs: Ambient temperature (°C, default 45, range 20–80) and Cables in group (default 1)
- Temperature correction: `I_adj = I_base × sqrt((90 - T_amb) / (90 - 45))`
- Group correction factors from IEC 60092-352 Table A.6:
  - 1: 1.00 · 2: 0.80 · 3: 0.70 · 4: 0.65 · 5: 0.60 · 6: 0.57 · 7: 0.54 · 8: 0.52 · 9: 0.50 · ≥12: 0.45
- Pass/fail uses derated ampacity; show base and derated values side by side
- No new CSV needed — store correction factors as a dict in `app.py`

---

## Priority 3 — Extend Voltage Range to 48 V

**What:** Extend slider from 9–36 V to 9–60 V. Add 48 V nominal label.

**Why third:** 48 V is now common in electric auxiliary, hotel-load DC buses, and foiling craft.
Formulas are identical — only the slider cap and label function change.

**How:**
- `st.slider(..., max_value=60)` — covers 48 V nominal + 25% charge headroom
- Add to `nominal_label()`: `elif v <= 58: return "48 V nominal system"`
- Two one-line changes in `app.py`

---

## Priority 4 — Printable / Downloadable Calculation Sheet

**What:** `st.download_button` exporting the current calculation as an HTML file — printable and
attachable to design submissions. No new dependencies.

**How:**
- Optional free-text "Project / circuit label" input at top of sidebar
- Build HTML string from current session values:
  - Header: label, date, tool version
  - Inputs table: voltage, current, run length, CSA, circuit type
  - Results: VD cold/hot, V at load, pass/fail, max run, ampacity, utilisation
  - Footer: verbatim standard references
- `st.download_button(data=html_str, file_name="volt_drop_calc.html", mime="text/html")`
- Place below the CSA sweep chart

---

## Priority 5 (Medium-term) — Fuse / Circuit Breaker Sizing

**What:** Recommend a protective device rating per ABYC E-11 §11.4.

**Rules:**
- Device must be > load current (no nuisance trip)
- Device must be ≤ cable ampacity (cable is protected)
- Standard ratings (A): 5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 100, 125, 150, 175, 200,
  225, 250, 300, 350, 400, 450, 500

**How:** `recommend_fuse(current_a, ampacity_a)` — walk the ratings list, return smallest above
load current that is ≤ ampacity. Warn if no valid device exists.

---

## Priority 6 (Medium-term) — Multi-Circuit Load Schedule

**What:** Second tab where the user builds a list of circuits (label, voltage, current, run, CSA,
type). Summary table shows pass/fail for each; total load current shown at bottom.

**Why later:** Requires session-state list management and add/remove UI — bigger change. Do once
features 1–4 are stable.

**How:** `st.tabs(["Single circuit", "Load schedule"])`. Circuits stored as list of dicts in
`st.session_state["circuits"]`. Table rendered with `st.data_editor` for inline editing.

---

## Verification checklist

| Feature | Test |
|---|---|
| Cable sizing | 1A / 13V / 10m / critical → confirm recommended CSA; check smallest reject is explained |
| Derating | 60°C ambient, 6 cables → `I_adj = I_base × sqrt(30/45)` = 0.816 × base |
| 48V slider | Drag to 48V → label "48 V nominal system"; calcs update |
| Export | Download HTML → open in browser → all values match screen → print to PDF |
| Fuse sizing | 10A load / 40A cable → 15A fuse; 41A load / 40A cable → no valid device warning |
| Load schedule | Add 3 circuits → table shows all; edit one → updates; remove one → gone |
