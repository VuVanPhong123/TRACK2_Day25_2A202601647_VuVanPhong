# NimbusAI — GPU Cost Optimization Report

## Executive summary

**Period:** monthly  
**Baseline spend:** $27,133  
**Optimized spend:** $14,626  
**Projected savings:** $12,507  (**46%**)

The largest measured lever is **Purchasing (spot/reserved)**. The recommendation is to execute high-ROI, low-risk levers first, then use measurement gates before applying commitments or workload moves broadly.

## Savings by lever

| Lever | Savings (USD) | Share of baseline |
|---|---:|---:|
| Inference (cascade/cache/batch) | $1,212 | 4.5% |
| Purchasing (spot/reserved) | $10,040 | 37.0% |
| Right-size util-lies | $655 | 2.4% |
| Kill idle GPUs | $600 | 2.2% |

## Why GPU-Util can lie

`nvidia-smi` GPU-Util measures whether the device is active, not whether rented compute is being converted into useful model FLOPs. A GPU can therefore report ~98% utilization while MFU is only ~20% when kernels are memory-stalled, launch-bound, synchronization-bound, or otherwise doing little arithmetic. FinOps decisions should use MFU/MBU and workload throughput alongside GPU-Util; otherwise NimbusAI can pay a full GPU-hour for a fraction of the useful work.

## Prioritized action plan

1. **Apply inference levers first:** preserve quality gates while cascading easy requests to the small model, reusing prompt cache, and batching latency-tolerant work. These changes improve $/1M-token without long infrastructure commitments.
2. **Match purchasing tier to workload shape:** checkpoint interruptible jobs on spot, reserve steady high-duty workloads, and keep bursty workloads on-demand. Re-check interruption rates and commitment duration before signing reservations.
3. **Remove structural waste:** terminate idle GPUs and right-size low-MFU/low-MBU workloads only after confirming memory capacity and bandwidth requirements. Track MFU/MBU after each change to prevent false savings that degrade throughput.

## Sustainability

- Energy per representative query: 0.24 Wh
- Carbon per representative query in us-east-1: 0.091 gCO2e
- Electricity cost per representative query: $0.00002880
- Cleanest region in the lab snapshot: **europe-north1**
- Cheapest region in the lab snapshot: **us-east-wa**

Carbon and electricity price are separate objectives. The cleanest region is not automatically the cheapest, and latency-sensitive inference should not be moved solely for carbon savings. Carbon-aware scheduling is best applied first to interruptible/batch workloads.

## Extension 4 — Reasoning budget

The measured reasoning/non-reasoning split is shown explicitly so the budget decision is auditable rather than based only on percentages.

| Segment | Traffic share | Optimized cost/day | Energy/day | Cost share | Energy share |
|---|---:|---:|---:|---:|---:|
| Reasoning | 8.4% | $1.396 | 29,788 Wh | 16.5% | 94.0% |
| Non-reasoning | 91.6% | $7.084 | 1,888 Wh | 83.5% | 6.0% |

- Proposed budget: cap reasoning at **5%** of traffic and reserve it for the highest-complexity/output requests.
- Estimated reroutes: **81 requests/day**
- Estimated savings from the cap: **$0.226/day** and **7,880 Wh/day**.

Reasoning requests are a small traffic slice but can dominate energy because the lab applies an ~80× reasoning energy multiplier and also generates longer outputs. The policy therefore protects reasoning for requests most likely to benefit from it instead of enabling it indiscriminately.

## Extension 5 — Carbon-aware scheduling

Moving interruptible workloads from **us-east-1** to the cleanest region **europe-north1** would save approximately **626.1 kgCO2e** (92.1%) over the modeled workload durations.
Cheapest region: **us-east-wa** · Cleanest: **europe-north1** · Balanced cost/carbon score: **europe-north1**.

| Region | $/kWh | gCO2/kWh | Electricity cost | Carbon |
|---|---:|---:|---:|---:|
| us-east-1 | 0.120 | 380 | $214.68 | 679.8 kgCO2e |
| us-west-2 | 0.070 | 120 | $125.23 | 214.7 kgCO2e |
| europe-north1 | 0.090 | 30 | $161.01 | 53.7 kgCO2e |
| europe-central2 | 0.180 | 660 | $322.02 | 1,180.7 kgCO2e |
| us-east-wa | 0.055 | 90 | $98.39 | 161.0 kgCO2e |

The cleanest region may be farther from end users; move only interruptible/batch jobs while keeping latency-sensitive inference near users.

## Governance and measurement

Re-baseline prices and carbon factors before production action, keep tag coverage above the chargeback gate, and validate each optimization against throughput/latency/quality. Savings in this lab are deterministic June-2026 snapshots, not live cloud quotes.

_Figures are June-2026 as-of snapshots; re-baseline before acting._