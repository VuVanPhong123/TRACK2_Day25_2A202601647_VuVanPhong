"""M5 — Optimization Report: combine M1-M4 into baseline-vs-optimized (deck §1/§11).

Run: python missions/m5_report.py   -> outputs/report.md + outputs/savings.png + outputs/writeup.md
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
from missions._common import num, catalog_by_type, ROOT
from finops import report, sustainability
from missions import m1_efficiency_audit, m2_inference_levers, m3_purchasing

DAYS = 30
# one tier down for over-provisioned ("util-lie") GPUs
RIGHTSIZE_MAP = {"H100": "A100", "H200": "H100", "A100": "A10G", "A10G": "L4", "L4": "L4"}


def run(verbose: bool = True) -> dict:
    r1 = m1_efficiency_audit.run(verbose=False)
    r2 = m2_inference_levers.run(verbose=False)
    r3 = m3_purchasing.run(verbose=False)
    cat = catalog_by_type()

    # --- buckets ---
    infer_savings = (r2["baseline_daily"] - r2["optimized_daily"]) * DAYS
    purchasing_savings = r3["on_demand_monthly"] - r3["optimized_monthly"]

    idle_savings = r1["idle_waste_daily"] * DAYS
    rightsize_savings = 0.0
    for lie in r1["lies"]:
        cur = lie["gpu_type"]
        tgt = RIGHTSIZE_MAP.get(cur, cur)
        delta = num(cat[cur]["on_demand_hr"]) - num(cat[tgt]["on_demand_hr"])
        rightsize_savings += max(0.0, delta) * 24 * DAYS

    levers = {
        "Inference (cascade/cache/batch)": round(infer_savings),
        "Purchasing (spot/reserved)": round(purchasing_savings),
        "Right-size util-lies": round(rightsize_savings),
        "Kill idle GPUs": round(idle_savings),
    }
    baseline = r2["baseline_daily"] * DAYS + r3["on_demand_monthly"]
    optimized = baseline - sum(levers.values())
    total_pct = sum(levers.values()) / baseline * 100 if baseline else 0.0

    # --- sustainability snapshot + extension outputs ---
    median_tokens = 800
    current_region = "us-east-1"
    wh = sustainability.wh_per_query(median_tokens)
    cleanest_region = min(sustainability.REGION_CARBON, key=sustainability.REGION_CARBON.get)
    cheapest_region = min(sustainability.REGION_PRICE_KWH, key=sustainability.REGION_PRICE_KWH.get)

    # Enrich Extension 4 with absolute values required by the rubric. M2 already
    # computes shares and total energy; deriving the split here keeps M2's public
    # result backward-compatible while making the report fully auditable.
    reasoning = dict(r2.get("reasoning", {}))
    traffic_share = reasoning.get("traffic_share", 0.0)
    cost_share = reasoning.get("cost_share", 0.0)
    energy_share = reasoning.get("energy_share", 0.0)
    total_cost_daily = float(r2.get("optimized_daily", 0.0))
    total_energy_wh_daily = float(reasoning.get("total_energy_wh_daily", 0.0))
    reasoning.update({
        "non_reasoning_traffic_share": max(0.0, 1.0 - traffic_share),
        "cost_daily": round(total_cost_daily * cost_share, 4),
        "non_reasoning_cost_daily": round(total_cost_daily * max(0.0, 1.0 - cost_share), 4),
        "non_reasoning_cost_share": max(0.0, 1.0 - cost_share),
        "energy_wh_daily": round(total_energy_wh_daily * energy_share, 2),
        "non_reasoning_energy_wh_daily": round(total_energy_wh_daily * max(0.0, 1.0 - energy_share), 2),
        "non_reasoning_energy_share": max(0.0, 1.0 - energy_share),
    })

    sust = {
        "wh_per_query": wh,
        "carbon_g": sustainability.carbon_g(wh, current_region),
        "energy_cost_usd": sustainability.energy_cost_usd(wh, current_region),
        "current_region": current_region,
        "cleanest_region": cleanest_region,
        "cheapest_region": cheapest_region,
        "reasoning": reasoning,
        "carbon_aware": r3.get("carbon_aware", {}),
    }

    md = report.build_report(baseline, optimized, levers, sustainability=sust)
    out_md = os.path.join(ROOT, "outputs", "report.md")
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)

    writeup = report.build_writeup(baseline, optimized, levers, r2, r1, sust)
    out_writeup = os.path.join(ROOT, "outputs", "writeup.md")
    with open(out_writeup, "w", encoding="utf-8") as f:
        f.write(writeup)

    png = report.savings_waterfall(
        levers,
        os.path.join(ROOT, "outputs", "savings.png"),
        baseline_usd=baseline,
    )

    if verbose:
        print("== M5 Optimization Report ==")
        print(md)
        suffix = " + outputs/savings.png" if png else " (matplotlib absent: PNG skipped)"
        print(f"\nWritten: outputs/report.md + outputs/writeup.md{suffix}")

    return {"baseline_monthly": round(baseline), "optimized_monthly": round(optimized),
            "levers": levers, "total_savings_pct": round(total_pct, 1),
            "reasoning": reasoning, "carbon_aware": r3.get("carbon_aware", {})}


if __name__ == "__main__":
    run()
