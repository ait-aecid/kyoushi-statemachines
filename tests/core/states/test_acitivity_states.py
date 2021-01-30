from typing import (
    Any,
    Dict,
)

from pytest_mock import MockFixture

from cr_kyoushi.simulation.logging import get_logger
from cr_kyoushi.simulation.transitions import Transition
from cr_kyoushi.statemachines.core.states import ActivityState


def test_activity_state_ret_increase(mocker: MockFixture):
    t1 = mocker.MagicMock(Transition)
    t2 = mocker.MagicMock(Transition)
    t3 = mocker.MagicMock(Transition)

    ret = mocker.MagicMock(Transition)
    increase = 1.03125

    log = get_logger()
    empty_context: Dict[str, Any] = {}

    transitions = [t1, t2, t3, ret]
    weights = [0.25] * 4
    modifiers = [1] * 4

    state = ActivityState(
        "test",
        transitions=transitions,
        weights=weights,
        modifiers=modifiers,
        ret_transition=ret,
        ret_increase=increase,
    )

    # simulate steps and check increase
    state.adapt_after(log, empty_context, t1)
    assert state.modifiers[3] == increase ** 1

    state.adapt_after(log, empty_context, t2)
    assert state.modifiers[3] == increase ** 2

    state.adapt_after(log, empty_context, t3)
    assert state.modifiers[3] == increase ** 3

    state.adapt_after(log, empty_context, ret)
    assert state.modifiers[3] == 1

    # double check
    assert state.modifiers == modifiers
