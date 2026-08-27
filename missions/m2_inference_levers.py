"""M2 — Inference Cost Levers: $/1M-token, batch x cache x cascade (deck §7).

Run: python missions/m2_inference_levers.py
"""
from __future__ import annotations
import math
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num
from finops import pricing, sustainability

# $/1M tokens (input, output) — illustrative 2026.
MODEL_PRICES = {"small": (0.20, 0.40), "large": (3.00, 15.00)}
REASONING_TARGET_SHARE = 0.05
REASONING_OUTPUT_MULTIPLIER = 6  # matches data/generate.py


def run(verbose: bool = True) -> dict:
    rows = load_csv("token_usage.csv")
    base_cost = opt_cost = 0.0
    total_tokens = 0
    total_wh = reasoning_wh = reasoning_cost = 0.0
    reasoning_rows = []

    for r in rows:
        inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
        cached = int(num(r["cached_input_tokens"]))
        is_batch = bool(int(num(r["is_batch"])))
        is_reasoning = bool(int(num(r["is_reasoning"])))
        total_tokens += inp + out

        # BASELINE: naive deployment — everything on the large model, no cache, no batch.
        lin, lout = MODEL_PRICES["large"]
        base_cost += pricing.request_cost(inp, out, lin, lout)

        # OPTIMIZED: cascade (route_tier), prompt caching, batch API.
        pin, pout = MODEL_PRICES[r["route_tier"]]
        row_cost = pricing.request_cost(inp, out, pin, pout, cached_in=cached, batch=is_batch)
        opt_cost += row_cost

        row_wh = sustainability.wh_per_query(inp + out, is_reasoning=is_reasoning)
        total_wh += row_wh
        if is_reasoning:
            reasoning_cost += row_cost
            reasoning_wh += row_wh
            # Synthetic data models the reasoning tax as ~6x output tokens.  Estimate
            # the non-reasoning alternative for a measurable routing-budget scenario.
            normal_out = max(1, round(out / REASONING_OUTPUT_MULTIPLIER))
            normal_cost = pricing.request_cost(inp, normal_out, pin, pout, cached_in=cached, batch=is_batch)
            normal_wh = sustainability.wh_per_query(inp + normal_out, is_reasoning=False)
            reasoning_rows.append({
                "output_tokens": out,
                "actual_cost": row_cost,
                "normal_cost": normal_cost,
                "actual_wh": row_wh,
                "normal_wh": normal_wh,
            })

    base_pm = pricing.dollars_per_million(base_cost, total_tokens)
    opt_pm = pricing.dollars_per_million(opt_cost, total_tokens)
    savings_pct = (1 - opt_cost / base_cost) * 100 if base_cost else 0.0

    # Extension 4 — Reasoning budget. Keep reasoning for the most output-heavy
    # requests (a transparent complexity proxy in this synthetic dataset) and cap
    # reasoning to 5% of daily traffic; estimate the avoidable $ and Wh.
    reasoning_count = len(reasoning_rows)
    target_count = math.floor(len(rows) * REASONING_TARGET_SHARE)
    demote_count = max(0, reasoning_count - target_count)
    ranked = sorted(reasoning_rows, key=lambda x: x["output_tokens"], reverse=True)
    demoted = ranked[target_count:] if demote_count else []
    cap_cost_savings = sum(max(0.0, x["actual_cost"] - x["normal_cost"]) for x in demoted)
    cap_energy_savings = sum(max(0.0, x["actual_wh"] - x["normal_wh"]) for x in demoted)

    reasoning = {
        "traffic_share": reasoning_count / len(rows) if rows else 0.0,
        "cost_share": reasoning_cost / opt_cost if opt_cost else 0.0,
        "energy_share": reasoning_wh / total_wh if total_wh else 0.0,
        "target_share": REASONING_TARGET_SHARE,
        "demoted_requests": demote_count,
        "cap_cost_savings_daily": round(cap_cost_savings, 4),
        "cap_energy_savings_wh_daily": round(cap_energy_savings, 2),
        "total_energy_wh_daily": round(total_wh, 2),
    }

    if verbose:
        print("== M2 Inference Cost Levers ==")
        print(f"requests={len(rows)}  tokens={total_tokens:,}")
        print(f"baseline  : ${base_cost:,.2f}/day   ${base_pm:.3f}/1M-token")
        print(f"optimized : ${opt_cost:,.2f}/day   ${opt_pm:.3f}/1M-token")
        print(f"savings   : {savings_pct:.1f}%  (cascade + caching + batch)")
        print(f"discount stack (batch + 100% cache): {pricing.discount_stack(batch=True, cache_hit_frac=1.0):.3f} of naive")
        print("\n-- Extension 4: Reasoning budget --")
        print(f"reasoning traffic: {reasoning['traffic_share']:.1%}; cost: {reasoning['cost_share']:.1%}; energy: {reasoning['energy_share']:.1%}")
        print(f"policy: cap reasoning at {REASONING_TARGET_SHARE:.0%} and reserve it for highest-complexity/output requests")
        print(f"estimated avoidable: ${cap_cost_savings:.3f}/day and {cap_energy_savings:,.0f} Wh/day ({demote_count} requests rerouted)")

    return {
        "baseline_daily": round(base_cost, 2), "optimized_daily": round(opt_cost, 2),
        "baseline_per_m": round(base_pm, 3), "optimized_per_m": round(opt_pm, 3),
        "savings_pct": round(savings_pct, 1), "total_tokens": total_tokens,
        "reasoning": reasoning,
    }


if __name__ == "__main__":
    run()
