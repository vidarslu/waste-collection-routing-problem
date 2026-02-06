# Waste Collection Routing Optimization

This repository works on a model to optimize real-world garbage collection operations. The time horizon is operational, and the objective is cost reduction.


Waste collection routing prototype. This repository contains a Gurobi-based optimization model, data schemas, and helper utilities to ingest CSVs, build an instance, solve, and visualize routes.

## Quick Start
1. Update CSVs in `data/` to reflect your customers, vehicles, depot, and facility.
2. Run the solver:

```bash
python model.py
```

## Project Structure
- `model.py`: Main optimization model, solver configuration, route summary, and visualization.
- `entities.py`: Domain classes for vehicles, customers, depot, and disposal facility.
- `data_io.py`: CSV loaders with validation.
- `instance_builder.py`: Converts domain objects into model inputs (sets, parameters, travel costs/times).
- `data/`: Sample CSV inputs for customers, vehicles, depot, and facility.
- `DATA_SCHEMA.md`: CSV format specification.
- `model_doc.tex`: LaTeX documentation of the mathematical model.
- `ROADMAP.md`: Product roadmap checklist.

## Notes
- The current model assumes exactly one depot and one disposal facility.
- Travel costs/times are derived from Euclidean distances between coordinates (placeholder for map APIs).
