"""
This module contains configuration and context classes or elements,
which might be useful for many state machines.
"""

import sys

from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Dict,
    Optional,
    Union,
)

from faker import Faker
from pydantic import (
    BaseModel,
    Field,
    root_validator,
    validator,
)

from cr_kyoushi.simulation.model import (
    ApproximateFloat,
    WorkSchedule,
)

from ..core.util import (
    check_probabilities,
    greater_equal_one,
)


if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class ActivityExtraConfig(BaseModel):
    """Base class for extra configuration fields for activity configs."""

    return_increase: float = Field(
        1.25,
        description=(
            "The multiplicative factor the return transitions weight "
            "should be increased each time it is not selected."
        ),
    )

    _validate_increase = validator("return_increase", allow_reuse=True)(
        greater_equal_one
    )


class ProbabilisticStateConfig(BaseModel):
    """Base class for transition probabilities configuration.

    This base class already defines validators to check the
    correctness of probability values and distributions.
    """

    @validator("*")
    def check_value_range(cls, v: float) -> float:
        """Validates the value range for all probability fields.

        Args:
            v: A probability fields value

        Raises:
            ValueError: If the number range is invalid

        Returns:
            The validated field value
        """
        if not (isinstance(v, int) or isinstance(v, float)) or (v >= 0 and v <= 100):
            return v
        raise ValueError("Probability value must be between 0.0 and 1.0 or 0 and 100!")

    @root_validator(pre=True)
    def check_all_field_types(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Verifies that all config fields are probability value fields.

        !!! Note
            This is only checked once the sub class is actually used to load
            a configuration.

        Args:
            values: Dictionary containing all fields

        Raises:
            ValueError: If a invalid field value type is detected

        Returns:
            The fields dictionary
        """
        for key, val in cls.__fields__.items():
            if key != "extra":
                field_type = val.type_
                if not issubclass(field_type, float):
                    raise ValueError(
                        (
                            "Probabilistic config fields must be float! "
                            f"Found {key}: {field_type}"
                        )
                    )
        return values

    @root_validator
    def check_probabilities(cls, values: Dict[str, float]) -> Dict[str, float]:
        """Validates the sum of all probabilities results in a clean probability distribution.

        i.e., The sum of all probabilities is 100% (i.e., 1.0)

        Args:
            values: Dictionary containing all fields

        Raises:
            ValueError: If the distribution does not sum to 1

        Returns:
            The fields dictionary
        """
        prob_fields = {key: val for key, val in values.items() if key != "extra"}
        check_probabilities(prob_fields)
        return values


class Idle(str, Enum):
    BIG = "big"
    MEDIUM = "medium"
    SMALL = "small"
    TINY = "tiny"

    @classmethod
    def lookup(cls):
        return {v: k for v, k in cls.__members__.items()}

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, val: Union[str, "Idle"]) -> "Idle":
        """Parses and validates `Idle` input in either `str`, `Enum` encoding.

        Args:
            val: The encoded input Idle

        Raises:
            ValueError: if the given input is not a valid Idle

        Returns:
            Idle enum
        """
        # check enum input
        if isinstance(val, Idle):
            return val

        # check str LogLevel input
        try:
            return cls.lookup()[val.upper()]
        except KeyError as key_error:
            raise ValueError("invalid string Idle") from key_error


class IdleConfig(BaseModel):
    big: Union[ApproximateFloat, float] = Field(
        ApproximateFloat(
            min=600,  # 10*60 = 10m
            max=3000,  # 50*60 = 50m
        ),
        description="The time in seconds to use for big idles",
    )

    medium: Union[ApproximateFloat, float] = Field(
        ApproximateFloat(
            min=60,  # 1m
            max=300,  # 5*60 = 5m
        ),
        description="The time in seconds to use for medium idles",
    )
    small: Union[ApproximateFloat, float] = Field(
        ApproximateFloat(
            min=5,  # 5s
            max=30,  # 30s
        ),
        description="The time in seconds to use for short idles",
    )

    tiny: Union[ApproximateFloat, float] = Field(
        ApproximateFloat(
            min=0.5,  # 500ms
            max=1.5,  # 1s500ms
        ),
        description="The time in seconds to use for very short idles",
    )

    def get(self, idle: Idle) -> Union[ApproximateFloat, float]:
        """Retrieves the idle config for the given Idle type

        Args:
            idle: The idle type to retrieve

        Returns:
            Idle value
        """
        return self.__getattribute__(idle.value)


class BasicStatemachineConfig(BaseModel):
    """Basic state machine configuration model

    Example:
        ```yaml
        max_errors: 0
        start_time: 2021-01-23T9:00
        end_time: 2021-01-29T00:01
        schedule:
        work_days:
            monday:
                start_time: 09:00
                end_time: 17:30
            friday:
                start_time: 11:21
                end_time: 19:43
        ```
    """

    max_errors: int = Field(
        0,
        description="The maximum amount of times to try to recover from an error",
    )

    start_time: Optional[datetime] = Field(
        None,
        description="The state machines start time",
    )

    end_time: Optional[datetime] = Field(
        None,
        description="The state machines end time",
    )

    idle: IdleConfig = Field(
        IdleConfig(),
        description="The idle configuration for the state machine",
    )

    schedule: Optional[WorkSchedule] = Field(
        None,
        description="The work schedule for the web browser user",
    )


class FakerContext(Protocol):
    """Context model for state machines using faker"""

    fake: Faker
    """Faker instance to use for generating various random content"""


class FakerContextModel(BaseModel):
    """Context model for faker state machines"""

    fake: Faker
    """Faker instance to use for generating various random content"""

    class Config:
        arbitrary_types_allowed = True
