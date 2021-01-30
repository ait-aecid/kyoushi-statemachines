from typing import (
    Any,
    Dict,
)

from pytest_mock import MockFixture

from cr_kyoushi.simulation.logging import get_logger
from cr_kyoushi.simulation.model import ApproximateFloat
from cr_kyoushi.simulation.util import now
from cr_kyoushi.statemachines.core.transitions import Idle


def test_idle_given_no_end_time(mocker: MockFixture):
    idle_amount = ApproximateFloat(min=0.5, max=1.5)
    context: Dict[str, Any] = {}
    idle = Idle(idle_amount=idle_amount)

    # mock sleep functions
    sleep_mock = mocker.patch(
        "cr_kyoushi.statemachines.core.transitions.sleep", return_value=None
    )
    sleep_until_mock = mocker.patch(
        "cr_kyoushi.statemachines.core.transitions.sleep_until",
        return_value=None,
    )

    idle(
        log=get_logger(),
        current_state="STATE",
        context=context,
        target="TARGET",
    )

    assert sleep_mock.mock_calls == [mocker.call(idle_amount)]
    assert sleep_until_mock.mock_calls == []


def test_idle_given_end_time(mocker: MockFixture):
    idle_amount = ApproximateFloat(min=1.5, max=1.5)
    context: Dict[str, Any] = {}
    current_time = now()
    idle = Idle(idle_amount=idle_amount, end_time=current_time)

    # mock sleep functions
    sleep_mock = mocker.patch(
        "cr_kyoushi.statemachines.core.transitions.sleep", return_value=None
    )
    sleep_until_mock = mocker.patch(
        "cr_kyoushi.statemachines.core.transitions.sleep_until",
        return_value=None,
    )
    # mock now to ensure that current_time is always the same
    mocker.patch(
        "cr_kyoushi.statemachines.core.transitions.now",
        return_value=current_time,
    )

    idle(
        log=get_logger(),
        current_state="STATE",
        context=context,
        target="TARGET",
    )

    assert sleep_mock.mock_calls == []
    assert sleep_until_mock.mock_calls == [mocker.call(current_time)]
