# Roadmap Checklist

## Phase 1 — MVP Data + Solver (1–2 weeks)
- [ ] Define CSV schema for customers and vehicles (columns + types).
- [ ] Implement CSV upload parser with validation for required fields and coordinates.
- [ ] Build a model-builder function that converts uploaded data → `V, C, N, travel_costs, travel_times`.
- [ ] Add solver config options: `TimeLimit`, `MIPGap`, log level.
- [ ] Output basic route summaries (per-vehicle list of customer IDs + totals).

## Phase 2 — Map Integration (1–2 weeks)
- [ ] Choose map provider (Google, Here, Mapbox, OSRM).
- [ ] Implement distance matrix service with caching.
- [ ] Replace Euclidean distances with road network distances.
- [ ] Add road-closure input (blocked arcs) and reoptimize.

## Phase 3 — UI + Visualization (1–2 weeks)
- [ ] Build map view showing routes (polyline per vehicle).
- [ ] Show per-vehicle schedule (sequence, ETA, total time).
- [ ] Export results to CSV/PDF.

## Phase 4 — Reoptimization + Stability (1–2 weeks)
- [ ] Add reoptimize endpoint with changeset (vehicle off, new customer, closed road).
- [ ] Add stability penalty to reduce route churn.
- [ ] Add warm-start from previous solution.

## Phase 5 — Scalability + Ops (ongoing)
- [ ] Add sparsification rules (k-nearest, max drive time).
- [ ] Add heuristic fallback for quick feasible solutions.
- [ ] Add async job queue + progress updates.
- [ ] Load test with 100–500 customers.
