from trip_planner import TripSession
from trip_planner.planner import ItineraryPlanner, ItineraryVariant
from trip_planner.solver import DeterministicSolver, OptimizationObjective


def test_solver_scores_and_ranks_candidates():
    session = TripSession(
        trip_id="trip-1",
        user_id="user-1",
        destination="Ladakh",
        origin={"name": "Delhi"},
        dates={"start": "2026-10-01", "end": "2026-10-02"},
        duration_days=2,
        budget={"amount": 80000, "currency": "INR"},
    )
    planned = ItineraryPlanner().plan(session)
    candidates = list(planned.variants.values())
    ranked = DeterministicSolver().rank(candidates, OptimizationObjective.COST)

    assert len(ranked) == 3
    assert ranked[0][1].total_score <= ranked[-1][1].total_score


def test_solver_maps_each_variant_to_an_objective():
    solver = DeterministicSolver()

    assert solver.objective_for_variant(ItineraryVariant.COST_OPTIMIZED) is OptimizationObjective.COST
    assert solver.objective_for_variant(ItineraryVariant.TIME_OPTIMIZED) is OptimizationObjective.TIME
    assert solver.objective_for_variant(ItineraryVariant.EXPERIENCE_OPTIMIZED) is OptimizationObjective.EXPERIENCE
