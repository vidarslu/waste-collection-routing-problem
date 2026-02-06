import gurobipy as gp
from gurobipy import GRB
from pathlib import Path

# --- Optional visualization ---
import networkx as nx
import matplotlib.pyplot as plt

from data_io import (
    load_customers_csv,
    load_depots_csv,
    load_facilities_csv,
    load_vehicles_csv,
)
from instance_builder import build_instance

# -----------------------------
# Data
# -----------------------------
DATA_DIR = Path("data")
customers = load_customers_csv(DATA_DIR / "customers.csv")
vehicles = load_vehicles_csv(DATA_DIR / "vehicles.csv")
depots = load_depots_csv(DATA_DIR / "depots.csv")
facilities = load_facilities_csv(DATA_DIR / "facilities.csv")

instance = build_instance(
    vehicles,
    customers,
    depots,
    facilities,
    cost_per_unit=1.0,
    time_per_unit=3.0,
)

V = instance["V"]      # Vehicles
C = instance["C"]      # Customers
D = instance["D"]      # Depot
F = instance["F"]      # Disposal facility
N = instance["N"]      # All nodes

demands = instance["demands"]
vehicle_capacities = instance["vehicle_capacities"]
vehicle_startup_costs = instance["vehicle_startup_costs"]
travel_costs = instance["travel_costs"]
travel_times = instance["travel_times"]
service_times = instance["service_times"]
max_shift_duration_vehicles = instance["max_shift_duration_vehicles"]
node_positions = instance["node_positions"]

# Convenience
A = list(travel_costs.keys())
demand = {i: demands.get(i, 0) for i in N}
service = {i: service_times.get(i, 0) for i in N}
depot = D[0]
facility = F[0]

# -----------------------------
# Model
# -----------------------------
m = gp.Model("Waste_Collection_Routing")

# Solver configuration (set to None to disable a parameter)
SOLVER_CONFIG = {
    "TimeLimit": 60,
    "MIPGap": 0.05,
    "OutputFlag": 1,
}
for param, value in SOLVER_CONFIG.items():
    if value is not None:
        m.setParam(param, value)

# Decision variables
x = m.addVars(A, V, vtype=GRB.BINARY, name="x")          # 1 if vehicle k uses arc (i, j)
y = m.addVars(V, vtype=GRB.BINARY, name="y")             # 1 if vehicle k is used
u = m.addVars(C, V, lb=0.0, name="u")                    # load after servicing customer i

# Objective: minimize total travel cost
m.setObjective(
    gp.quicksum(travel_costs[i, j] * x[i, j, k] for (i, j) in A for k in V)
    + gp.quicksum(vehicle_startup_costs[k] * y[k] for k in V),
    GRB.MINIMIZE,
)

# Each customer is visited exactly once (in and out)
for c in C:
    m.addConstr(
        gp.quicksum(x[c, j, k] for k in V for j in N if (c, j) in travel_costs) == 1,
        name=f"visit_out_{c}",
    )
    m.addConstr(
        gp.quicksum(x[i, c, k] for k in V for i in N if (i, c) in travel_costs) == 1,
        name=f"visit_in_{c}",
    )

# Flow conservation and depot start/end
for k in V:
    m.addConstr(
        gp.quicksum(x[depot, j, k] for j in N if (depot, j) in travel_costs) == y[k],
        name=f"depot_out_{k}",
    )
    m.addConstr(
        gp.quicksum(x[i, depot, k] for i in N if (i, depot) in travel_costs) == y[k],
        name=f"depot_in_{k}",
    )

    # If a vehicle serves any customer, it must be used
    for c in C:
        m.addConstr(
            gp.quicksum(x[c, j, k] for j in N if (c, j) in travel_costs) <= y[k],
            name=f"use_link_{c}_{k}",
        )

    # Flow conservation at customers and facility
    for n in C + F:
        m.addConstr(
            gp.quicksum(x[n, j, k] for j in N if (n, j) in travel_costs)
            == gp.quicksum(x[i, n, k] for i in N if (i, n) in travel_costs),
            name=f"flow_{n}_{k}",
        )

    # Require a disposal facility visit if the vehicle is used
    m.addConstr(
        gp.quicksum(x[i, facility, k] for i in N if (i, facility) in travel_costs) >= y[k],
        name=f"facility_in_{k}",
    )

    # Enforce return to depot from facility only
    for i in C:
        if (i, depot) in travel_costs:
            m.addConstr(x[i, depot, k] == 0, name=f"no_cust_to_depot_{i}_{k}")

# Capacity and subtour elimination via load variables
for k in V:
    cap = vehicle_capacities[k]

    for c in C:
        inbound = gp.quicksum(x[i, c, k] for i in N if (i, c) in travel_costs)
        m.addConstr(u[c, k] <= cap * inbound, name=f"load_ub_{c}_{k}")
        m.addConstr(u[c, k] >= demand[c] * inbound, name=f"load_lb_{c}_{k}")

    # From depot/facility to customer: load starts at demand
    for j in C:
        for i in [depot, facility]:
            if (i, j) in travel_costs:
                m.addConstr(
                    u[j, k] >= demand[j] - cap * (1 - x[i, j, k]),
                    name=f"load_start_{i}_{j}_{k}",
                )

    # Between customers: propagate load
    for i in C:
        for j in C:
            if (i, j) in travel_costs:
                m.addConstr(
                    u[j, k] >= u[i, k] + demand[j] - cap * (1 - x[i, j, k]),
                    name=f"load_{i}_{j}_{k}",
                )

# Shift duration (travel + service) per vehicle
for k in V:
    m.addConstr(
        gp.quicksum(
            (travel_times[i, j] + service[i]) * x[i, j, k] for (i, j) in A
        )
        <= max_shift_duration_vehicles[k],
        name=f"shift_{k}",
    )

# -----------------------------
# Solve
# -----------------------------
m.optimize()

# -----------------------------
# Output summary
# -----------------------------
def _extract_route(selected_arcs, start, max_steps):
    next_map = {i: j for (i, j) in selected_arcs}
    route = [start]
    cur = start
    for _ in range(max_steps):
        if cur not in next_map:
            break
        nxt = next_map[cur]
        route.append(nxt)
        cur = nxt
        if cur == start:
            break
    return route


if m.SolCount > 0:
    print("\nRoute summary:")
    for k in V:
        if y[k].X < 0.5:
            continue
        arcs_k = [(i, j) for (i, j) in A if x[i, j, k].X > 0.5]
        route = _extract_route(arcs_k, depot, max_steps=len(N) + 5)
        customers_served = [n for n in route if n in C]
        total_cost = sum(travel_costs[i, j] for (i, j) in arcs_k) + vehicle_startup_costs[k]
        total_time = sum(travel_times[i, j] + service[i] for (i, j) in arcs_k)

        print(f"- {k}:")
        print(f"  Route: {' -> '.join(route)}")
        print(f"  Customers: {', '.join(customers_served) if customers_served else 'None'}")
        print(f"  Cost: {total_cost}")
        print(f"  Time: {total_time}")

# -----------------------------
# Visualization
# -----------------------------
if m.SolCount > 0:
    # Collect selected arcs by vehicle
    selected = {k: [] for k in V}
    for (i, j) in A:
        for k in V:
            if x[i, j, k].X > 0.5:
                selected[k].append((i, j))

    # Build graph
    G = nx.DiGraph()
    G.add_nodes_from(N)
    for k in V:
        G.add_edges_from(selected[k])

    # Node positions (fallback to spring layout)
    pos = {n: node_positions[n] for n in N}
    if set(pos.keys()) != set(N):
        pos = nx.spring_layout(G, seed=7)

    # Styling
    node_colors = []
    for n in N:
        if n == depot:
            node_colors.append("#1f77b4")  # depot
        elif n == facility:
            node_colors.append("#2ca02c")  # facility
        else:
            node_colors.append("#ff7f0e")  # customers

    plt.figure(figsize=(8, 5))
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=900)
    nx.draw_networkx_labels(G, pos, font_color="white")

    edge_colors = {
        "V1": "#d62728",
        "V2": "#9467bd",
        "V3": "#8c564b",
    }
    for k in V:
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=selected[k],
            edge_color=edge_colors.get(k, "#7f7f7f"),
            width=2.5,
            arrows=True,
            arrowsize=18,
            connectionstyle="arc3,rad=0.1",
            label=k,
        )

    # Legend
    for k in V:
        plt.plot([], [], color=edge_colors.get(k, "#7f7f7f"), label=k, linewidth=2.5)
    plt.legend(title="Vehicle", loc="upper left")

    plt.title("Waste Collection Routing Solution")
    plt.axis("off")
    plt.tight_layout()
    plt.show()
else:
    print("No feasible solution available to visualize.")
