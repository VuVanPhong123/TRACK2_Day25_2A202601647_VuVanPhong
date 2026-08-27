"""Report assembly — the lab's deliverable: baseline vs optimized + savings chart."""
from __future__ import annotations


def _money(x: float) -> str:
    return f"${x:,.0f}"


def build_report(baseline_usd: float, optimized_usd: float, levers: dict,
                 sustainability: dict | None = None, period: str = "monthly") -> str:
    """Return a rubric-complete markdown cost-optimization report."""
    savings = baseline_usd - optimized_usd
    pct = (savings / baseline_usd * 100.0) if baseline_usd > 0 else 0.0
    ordered = sorted(levers.items(), key=lambda kv: kv[1], reverse=True)
    top_lever = ordered[0][0] if ordered else "n/a"

    lines = [
        "# NimbusAI — GPU Cost Optimization Report",
        "",
        "## Executive summary",
        "",
        f"**Period:** {period}  ",
        f"**Baseline spend:** {_money(baseline_usd)}  ",
        f"**Optimized spend:** {_money(optimized_usd)}  ",
        f"**Projected savings:** {_money(savings)}  (**{pct:.0f}%**)",
        "",
        f"The largest measured lever is **{top_lever}**. The recommendation is to execute high-ROI, low-risk levers first, then use measurement gates before applying commitments or workload moves broadly.",
        "",
        "## Savings by lever",
        "",
        "| Lever | Savings (USD) | Share of baseline |",
        "|---|---:|---:|",
    ]
    for name, amount in levers.items():
        share = amount / baseline_usd * 100.0 if baseline_usd else 0.0
        lines.append(f"| {name} | ${amount:,.0f} | {share:.1f}% |")

    lines += [
        "",
        "## Why GPU-Util can lie",
        "",
        "`nvidia-smi` GPU-Util measures whether the device is active, not whether rented compute is being converted into useful model FLOPs. A GPU can therefore report ~98% utilization while MFU is only ~20% when kernels are memory-stalled, launch-bound, synchronization-bound, or otherwise doing little arithmetic. FinOps decisions should use MFU/MBU and workload throughput alongside GPU-Util; otherwise NimbusAI can pay a full GPU-hour for a fraction of the useful work.",
        "",
        "## Prioritized action plan",
        "",
        "1. **Apply inference levers first:** preserve quality gates while cascading easy requests to the small model, reusing prompt cache, and batching latency-tolerant work. These changes improve $/1M-token without long infrastructure commitments.",
        "2. **Match purchasing tier to workload shape:** checkpoint interruptible jobs on spot, reserve steady high-duty workloads, and keep bursty workloads on-demand. Re-check interruption rates and commitment duration before signing reservations.",
        "3. **Remove structural waste:** terminate idle GPUs and right-size low-MFU/low-MBU workloads only after confirming memory capacity and bandwidth requirements. Track MFU/MBU after each change to prevent false savings that degrade throughput.",
    ]

    if sustainability:
        lines += [
            "",
            "## Sustainability",
            "",
            f"- Energy per representative query: {sustainability.get('wh_per_query', 0):.2f} Wh",
            f"- Carbon per representative query in {sustainability.get('current_region', 'us-east-1')}: {sustainability.get('carbon_g', 0):.3f} gCO2e",
            f"- Electricity cost per representative query: ${sustainability.get('energy_cost_usd', 0):.8f}",
            f"- Cleanest region in the lab snapshot: **{sustainability.get('cleanest_region', 'n/a')}**",
            f"- Cheapest region in the lab snapshot: **{sustainability.get('cheapest_region', 'n/a')}**",
            "",
            "Carbon and electricity price are separate objectives. The cleanest region is not automatically the cheapest, and latency-sensitive inference should not be moved solely for carbon savings. Carbon-aware scheduling is best applied first to interruptible/batch workloads.",
        ]

        reasoning = sustainability.get("reasoning") or {}
        if reasoning:
            lines += [
                "",
                "## Extension 4 — Reasoning budget",
                "",
                f"- Reasoning traffic share: **{reasoning.get('traffic_share', 0):.1%}**",
                f"- Share of optimized inference cost: **{reasoning.get('cost_share', 0):.1%}**",
                f"- Share of inference energy: **{reasoning.get('energy_share', 0):.1%}**",
                f"- Proposed budget: cap reasoning at **{reasoning.get('target_share', 0):.0%}** of traffic and reserve it for the highest-complexity/output requests.",
                f"- Estimated reroutes: **{reasoning.get('demoted_requests', 0)} requests/day**",
                f"- Estimated savings from the cap: **${reasoning.get('cap_cost_savings_daily', 0):.3f}/day** and **{reasoning.get('cap_energy_savings_wh_daily', 0):,.0f} Wh/day**.",
                "",
                "Reasoning requests are a small traffic slice but can dominate energy because the lab applies an ~80× reasoning energy multiplier and also generates longer outputs. The policy therefore protects reasoning for requests most likely to benefit from it instead of enabling it indiscriminately.",
            ]

        carbon = sustainability.get("carbon_aware") or {}
        if carbon:
            lines += [
                "",
                "## Extension 5 — Carbon-aware scheduling",
                "",
                f"Moving interruptible workloads from **{carbon.get('current_region', 'n/a')}** to the cleanest region **{carbon.get('cleanest_region', 'n/a')}** would save approximately **{carbon.get('saved_kgco2e', 0):,.1f} kgCO2e** ({carbon.get('reduction_pct', 0):.1f}%) over the modeled workload durations.",
                f"Cheapest region: **{carbon.get('cheapest_region', 'n/a')}** · Cleanest: **{carbon.get('cleanest_region', 'n/a')}** · Balanced cost/carbon score: **{carbon.get('balanced_region', 'n/a')}**.",
                "",
                "| Region | $/kWh | gCO2/kWh | Electricity cost | Carbon |",
                "|---|---:|---:|---:|---:|",
            ]
            for row in carbon.get("region_matrix", []):
                lines.append(
                    f"| {row['region']} | {row['price_per_kwh']:.3f} | {row['carbon_g_per_kwh']:.0f} | ${row['electricity_cost_usd']:,.2f} | {row['carbon_kgco2e']:,.1f} kgCO2e |"
                )
            lines += [
                "",
                carbon.get("latency_tradeoff", "Move only workloads whose latency/SLA permits regional scheduling."),
            ]

    lines += [
        "",
        "## Governance and measurement",
        "",
        "Re-baseline prices and carbon factors before production action, keep tag coverage above the chargeback gate, and validate each optimization against throughput/latency/quality. Savings in this lab are deterministic June-2026 snapshots, not live cloud quotes.",
        "",
        "_Figures are June-2026 as-of snapshots; re-baseline before acting._",
    ]
    return "\n".join(lines)


def build_writeup(baseline_usd: float, optimized_usd: float, levers: dict,
                  m2: dict, m1: dict, sustainability: dict) -> str:
    """Create the short submission write-up requested by Guide.md."""
    savings = baseline_usd - optimized_usd
    pct = savings / baseline_usd * 100.0 if baseline_usd else 0.0
    top_name, top_value = max(levers.items(), key=lambda kv: kv[1]) if levers else ("n/a", 0)
    lie_ids = ", ".join(x["gpu_id"] for x in m1.get("lies", [])) or "none"
    reasoning = sustainability.get("reasoning", {})
    carbon = sustainability.get("carbon_aware", {})
    return "\n".join([
        "# Lab 25 — FinOps Write-up",
        "",
        "## 1. Baseline vs. optimized",
        f"Monthly spend falls from **{_money(baseline_usd)}** to **{_money(optimized_usd)}**, saving **{_money(savings)} ({pct:.1f}%)**. Inference unit economics improve from **${m2.get('baseline_per_m', 0):.3f}/1M-token** to **${m2.get('optimized_per_m', 0):.3f}/1M-token**.",
        "",
        "## 2. Lever analysis",
        f"The largest measured lever is **{top_name}** at approximately **{_money(top_value)}** per month. Inference cascade/cache/batch reduces the cost per served token; purchasing optimization aligns spot/reserved/on-demand with interruption tolerance and duty cycle; right-sizing and idle shutdown remove capacity that is paid for but not productively used.",
        "",
        "## 3. GPU-Util lie",
        f"Detected GPU-Util lie candidates: **{lie_ids}**. High GPU-Util only proves that the GPU clock is active; low MFU shows that little peak arithmetic is being converted into useful work. Likely causes include memory stalls, synchronization, kernel-launch overhead, or workload shape, so MFU/MBU and throughput are required before a right-size decision.",
        "",
        "## 4. Extensions implemented",
        f"**Reasoning budget:** reasoning is {reasoning.get('traffic_share', 0):.1%} of traffic but {reasoning.get('energy_share', 0):.1%} of modeled inference energy. Capping it at {reasoning.get('target_share', 0):.0%} and reserving it for the highest-complexity requests is estimated to save ${reasoning.get('cap_cost_savings_daily', 0):.3f}/day and {reasoning.get('cap_energy_savings_wh_daily', 0):,.0f} Wh/day.",
        f"**Carbon-aware scheduling:** movable workloads can reduce modeled emissions by {carbon.get('saved_kgco2e', 0):,.1f} kgCO2e ({carbon.get('reduction_pct', 0):.1f}%) by moving from {carbon.get('current_region', 'n/a')} to {carbon.get('cleanest_region', 'n/a')}. The cheapest and cleanest regions differ, so the decision must also respect latency/SLA.",
        "",
        "## 5. First three actions as FinOps lead",
        "1. Roll out inference cascade/cache/batch with quality and latency guardrails because it improves unit economics without long commitments.",
        "2. Enforce a reasoning budget and use reasoning only for requests that need it; monitor cost, energy, and answer quality together.",
        "3. Move checkpointable/batch jobs to the appropriate spot/clean-region schedule, then right-size or stop idle GPUs after MFU/MBU validation.",
        "",
        "All figures come from the deterministic lab dataset and June-2026 illustrative price/carbon snapshots; production decisions require a fresh baseline.",
    ])


def savings_waterfall(levers: dict, path: str) -> str:
    """Write a simple savings bar chart PNG. Returns the path. No-op if matplotlib absent."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return ""
    names = list(levers.keys())
    vals = [levers[n] for n in names]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(names, vals, color="#2e548a")
    ax.set_ylabel("Savings (USD / month)")
    ax.set_title("GPU cost savings by FinOps lever")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
