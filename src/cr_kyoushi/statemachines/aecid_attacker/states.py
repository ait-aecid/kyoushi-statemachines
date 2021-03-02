import random

from typing import (
    List,
    Optional,
    Union,
)

from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation.model import ApproximateFloat
from cr_kyoushi.simulation.states import State
from cr_kyoushi.simulation.transitions import (
    DelayedTransition,
    Transition,
    TransitionFunction,
)


class AttackStepTransition:
    def __init__(
        self,
        transition: Transition,
        children: List["AttackStepTransition"] = [],
    ):
        self.transition: Transition = transition
        self.children: List["AttackStepTransition"] = children

    @property
    def transitions(self) -> List[Transition]:
        return [self.transition] + [child.transitions for child in self.children]


class AttackStep:
    def __init__(
        self,
        action: TransitionFunction,
        name: Optional[str] = None,
        children: List["AttackStep"] = [],
        delay_before: Union[ApproximateFloat, float] = 0.0,
        delay_after: Union[ApproximateFloat, float] = 0.0,
    ):
        self._action: TransitionFunction = action
        self._name: Optional[str] = name
        self.children: List["AttackStep"] = children
        self._delay_before: Union[ApproximateFloat, float] = delay_before
        self._delay_after: Union[ApproximateFloat, float] = delay_after

    def transition(
        self,
        target: str,
        name_prefix: Optional[str] = None,
    ) -> DelayedTransition:
        return DelayedTransition(
            transition_function=self._action,
            name=self._name,
            target=target,
            delay_before=self._delay_before,
            delay_after=self._delay_after,
            name_prefix=name_prefix,
        )

    def convert(
        self, target: str, name_prefix: Optional[str] = None
    ) -> AttackStepTransition:
        return AttackStepTransition(
            transition=self.transition(target, name_prefix),
            children=[child.transition(target, name_prefix) for child in self.children],
        )


class AttackPhaseState(State):
    def __init__(
        self,
        name: str,
        steps: List[AttackStep],
        next_phase: Optional[Transition] = None,
        name_prefix: Optional[str] = None,
    ):
        self._next_phase: Optional[Transition] = next_phase
        # convert attack steps in attack step transitions
        self.steps: List[AttackStepTransition] = [
            step.convert(name, name_prefix) for step in steps
        ]

        # combine all steps and their children into on big
        # transition list
        transitions: List[Transition] = (
            [] if self._next_phase is None else [self._next_phase]
        )
        for step in self.steps:
            transitions.extend(step.transitions)

        super().__init__(name, transitions=transitions, name_prefix=name_prefix)

    def next(self, log: BoundLogger, context) -> Optional[Transition]:
        if len(self.steps) > 0:
            # choose a random step to execute
            step: AttackStepTransition = random.choice(self.steps)

            # add potential step children to available steps list
            self.steps.extend(step.children)
            # remove selected step from available steps
            self.steps.remove(step)
            return step
        else:
            # if we have no steps in this phase left
            # then execute the transition leading to the next phase
            return self._next_phase
