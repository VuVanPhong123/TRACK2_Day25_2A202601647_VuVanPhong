# Lab 25 — FinOps Write-up

## 1. Baseline vs. optimized
Monthly spend falls from **$27,133** to **$14,626**, saving **$12,507 (46.1%)**. Inference unit economics improve from **$6.488/1M-token** to **$1.126/1M-token**.

## 2. Lever analysis
The largest measured lever is **Purchasing (spot/reserved)** at approximately **$10,040** per month. Inference cascade/cache/batch reduces the cost per served token; purchasing optimization aligns spot/reserved/on-demand with interruption tolerance and duty cycle; right-sizing and idle shutdown remove capacity that is paid for but not productively used.

## 3. GPU-Util lie
Detected GPU-Util lie candidates: **gpu-h100-4, gpu-a10g-1**. High GPU-Util only proves that the GPU clock is active; low MFU shows that little peak arithmetic is being converted into useful work. Likely causes include memory stalls, synchronization, kernel-launch overhead, or workload shape, so MFU/MBU and throughput are required before a right-size decision.

## 4. Extensions implemented
**Reasoning budget:** reasoning is 8.4% of traffic, costs $1.396/day, and uses 29,788 Wh/day versus $7.084/day and 1,888 Wh/day for non-reasoning traffic. Capping reasoning at 5% is estimated to save $0.226/day and 7,880 Wh/day.
**Carbon-aware scheduling:** movable workloads can reduce modeled emissions by 626.1 kgCO2e (92.1%) by moving from us-east-1 to europe-north1. The cheapest and cleanest regions differ, so the decision must also respect latency/SLA.

## 5. First three actions as FinOps lead
1. Roll out inference cascade/cache/batch with quality and latency guardrails because it improves unit economics without long commitments.
2. Enforce a reasoning budget and use reasoning only for requests that need it; monitor cost, energy, and answer quality together.
3. Move checkpointable/batch jobs to the appropriate spot/clean-region schedule, then right-size or stop idle GPUs after MFU/MBU validation.

All figures come from the deterministic lab dataset and June-2026 illustrative price/carbon snapshots; production decisions require a fresh baseline.