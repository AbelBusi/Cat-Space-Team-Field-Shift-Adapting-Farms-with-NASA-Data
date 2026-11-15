"""Figure of the v1 -> v3 comparison for the paper (paper/figures/v3_overview.png), only from saved artifacts:
ml/artifacts/v3_era5_rain (summary, metrics, hindcasts, drought table) and ml/artifacts/api_validation, projections (v1).

    ml/.venv/bin/python ml/scripts/paper_v3_figure.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "ml" / "artifacts"
V3 = json.loads((A / "v3_era5_rain" / "summary.json").read_text())
CH1 = json.loads((A / "api_validation" / "checks.json").read_text())["checks"]
met = {(r["model"], r["metric"]): r for r in json.loads((A / "v3_era5_rain" / "validation_metrics_ci.json").read_text())["validation_2018_2022"]}
C1, C3, GRID = "#A88B5A", "#2E6E86", "#D9D9D9"          # DESIGN.md soil (v1) and deep (v3)

fig, ax = plt.subplots(2, 2, figsize=(11, 7.4))
plt.rcParams.update({"font.size": 9})

# (a) error of the one-step predictions
a = ax[0, 0]; sl = V3["second_look_2023_2025"]
groups = ["Validation\n2018–2022", "Second look\n2023–2025", "March 2023\n(coastal El Niño)"]
v1 = [met[("v1", "RMSE")]["value"], sl["rmse_v1"], sl["march_2023_rmse"]["v1"]]
v3 = [met[("v3", "RMSE")]["value"], sl["rmse_v3"], sl["march_2023_rmse"]["v3"]]
x = np.arange(3)
a.bar(x - 0.18, v1, 0.36, color=C1, label="v1 (CHIRPS rain)")
a.bar(x + 0.18, v3, 0.36, color=C3, label="v3 (+ ERA5-Land rain, monotone)")
for i in range(3):
    a.text(i - 0.18, v1[i] + 0.001, f"{v1[i]:.4f}", ha="center", fontsize=7.5)
    a.text(i + 0.18, v3[i] + 0.001, f"{v3[i]:.4f}", ha="center", fontsize=7.5)
a.set_xticks(x, groups); a.set_ylabel("RMSE (m³ m⁻³)"); a.set_title("(a) One-step error of the soil water model", loc="left")
a.legend(frameon=False, fontsize=8)

# (b) mean response to one changed input (checks S1 and S3), with the size required by S3
b = ax[0, 1]; c3 = V3["scenario_checks"]
labels = ["+2 °C", "−2 °C", "rain × 0.5", "rain × 2"]
r1 = [CH1["S1"]["mean_effect_plus2"], CH1["S1"]["mean_effect_minus2"], CH1["S3"]["mean_effect_half"], CH1["S3"]["mean_effect_double"]]
r3 = [c3["S1"]["mean_effect_plus2"], c3["S1"]["mean_effect_minus2"], c3["S3"]["mean_effect_half"], c3["S3"]["mean_effect_double"]]
x = np.arange(4)
b.axhline(0, color="black", lw=0.8)
for y in (0.003, -0.003):
    b.axhline(y, color="grey", lw=0.8, ls=":")
b.bar(x - 0.18, r1, 0.36, color=C1, label="v1"); b.bar(x + 0.18, r3, 0.36, color=C3, label="v3")
b.text(-0.45, -0.0045, "dotted: ±0.003, the size S3 asks for", ha="left", fontsize=7, color="grey")
b.set_xticks(x, labels); b.set_ylabel("Mean change at lead 3 (m³ m⁻³)")
b.set_title("(b) Response to one changed input (checks S1, S3)", loc="left"); b.legend(frameon=False, fontsize=8)

# (c) droughts of 1-6 months (check S2)
c = ax[1, 0]
d1 = pd.read_csv(A / "api_validation" / "s2_droughts.csv"); d3 = pd.read_csv(A / "v3_era5_rain" / "s2_droughts.csv")
c.plot(d1.months, d1.mean_change_end, "o-", color=C1, label="v1"); c.plot(d3.months, d3.mean_change_end, "o-", color=C3, label="v3")
c.axhline(0, color="black", lw=0.8)
c.set_xlabel("Months without rain"); c.set_ylabel("Change at the drought's end (m³ m⁻³)")
c.set_title("(c) Longer droughts dry the soil more (check S2)", loc="left"); c.legend(frameon=False, fontsize=8)

# (d) projection skill by lead, Validation hindcasts
d = ax[1, 1]
h1 = pd.read_csv(A / "projections" / "hindcast_skill_by_lead.csv"); h1 = h1[(h1.variable == "sm") & (h1.period == "validation")]
h3 = pd.read_csv(A / "v3_era5_rain" / "hindcast_skill_validation.csv")
for h, col, lab, off in ((h1, C1, "v1", -0.12), (h3, C3, "v3", 0.12)):
    d.errorbar(h.lead + off, h.skill, yerr=[h.skill - h.skill_ci_low, h.skill_ci_high - h.skill], fmt="o", color=col, ms=4, capsize=2, label=lab)
d.axhline(0, color="black", lw=0.8); d.axvline(6.5, color="grey", ls=":", lw=0.8)
d.text(6.6, 0.38, "useful lead\n6 months", fontsize=7, color="grey")
d.set_xlabel("Months ahead"); d.set_ylabel("Skill vs better simple rule (95 % CI)")
d.set_title("(d) Projection skill, hindcasts 2018–2022", loc="left"); d.legend(frameon=False, fontsize=8)

for a_ in ax.ravel():
    a_.spines[["top", "right"]].set_visible(False); a_.grid(axis="y", color=GRID, lw=0.5); a_.set_axisbelow(True)
fig.tight_layout()
out = ROOT / "paper" / "figures" / "v3_overview.png"
fig.savefig(out, dpi=200)
print(out)
