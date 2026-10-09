import pytest

from trip_planner.observability import TraceCollector


def test_trace_collector_records_successful_span():
    collector = TraceCollector()

    with collector.span("budget.calculate", {"trip_id": "trip-1"}):
        pass

    assert collector.records[0].status == "success"
    assert collector.records[0].operation == "budget.calculate"
    assert collector.records[0].duration_ms >= 0


def test_trace_collector_records_failed_span_and_reraises():
    collector = TraceCollector()

    with pytest.raises(RuntimeError):
        with collector.span("provider.search"):
            raise RuntimeError("timeout")

    assert collector.records[0].status == "failed"
    assert collector.records[0].error == "timeout"
