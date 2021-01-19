import json

import pytest

from pydantic import ValidationError

from cr_kyoushi.simulation.model import ApproximateFloat
from cr_kyoushi.statemachines.core.config import ProbabilisticStateConfig
from cr_kyoushi.statemachines.core.config import ProbVal


class ValidProbConfig(ProbabilisticStateConfig):
    a: ProbVal
    b: ProbVal
    c: ProbVal
    d: ProbVal


class InvalidProbConfigComplex(ProbabilisticStateConfig):
    a: ProbVal
    b: ProbVal
    c: ProbVal
    d: ApproximateFloat


class InvalidProbConfigSimple(ProbabilisticStateConfig):
    a: ProbVal
    b: ProbVal
    c: ProbVal
    d: str


@pytest.mark.parametrize(
    "a, b, c, d",
    [
        pytest.param(25, 25, 25, 25, id="int-uniform-probabilities"),
        pytest.param(0.25, 0.25, 0.25, 0.25, id="float-uniform-probabilities"),
        pytest.param(5, 20, 25, 50, id="int-mixed-probabilities"),
        pytest.param(0.05, 0.2, 0.25, 0.5, id="float-mixed-probabilities"),
        pytest.param(25.5, 24.5, 25, 25, id="float-int-probabilities"),
    ],
)
def test_given_valid_class_and_config_validates(a, b, c, d):
    assert ValidProbConfig(a=a, b=b, c=c, d=d).dict() == {
        "a": a,
        "b": b,
        "c": c,
        "d": d,
    }
    assert ValidProbConfig.parse_raw(
        json.dumps(
            {
                "a": a,
                "b": b,
                "c": c,
                "d": d,
            }
        )
    ).dict() == {
        "a": a,
        "b": b,
        "c": c,
        "d": d,
    }


@pytest.mark.parametrize(
    "a, b, c, d",
    [
        pytest.param(25, 25, 25, 50, id="int-too-large"),
        pytest.param(0.25, 0.25, 0.25, 0.5, id="float-too-large"),
        pytest.param(5, 20, 25, 10, id="int-too-small"),
        pytest.param(0.05, 0.2, 0.25, 0.1, id="float-too-small"),
    ],
)
def test_given_invalid_sum_raises(a, b, c, d):
    with pytest.raises(ValidationError):
        ValidProbConfig(a=a, b=b, c=c, d=d)
    with pytest.raises(ValidationError):
        ValidProbConfig.parse_raw(json.dumps({"a": a, "b": b, "c": c, "d": d}))


@pytest.mark.parametrize(
    "a, b, c, d",
    [
        pytest.param(25, 25, 25, -50, id="int-negative"),
        pytest.param(0.25, 0.25, 0.25, -0.5, id="float-negative"),
        pytest.param(5, 20, 25, 150, id="int-greater-100"),
        pytest.param(0.05, 0.2, 0.25, 150.10, id="float-greater-100"),
    ],
)
def test_given_invalid_val_range_raises(a, b, c, d):
    with pytest.raises(ValidationError):
        ValidProbConfig(a=a, b=b, c=c, d=d)
    with pytest.raises(ValidationError):
        ValidProbConfig.parse_raw(json.dumps({"a": a, "b": b, "c": c, "d": d}))


@pytest.mark.parametrize(
    "ConfigType, a, b, c, d",
    [
        pytest.param(
            InvalidProbConfigSimple,
            25,
            25,
            25,
            "25",
            id="simple-int-uniform-probabilities",
        ),
        pytest.param(
            InvalidProbConfigSimple,
            0.25,
            0.25,
            0.25,
            "0.25",
            id="simple-float-uniform-probabilities",
        ),
        pytest.param(
            InvalidProbConfigSimple,
            5,
            20,
            25,
            "50",
            id="simple-int-mixed-probabilities",
        ),
        pytest.param(
            InvalidProbConfigSimple,
            0.05,
            0.2,
            0.25,
            "0.5",
            id="simple-float-mixed-probabilities",
        ),
        pytest.param(
            InvalidProbConfigSimple,
            25.5,
            24.5,
            25,
            "25",
            id="simple-float-int-probabilities",
        ),
        pytest.param(
            InvalidProbConfigComplex,
            25,
            25,
            25,
            25,
            id="complex-int-uniform-probabilities",
        ),
        pytest.param(
            InvalidProbConfigComplex,
            0.25,
            0.25,
            0.25,
            0.25,
            id="complex-float-uniform-probabilities",
        ),
        pytest.param(
            InvalidProbConfigComplex,
            5,
            20,
            25,
            50,
            id="complex-int-mixed-probabilities",
        ),
        pytest.param(
            InvalidProbConfigComplex,
            0.05,
            0.2,
            0.25,
            0.5,
            id="complex-float-mixed-probabilities",
        ),
        pytest.param(
            InvalidProbConfigComplex,
            25.5,
            24.5,
            25,
            25,
            id="complex-float-int-probabilities",
        ),
    ],
)
def test_given_invalid_class_and_config_raises(ConfigType, a, b, c, d):
    with pytest.raises(ValidationError):
        ConfigType(a=a, b=b, c=c, d=d)
    with pytest.raises(ValidationError):
        ConfigType.parse_raw(json.dumps({"a": a, "b": b, "c": c, "d": d}))
