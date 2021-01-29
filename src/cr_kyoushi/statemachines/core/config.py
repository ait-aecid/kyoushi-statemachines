"""
This module contains configuration and context classes or elements,
which might be useful for many state machines.
"""

from typing import (
    Any,
    Dict,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
    root_validator,
    validator,
)

from cr_kyoushi.simulation.model import ApproximateFloat


ProbVal = Union[
    float, int
]  # float must be first or otherwise pydantic validation will do weird things
"""Type alias for probability values"""


class ProbabilisticStateConfig(BaseModel):
    """Base class for transition probabilities configuration.

    This base class already defines validators to check the
    correctness of probability values and distributions.
    """

    @validator("*")
    def check_value_range(cls, v: ProbVal) -> ProbVal:
        """Validates the value range for all probability fields.

        Args:
            v: A probability fields value

        Raises:
            ValueError: If the number range is invalid

        Returns:
            The validated field value
        """
        if v >= 0 and v <= 100:
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
        for key, val in values.items():
            field_type = cls.__fields__[key].type_
            if field_type not in [ProbVal, float, int]:
                raise ValueError(
                    (
                        "Probabilistic config fields must be int or float! "
                        f"Found {key}: {field_type}"
                    )
                )
        return values

    @root_validator
    def check_probabilities(cls, values: Dict[str, ProbVal]) -> Dict[str, ProbVal]:
        """Validates the sum of all probabilities results in a clean probability distribution.

        i.e., The sum of all probabilities is 100% (1.0 or 100)

        Args:
            values: Dictionary containing all fields

        Raises:
            ValueError: If the distribution does not sum to 100%

        Returns:
            The fields dictionary
        """
        prob_sum = sum(values.values(), 0.0)

        if prob_sum == 1.0 or prob_sum == 100:
            return values

        raise ValueError(
            (
                "Sum of all transition probabilities must be either 1.0 or 100, "
                f"but is {prob_sum}"
            )
        )


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
            min=80,  # 80 = 1m20s
            max=300,  # 5*60 = 5m
        ),
        description="The time in seconds to use for big idles",
    )
    small: Union[ApproximateFloat, float] = Field(
        ApproximateFloat(
            min=5,  # 5s
            max=60,  # 60s
        ),
        description="The time in seconds to use for big idles",
    )

    tiny: Union[ApproximateFloat, float] = Field(
        ApproximateFloat(
            min=0.5,  # 500ms
            max=1.5,  # 1s500ms
        ),
        description="The time in seconds to use for big idles",
    )
