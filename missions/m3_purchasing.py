"""M3 — Purchasing Strategy: break-even, tier choice, spot-checkpoint sim (deck §4).

Run: python missions/m3_purchasing.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num, catalog_by_type
from finops import pricing, sustainability

DAYS = 30
CURRENT_REGION = "us-east-1"


def run(verbose: bool = True) -> dict:
    jobs = load_csv("workloads.csv")
    cat = catalog_by_type()
    on_demand_monthly = optimized_monthly = 0.0
    recs = []
    carbon_jobs = []
    interruptible_kwh = 0.0

    cleanest_region = min(sustainability.REGION_CARBON, key=sustainability.REGION_CARBON.get)
    for j in jobs:
        gtype = j["gpu_type"]
        ngpu = int(num(j["num_gpus"]))
        hpd = num(j["hours_per_day"])
        interruptible = bool(int(num(j["interruptible"])))
        c = cat[gtype]
        gpu_hours = hpd * DAYS * ngpu
        od = num(c["on_demand_hr"])
        on_demand_cost = gpu_hours * od

        tier = pricing.recommend_tier(hpd, interruptible)
        if tier == "spot":
            sim = pricing.spot_checkpoint_cost(gpu_hours, num(c["spot_hr"]), od)
            opt_cost = sim["spot_cost"]
        elif tier == "reserved":
            opt_cost = gpu_hours * num(c["reserved_3yr_hr"])
        else:
            opt_cost = on_demand_cost

        on_demand_monthly += on_demand_cost
        optimized_monthly += opt_cost
        recs.append({"job_id": j["job_id"], "gpu_type": gtype, "tier": tier,
                     "on_demand": round(on_demand_cost), "optimized": round(opt_cost)})

        # Extension 5 — carbon-aware scheduling for jobs that can be moved in time/region.
        if interruptible:
            job_days = min(DAYS, max(0.0, num(j.get("days", DAYS), DAYS)))
            job_gpu_hours = hpd * job_days * ngpu
            energy_kwh = job_gpu_hours * num(c["watts"]) / 1000.0
            interruptible_kwh += energy_kwh
            current_g = energy_kwh * sustainability.REGION_CARBON[CURRENT_REGION]
            clean_g = energy_kwh * sustainability.REGION_CARBON[cleanest_region]
            carbon_jobs.append({
                "job_id": j["job_id"],
                "gpu_type": gtype,
                "energy_kwh": round(energy_kwh, 2),
                "current_region": CURRENT_REGION,
                "target_region": cleanest_region,
                "current_kgco2e": round(current_g / 1000.0, 2),
                "target_kgco2e": round(clean_g / 1000.0, 2),
                "saved_kgco2e": round((current_g - clean_g) / 1000.0, 2),
            })

    savings = on_demand_monthly - optimized_monthly
    savings_pct = savings / on_demand_monthly * 100 if on_demand_monthly else 0.0

    # Compare every available region using the same movable workload energy.
    region_matrix = []
    for region in sustainability.REGION_CARBON:
        region_matrix.append({
            "region": region,
            "price_per_kwh": sustainability.REGION_PRICE_KWH[region],
            "carbon_g_per_kwh": sustainability.REGION_CARBON[region],
            "electricity_cost_usd": round(interruptible_kwh * sustainability.REGION_PRICE_KWH[region], 2),
            "carbon_kgco2e": round(interruptible_kwh * sustainability.REGION_CARBON[region] / 1000.0, 2),
        })
    cheapest_region = min(sustainability.REGION_PRICE_KWH, key=sustainability.REGION_PRICE_KWH.get)
    min_price = min(sustainability.REGION_PRICE_KWH.values())
    min_carbon = min(sustainability.REGION_CARBON.values())
    balanced_region = min(
        sustainability.REGION_CARBON,
        key=lambda r: sustainability.REGION_PRICE_KWH[r] / min_price + sustainability.REGION_CARBON[r] / min_carbon,
    )
    current_total_g = interruptible_kwh * sustainability.REGION_CARBON[CURRENT_REGION]
    target_total_g = interruptible_kwh * sustainability.REGION_CARBON[cleanest_region]
    carbon_aware = {
        "current_region": CURRENT_REGION,
        "cleanest_region": cleanest_region,
        "cheapest_region": cheapest_region,
        "balanced_region": balanced_region,
        "interruptible_energy_kwh": round(interruptible_kwh, 2),
        "saved_kgco2e": round((current_total_g - target_total_g) / 1000.0, 2),
        "reduction_pct": round((1 - target_total_g / current_total_g) * 100, 1) if current_total_g else 0.0,
        "jobs": carbon_jobs,
        "region_matrix": region_matrix,
        "latency_tradeoff": "The cleanest region may be farther from end users; move only interruptible/batch jobs while keeping latency-sensitive inference near users.",
    }

    if verbose:
        print("== M3 Purchasing Strategy ==")
        print(f"break-even utilization @ 45% reserved discount = {pricing.break_even_utilization(0.45):.0%}")
        print(f"{'job':18}{'gpu':7}{'tier':11}{'on-demand':>12}{'optimized':>12}")
        for r in recs:
            print(f"{r['job_id']:18}{r['gpu_type']:7}{r['tier']:11}${r['on_demand']:>11,}${r['optimized']:>11,}")
        print(f"\nmonthly: on-demand ${on_demand_monthly:,.0f} -> optimized ${optimized_monthly:,.0f}  ({savings_pct:.1f}% saved)")
        print("\n-- Extension 5: Carbon-aware scheduling --")
        print(f"movable energy: {interruptible_kwh:,.1f} kWh; {CURRENT_REGION} -> {cleanest_region} saves {carbon_aware['saved_kgco2e']:,.1f} kgCO2e ({carbon_aware['reduction_pct']:.1f}%)")
        print(f"cheapest={cheapest_region}; cleanest={cleanest_region}; balanced={balanced_region}")
        print(f"{'region':18}{'$/kWh':>8}{'gCO2/kWh':>11}{'electricity':>13}{'kgCO2e':>10}")
        for r in region_matrix:
            print(f"{r['region']:18}{r['price_per_kwh']:>8.3f}{r['carbon_g_per_kwh']:>11.0f}${r['electricity_cost_usd']:>12,.2f}{r['carbon_kgco2e']:>10,.1f}")

    return {"recommendations": recs, "on_demand_monthly": round(on_demand_monthly),
            "optimized_monthly": round(optimized_monthly), "savings_pct": round(savings_pct, 1),
            "carbon_aware": carbon_aware}


if __name__ == "__main__":
    run()
