# EV Fleet Real Options, India

Should an Indian regional trucking operator buy a diesel truck, buy an electric
truck, or wait a year and decide with better information? A real-options
(binomial decision tree) model, built entirely on real, independently sourced
Indian data.

## Real inputs

| Input | Value | Source |
|---|---|---|
| Diesel truck (Ashok Leyland AVTR 1920 HG) | Rs 25.5 lakh capex, 5.5 km/L | trucksbuses.com, cardekho, 2026 |
| EV truck (Tata Prima E.28K) | Rs 40 lakh capex, 453 kWh battery, 175 km range | Tata Motors spec sheet, dealer listings, 2026 |
| Diesel price history | Annual averages, 2004-2026 | cleartax.in historical diesel price compilation |
| Diesel volatility and drift | sigma = 7.0%/yr, mu = 5.1%/yr | calibrated from the price history above, 2015-2026 post-deregulation window |

Every capex, efficiency, and range figure is a real, sourced number (see
`Inputs` sheet notes in the workbook for each one specifically); a few
operating estimates (electricity tariff, maintenance cost per km, freight
rate) are flagged as estimates rather than sourced figures, and are yellow
editable cells.

This is a standalone project with its own data and its own volatility
calibration. It shares a methodology, not a dataset, with an earlier US-focused
oil-shock stress test.

## Why India, and why this scope

Diesel pricing in India was administered until October 2014; the volatility
calibration uses only the post-deregulation window (2015-2026) so it isn't
mixing two different pricing regimes into one number.

This models a regional, return-to-base duty cycle, not long-haul interstate
trucking. The Tata Prima E.28K's real range (150-200 km/charge) is a hard
constraint for long-haul without en-route fast-charging infrastructure that
doesn't yet exist at scale in India. Regional distribution with overnight depot
charging is the use case where this truck's real specifications aren't a
binding constraint.

## Method

A 6-year (t = 0..5) recombining binomial lattice on the diesel price, with
`u = exp(sigma)`, `d = 1/u`, and a physical (drift-matched, not risk-neutral)
up-probability chosen so the lattice reproduces India's real historical drift,
not just its volatility. At every node, backward induction picks the best of:
buy an EV truck now, buy a diesel truck now, or wait one year and decide again
(zero cash flow while waiting). Every "buy" value gets a full fresh 8-year
truck life from that decision point, not a truncated remaining life.

## Findings

**At today's diesel price (Rs 98/litre), diesel dominates by a wide margin:**
buying diesel now is worth Rs 52.8 lakh vs Rs 37.1 lakh for EV, a 42% gap.

**The diesel price would need to rise to Rs 117.31/litre (+20%) before EV
becomes the better buy.** At India's real 5.1%/year historical drift, that
level is reached in roughly 3.5 years.

**The value of flexibility is exactly Rs 0 at India's real volatility.**
India's diesel price is low-volatility (7%/year) even though it trends up
steadily, so waiting to decide never beats just committing to the
currently-better option. See `charts/02_option_value_vs_volatility.png`: option
value stays flat at zero until volatility crosses roughly 38-40%, then rises.
Crude oil itself runs at about 43% annual volatility, so a market with that
much price risk (unlike India's administered, low-volatility diesel pricing)
is exactly where flexibility would start to be worth paying for. This is the
textbook real-options result, shown with real numbers rather than asserted.

**Practical read:** for a regional Indian fleet operator today, this isn't
"wait and see" -- it's "buy the diesel truck now, and re-run this same
calculation for the next truck purchase in 3-4 years," since that is roughly
when the crossover becomes plausible.

## Repo structure

```
data/
  diesel_price_india.csv          real annual average retail diesel prices, 2004-2026
  calibrate_volatility.py         computes sigma/mu/u/d/p from the post-2015 window
  volatility_calibration.json     calibration output, consumed by the Excel model
excel/
  build_model.py                  generates the full workbook (all live formulas)
  ev_real_options_india.xlsx      README, Inputs, Lattice, DecisionTree, Summary, Sensitivity
charts/
  build_charts.py                 regenerates both PNGs below
  01_diesel_price_history.png
  02_option_value_vs_volatility.png
```

Regenerate everything: `python data/calibrate_volatility.py`, then
`python excel/build_model.py`, then `python charts/build_charts.py`.
