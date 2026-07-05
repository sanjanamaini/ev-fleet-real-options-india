"""Calibrates diesel-price volatility and drift from real, sourced Indian
retail diesel price history (data/diesel_price_india.csv, annual averages,
2004-2026, source: cleartax.in historical diesel price compilation).

Uses the post-deregulation window (2015 onward) since India deregulated
diesel pricing in October 2014 -- before that, prices were subsidized and
administered on a different basis, so including the pre-2015 years would
mix two different pricing regimes into one volatility estimate.

Run:  python data/calibrate_volatility.py
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)


def main():
    df = pd.read_csv(os.path.join(HERE, "diesel_price_india.csv"))
    df = df.sort_values("year")
    prices = df["avg_diesel_price_inr_per_litre"].values
    years = df["year"].values

    log_ret_full = np.diff(np.log(prices))
    print(f"Full history ({years[0]}-{years[-1]}, n={len(log_ret_full)}): "
          f"sigma={log_ret_full.std(ddof=1):.4f}")

    post2015 = df[df["year"] >= 2015]
    p2015 = post2015["avg_diesel_price_inr_per_litre"].values
    log_ret = np.diff(np.log(p2015))
    sigma = log_ret.std(ddof=1)
    mu = log_ret.mean()
    print(f"Post-deregulation (2015-{years[-1]}, n={len(log_ret)}): "
          f"sigma={sigma:.4f}  mu={mu:.4f}")

    up_years = int((np.diff(prices) > 0).sum())
    print(f"Historical up-years (full history): {up_years} of {len(prices)-1}")

    u = np.exp(sigma)
    d = 1 / u
    p_up = (np.exp(mu) - d) / (u - d)
    print(f"\nLattice parameters: u={u:.4f}  d={d:.4f}  p(up)={p_up:.4f}")
    print(f"Expected log-return under lattice: {p_up*np.log(u)+(1-p_up)*np.log(d):.4f} (target mu={mu:.4f})")

    out = {
        "sigma_annual": float(sigma), "mu_annual": float(mu),
        "u": float(u), "d": float(d), "p_up": float(p_up),
        "last_price": float(prices[-1]), "last_year": int(years[-1]),
        "calibration_window": "2015-2026, post fuel-price-deregulation (Oct 2014)",
        "source": "cleartax.in historical diesel price compilation",
    }
    with open(os.path.join(HERE, "volatility_calibration.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nsaved data/volatility_calibration.json")


if __name__ == "__main__":
    main()
