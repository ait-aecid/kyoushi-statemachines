from typing import (
    List,
    Optional,
    Sequence,
)

from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation.model import Context
from cr_kyoushi.simulation.states import AdaptiveProbabilisticState
from cr_kyoushi.simulation.transitions import Transition


__all__ = ["ActivityState"]


class ActivityState(AdaptiveProbabilisticState):
    def __init__(
        self,
        name: str,
        transitions: List[Transition],
        ret_transition: Transition,
        weights: Sequence[float],
        modifiers: Optional[Sequence[float]] = None,
        ret_increase: float = 1.03125,
    ):
        super().__init__(
            name,
            transitions,
            weights,
            modifiers,
        )
        self.__ret_index: int = self.transitions.index(ret_transition)
        self.__ret: Transition = ret_transition
        self.__ret_increase: float = ret_increase

    def adapt_after(
        self,
        log: BoundLogger,
        context: Context,
        selected: Transition,
    ):
        # when we leave reset the modifiers
        if selected is self.__ret:
            self.reset()
        # if we do not leave the activity increase the ret modifier
        else:
            self._modifiers[self.__ret_index] *= self.__ret_increase
