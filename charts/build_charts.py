"""Two real charts for the README: India diesel price history (showing the
2014 deregulation break the volatility calibration is built around), and the
option-value-vs-volatility sensitivity result.

Run:  python charts/build_charts.py
"""
import json
import math
import os

import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")

INK = "#1F3B4D"
MUTED = "#808080"
ACCENT = "#C0392B"


def chart_diesel_history():
    df = pd.read_csv(os.path.join(DATA, "diesel_price_india.csv")).sort_values("year")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(df["year"], df["avg_diesel_price_inr_per_litre"], color=INK, linewidth=2)
    ax.axvline(2014.75, color=MUTED, linestyle="--", linewidth=1)
    ax.text(2014.9, df["avg_diesel_price_inr_per_litre"].max() * 0.95,
            "Oct 2014: diesel pricing\nderegulated", color=MUTED, fontsize=9)
    ax.set_title("India average retail diesel price, 2004-2026", color=INK, fontsize=13, weight="bold")
    ax.set_ylabel("Rs per litre")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#E0E0E0", linewidth=0.7)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "01_diesel_price_history.png"), dpi=150)
    plt.close(fig)


def chart_sensitivity():
    calib = json.load(open(os.path.join(DATA, "volatility_calibration.json")))
    diesel_capex, fuel_eff, diesel_maint = 2550000, 5.5, 4.0
    ev_capex, charge_infra, battery, range_km, elec_price, ev_maint = 4000000, 300000, 453, 175, 7.5, 2.0
    dist, freight, overhead, r = 90000, 40, 60000, 0.12
    price0, mu = calib["last_price"], calib["mu_annual"]
    life = 8
    ann = (1 - (1 + r) ** -life) / r
    ev_eff = battery / range_km
    ev_cf = dist * (freight - ev_eff * elec_price - ev_maint) - overhead
    ev_now = -ev_capex - charge_infra + ev_cf * ann

    def invest_diesel(price):
        cf = dist * (freight - price / fuel_eff - diesel_maint) - overhead
        return -diesel_capex + cf * ann

    diesel_now = invest_diesel(price0)
    commit_now = max(ev_now, diesel_now)

    sigmas = [0.05 + 0.01 * i for i in range(41)]
    options = []
    for sigma in sigmas:
        u = math.exp(sigma)
        d = 1 / u
        p = (math.exp(mu) - d) / (u - d)
        up = max(ev_now, invest_diesel(price0 * u))
        down = max(ev_now, invest_diesel(price0 * d))
        wait = (p * up + (1 - p) * down) / (1 + r)
        options.append(max(commit_now, wait) - commit_now)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot([s * 100 for s in sigmas], options, color=INK, linewidth=2)
    ax.axvline(calib["sigma_annual"] * 100, color=ACCENT, linestyle="--", linewidth=1.2)
    ax.text(calib["sigma_annual"] * 100 + 0.6, max(options) * 0.9,
            f"India today\n({calib['sigma_annual']*100:.1f}%)", color=ACCENT, fontsize=9)
    ax.axvline(43, color=MUTED, linestyle="--", linewidth=1)
    ax.text(43 + 0.6, max(options) * 0.6, "Crude oil's own\nvolatility (~43%)", color=MUTED, fontsize=9)
    ax.set_title("Value of waiting to decide, vs diesel-price volatility", color=INK, fontsize=13, weight="bold")
    ax.set_xlabel("Annual volatility, sigma (%)")
    ax.set_ylabel("Option value (Rs)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#E0E0E0", linewidth=0.7)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "02_option_value_vs_volatility.png"), dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    chart_diesel_history()
    chart_sensitivity()
    print("wrote charts/01_diesel_price_history.png and charts/02_option_value_vs_volatility.png")
