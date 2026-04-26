import math

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_i import (
    DeliveryRoutingIn, DeliveryRoutingOut, RouteOut, RoutingStop,
)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _route_distance(depot: tuple[float, float], stops: list[RoutingStop]) -> float:
    if not stops:
        return 0.0
    d = _haversine_km(depot[0], depot[1], stops[0].lat, stops[0].lon)
    for a, b in zip(stops, stops[1:]):
        d += _haversine_km(a.lat, a.lon, b.lat, b.lon)
    d += _haversine_km(stops[-1].lat, stops[-1].lon, depot[0], depot[1])
    return d


def _clarke_wright(depot: tuple[float, float],
                   stops: list[RoutingStop],
                   capacity: float,
                   n_vehicles: int) -> tuple[list[list[RoutingStop]], list[str]]:
    """
    Classic Clarke-Wright savings algorithm.
    Each stop starts on its own out-and-back route; routes merge greedily by
    largest savings while respecting vehicle capacity.
    """
    # Initial: one route per stop
    routes: dict[str, list[RoutingStop]] = {s.stop_id: [s] for s in stops}
    loads: dict[str, float] = {s.stop_id: s.demand for s in stops}

    # Compute savings for every pair (i, j): s_ij = d(0,i) + d(0,j) - d(i,j)
    savings: list[tuple[float, str, str]] = []
    for i, si in enumerate(stops):
        for sj in stops[i + 1:]:
            s = (_haversine_km(depot[0], depot[1], si.lat, si.lon)
                 + _haversine_km(depot[0], depot[1], sj.lat, sj.lon)
                 - _haversine_km(si.lat, si.lon, sj.lat, sj.lon))
            savings.append((s, si.stop_id, sj.stop_id))

    savings.sort(reverse=True)

    # Track which route each stop ends up in
    route_of: dict[str, str] = {sid: sid for sid in routes}

    for _, i_id, j_id in savings:
        ri = route_of[i_id]
        rj = route_of[j_id]
        if ri == rj:
            continue
        # Only merge if i is at end of one route and j is at start of the other (or vice versa)
        ri_route = routes[ri]
        rj_route = routes[rj]
        if loads[ri] + loads[rj] > capacity:
            continue

        merged = None
        if ri_route[-1].stop_id == i_id and rj_route[0].stop_id == j_id:
            merged = ri_route + rj_route
        elif ri_route[0].stop_id == i_id and rj_route[-1].stop_id == j_id:
            merged = rj_route + ri_route
        elif ri_route[-1].stop_id == i_id and rj_route[-1].stop_id == j_id:
            merged = ri_route + list(reversed(rj_route))
        elif ri_route[0].stop_id == i_id and rj_route[0].stop_id == j_id:
            merged = list(reversed(ri_route)) + rj_route

        if merged is None:
            continue

        new_key = ri
        routes[new_key] = merged
        loads[new_key] = loads[ri] + loads[rj]
        del routes[rj]
        del loads[rj]
        for s in merged:
            route_of[s.stop_id] = new_key

    final_routes = list(routes.values())
    final_routes.sort(key=lambda r: -sum(s.demand for s in r))   # biggest first

    if len(final_routes) <= n_vehicles:
        return final_routes, []

    # Drop overflow stops as "unrouted"
    routed = final_routes[:n_vehicles]
    unrouted_routes = final_routes[n_vehicles:]
    unrouted_ids = [s.stop_id for r in unrouted_routes for s in r]
    return routed, unrouted_ids


@register_model("M-I5")
class DeliveryRoutingModel(BaseMLModel[DeliveryRoutingIn, DeliveryRoutingOut]):
    metadata = ModelMetadata(
        model_id="M-I5", block="I",
        name="Delivery Routing (VRP)",
        version="1.0.0",
        algorithm="Clarke-Wright savings heuristic with capacity constraint (haversine distance)",
        is_stub=False,
        feature_names=["depot", "stops", "vehicle_capacity", "n_vehicles"],
        supported_explainers=["rule_based"],
        description="Capacitated vehicle routing — assigns stops to vehicles minimizing total distance.",
    )

    def predict(self, input_data: DeliveryRoutingIn) -> DeliveryRoutingOut:
        depot = (input_data.depot_lat, input_data.depot_lon)
        routes, unrouted = _clarke_wright(
            depot, input_data.stops,
            input_data.vehicle_capacity, input_data.n_vehicles,
        )

        route_outs: list[RouteOut] = []
        total = 0.0
        for vid, r in enumerate(routes, start=1):
            d = _route_distance(depot, r)
            total += d
            route_outs.append(RouteOut(
                vehicle_id=vid,
                stop_sequence=[s.stop_id for s in r],
                distance_km=round(d, 3),
                load=round(sum(s.demand for s in r), 3),
            ))

        return DeliveryRoutingOut(
            routes=route_outs,
            total_distance_km=round(total, 3),
            n_vehicles_used=len(route_outs),
            unrouted_stops=unrouted,
            method="clarke_wright_savings",
        )

    def explain(self, input_data: DeliveryRoutingIn) -> dict:
        return {
            "stop_geography": 0.50,
            "vehicle_capacity": 0.30,
            "fleet_size": 0.20,
        }
