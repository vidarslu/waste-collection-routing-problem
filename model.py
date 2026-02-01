import gurobipy as gp
from gurobipy import GRB

# --- Optional visualization ---
import networkx as nx
import matplotlib.pyplot as plt

# -----------------------------
# Data
# -----------------------------
V = ['V1', 'V2', 'V3']      # Vehicles
C = ['N2', 'N3']            # Customers
D = ['N1']                  # Depot
F = ['N4']                  # Disposal facility
N = D + C + F               # All nodes

demands = {'N2': 5, 'N3': 7}
vehicle_capacities = {'V1': 10, 'V2': 8, 'V3': 12}

travel_costs = {
    ('N1', 'N2'): 4, ('N1', 'N3'): 6,
    ('N2', 'N3'): 2, ('N3', 'N2'): 2,   # add reverse if you want symmetry (optional)
    ('N2', 'N4'): 5, ('N3', 'N4'): 3,
    ('N4', 'N1'): 7,
    ('N2', 'N1'): 4, ('N3', 'N1'): 6,
    ('N4', 'N2'): 5, ('N4', 'N3'): 3
}

travel_times = {
    ('N1', 'N2'): 10, ('N1', 'N3'): 15,
    ('N2', 'N3'): 5,  ('N3', 'N2'): 5,   # optional reverse
    ('N2', 'N4'): 12, ('N3', 'N4'): 8,
    ('N4', 'N1'): 20,
    ('N2', 'N1'): 10, ('N3', 'N1'): 15,
    ('N4', 'N2'): 12, ('N4', 'N3'): 8
}

service_times = {'N2': 5, 'N3': 7}
max_shift_duration_vehicles = {'V1': 60, 'V2': 50, 'V3': 70}
big_m = 1e6

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

# Decision variables
x = m.addVars(V, A, vtype=GRB.BINARY, name="x")     # x[v,i,j] for (i,j) in A
u = m.addVars(V, N, lb=0.0, vtype=GRB.CONTINUOUS, lb=0.0, name="u")  # load upon arrival at node
T = m.addVars(V, N, lb=0.0, vtype=GRB.CONTINUOUS,lb=0.0, name="T")  # arrival time at node
y = m.addVars(V, vtype=GRB.BINARY, name="y")        # 1 if vehicle used

# Objective: minimize travel cost
m.setObjective(
    gp.quicksum(travel_costs[i, j] * x[v, i, j] for v in V for (i, j) in A),
    GRB.MINIMIZE
)

# -----------------------------
# Constraints
# -----------------------------

# 1) Each customer is visited exactly once (exactly one incoming arc to each customer)
m.addConstrs(
    (gp.quicksum(x[v, i, c] for v in V for (i, j) in A if j == c) == 1 for c in C),
    name="VisitOnce_in"
)

# 2) Flow conservation at customers for each vehicle
#    (inflow == outflow) at each customer for each vehicle
m.addConstrs(
    (
        gp.quicksum(x[v, i, n] for (i, j) in A if j == n) -
        gp.quicksum(x[v, n, j] for (i, j) in A if i == n)
        == 0
        for v in V for n in C
    ),
    name="FlowCustomers"
)

# 3) Vehicle usage pattern:
#    If vehicle is used: exactly one departure from depot, exactly one arrival to facility, exactly one facility->depot return.
#    If unused: all are 0.
m.addConstrs(
    (gp.quicksum(x[v, depot, j] for (i, j) in A if i == depot) == y[v] for v in V),
    name="StartDepot"
)
m.addConstrs(
    (gp.quicksum(x[v, i, facility] for (i, j) in A if j == facility) == y[v] for v in V),
    name="EndAtFacility"
)
m.addConstrs(
    (x[v, facility, depot] == y[v] if (facility, depot) in A else y[v] == 0 for v in V),
    name="FacilityToDepot"
)

# Prevent leaving the facility except to depot (keeps the route structure clean)
m.addConstrs(
    (
        gp.quicksum(x[v, facility, j] for (i, j) in A if i == facility and j != depot) == 0
        for v in V
    ),
    name="NoFacilityExitExceptDepot"
)

# Prevent going into depot except from facility (optional, but matches "return from facility to depot")
m.addConstrs(
    (
        gp.quicksum(x[v, i, depot] for (i, j) in A if j == depot and i != facility) == 0
        for v in V
    ),
    name="NoDepotInExceptFromFacility"
)

# 4) Capacity/load constraints
# Set load at depot and facility to 0 (arrival load there)
m.addConstrs((u[v, depot] == 0 for v in V), name="LoadAtDepotZero")
m.addConstrs((u[v, facility] == 0 for v in V), name="LoadAtFacilityZero")

# Bounds on load at customers
m.addConstrs((u[v, n] <= vehicle_capacities[v] for v in V for n in N), name="CapUpper")

# Load propagation: if v travels i->j then u[j] >= u[i] + demand[j]
# (Demand only nonzero at customers; depot/facility demand=0)
for v in V:
    Q = vehicle_capacities[v]
    for (i, j) in A:
        m.addConstr(
            u[v, j] >= u[v, i] + demand[j] - Q * (1 - x[v, i, j]),
            name=f"LoadProp_{v}_{i}_{j}"
        )

# 5) Time constraints
# Start time at depot = 0 if vehicle used (else also 0)
m.addConstrs((T[v, depot] == 0 for v in V), name="TimeAtDepotZero")

# Time propagation: if v travels i->j then T[j] >= T[i] + service[i] + travel_time(i,j)
for v in V:
    for (i, j) in A:
        m.addConstr(
            T[v, j] >= T[v, i] + service[i] + travel_times[i, j] - big_m * (1 - x[v, i, j]),
            name=f"TimeProp_{v}_{i}_{j}"
        )

# Shift duration: arrival back at depot (from facility) must be within max shift if used
# Since we forced facility->depot when used, this effectively bounds full route duration.
m.addConstrs(
    (T[v, depot] <= max_shift_duration_vehicles[v] + big_m * (1 - y[v]) for v in V),
    name="ShiftDuration"
)
# NOTE: T[v,depot] is fixed at 0 above, so the constraint above is trivial.
# Better: constrain arrival time at depot AFTER returning. We can instead constrain T at depot with a separate variable.
# Simple workaround: constrain arrival time at depot via facility->depot arc:
for v in V:
    if (facility, depot) in A:
        m.addConstr(
            T[v, depot] >= T[v, facility] + service[facility] + travel_times[facility, depot] - big_m * (1 - x[v, facility, depot]),
            name=f"ReturnTime_{v}"
        )
        m.addConstr(
            T[v, depot] <= max_shift_duration_vehicles[v] + big_m * (1 - y[v]),
            name=f"ReturnWithinShift_{v}"
        )

# -----------------------------
# Solve
# -----------------------------
m.Params.OutputFlag = 1
m.optimize()

# -----------------------------
# Print solution routes
# -----------------------------
if m.Status == GRB.OPTIMAL:
    print("\nOptimal objective:", m.ObjVal)

    for v in V:
        if y[v].X < 0.5:
            continue
        print(f"\nRoute for {v}:")
        # Build successor map
        succ = {}
        for (i, j) in A:
            if x[v, (i, j)].X > 0.5:
                succ[i] = j

        # Follow route from depot
        route = [depot]
        cur = depot
        for _ in range(len(N) + 5):
            if cur not in succ:
                break
            cur = succ[cur]
            route.append(cur)
            if cur == depot:
                break
        print(" -> ".join(route))

if m.Status == GRB.INFEASIBLE:
    print("INFEASIBLE -> computing IIS")
    m.computeIIS()
    m.write("model.ilp")  # åpnes i teksteditor, viser constraints i IIS
    print("Wrote IIS to model.ilp")

# -----------------------------
# Visualization
# -----------------------------
# Make a directed graph of the solution arcs
G = nx.DiGraph()
G.add_nodes_from(N)
for (i, j) in A:
    G.add_edge(i, j, weight=travel_costs[i, j])

# If you want fixed positions (nicer for tiny instances), define them:
pos = {
    'N1': (0, 0),   # depot
    'N2': (1, 1),
    'N3': (2, 1),
    'N4': (1.5, -0.5)  # facility
}

plt.figure()
nx.draw_networkx_nodes(G, pos)
nx.draw_networkx_labels(G, pos)

# Draw chosen edges per vehicle (no fancy coloring needed—just labels)

status = m.Status

if status == GRB.OPTIMAL or status == GRB.SUBOPTIMAL:

    for v in V:
        chosen = [(i, j) for (i, j) in A if x[v, i, j].X > 0.5]
        if chosen:
            nx.draw_networkx_edges(G, pos, edgelist=chosen, arrows=True)

plt.title("Chosen arcs (solution)")
plt.axis("off")
plt.show()
