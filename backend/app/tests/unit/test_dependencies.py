import uuid

from app.services.dependencies import graph_would_create_cycle


def test_self_dependency_is_a_cycle():
    task_id = uuid.uuid4()
    assert graph_would_create_cycle({}, task_id, task_id)


def test_indirect_cycle_is_detected_with_dfs():
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    graph = {a: [b], b: [c]}
    assert graph_would_create_cycle(graph, c, a)


def test_valid_dependency_is_accepted():
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    graph = {a: [b]}
    assert not graph_would_create_cycle(graph, b, c)


def test_existing_branches_do_not_cause_false_positive():
    a, b, c, d = (uuid.uuid4() for _ in range(4))
    graph = {a: [b, c], b: [d]}
    assert not graph_would_create_cycle(graph, c, d)
