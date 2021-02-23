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
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name,
            transitions,
            weights,
            modifiers,
            name_prefix=name_prefix,
        )
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
            self._modifiers[self.__ret] *= self.__ret_increase
