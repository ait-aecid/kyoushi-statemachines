from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation import states
from cr_kyoushi.simulation.transitions import Transition
from cr_kyoushi.simulation.util import now

from .context import Context


class ActivitySelectionState(states.AdaptiveProbabilisticState):
    """The main activity selection state for the wordpress editor user.

    This will decide between either entering the wordpress editor activity or idling.
    """

    def __init__(
        self,
        name: str,
        wp_editor_transition: Transition,
        idle_transition: Transition,
        wp_editor_max_daily: int = 10,
        wp_editor_weight: float = 0.6,
        idle_weight: float = 0.4,
    ):
        """
        Args:
            name: The states name
            wp_editor_transition: The transition to enter the wordpress editor activity
            idle_transition: The idle transition
            wp_editor_max_daily: The maximum amount of times to enter the wordpress editor activity per day.
            wp_editor_weight: The propability of entering the wordpress editor activity.
            idle_weight: The propability of entering the idle activity.
        """
        super().__init__(
            name=name,
            transitions=[wp_editor_transition, idle_transition],
            weights=[wp_editor_weight, idle_weight],
        )
        self.__wp_editor = wp_editor_transition
        self.__wp_editor_count = 0
        self.__wp_editor_max = wp_editor_max_daily
        self.__day = now().date()

    def adapt_before(self, log: BoundLogger, context: Context):
        """Sets the propability of entering the wordpress editor activity to 0 if the daylie maximum is reached"""
        super().adapt_before(log, context)

        # reset wp_editor count and modifiers if we have a new day
        current_day = now().date()
        if self.__day != current_day:
            self.__day = current_day
            self.__wp_editor_count = 0
            self.reset()

        # if we reached the wp_editor limit set the transition probability to 0
        if self.__wp_editor_count >= self.__wp_editor_max:
            self._modifiers[self.__wp_editor] = 0

    def adapt_after(self, log, context, selected):
        """Increases the wordpress editor activity enter count"""
        super().adapt_after(log, context, selected)

        # increase wp_editor count if we selected the transition
        if selected == self.__wp_editor:
            self.__wp_editor_count += 1
