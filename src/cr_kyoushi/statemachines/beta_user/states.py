from typing import Dict

from cr_kyoushi.simulation import states
from cr_kyoushi.simulation.transitions import Transition
from cr_kyoushi.simulation.util import now


class ActivitySelectionState(states.AdaptiveProbabilisticState):
    """The main activity selection state for the horde user.

    This will decide between either entering the horde activity or idling.
    """

    def __init__(
        self,
        name: str,
        horde: Transition,
        owncloud: Transition,
        ssh_user: Transition,
        web_browser: Transition,
        wp_editor: Transition,
        wpdiscuz: Transition,
        idle: Transition,
        horde_weight: float = 0.3,
        owncloud_weight: float = 0.15,
        ssh_user_weight: float = 0,
        web_browser_weight: float = 0.2,
        wp_editor_weight: float = 0,
        wpdiscuz_weight: float = 0.15,
        idle_weight: float = 0.2,
        horde_max_daily: int = 10,
        owncloud_max_daily: int = 10,
        ssh_user_max_daily: int = 10,
        web_browser_max_daily: int = 10,
        wp_editor_max_daily: int = 10,
        wpdiscuz_max_daily: int = 10,
    ):
        """
        Args:
            name: The states name
            horde: The transition to enter the horde activity
            horde_max_daily: The maximum amount of times to enter the horde activity per day.
            horde_weight: The propability of entering the horde activity.
            owncloud: The transition to enter the horde activity
            ssh_user: The transition to enter the horde activity
            web_browser: The transition to enter the horde activity
            wp_editor: The transition to enter the horde activity
            wpdiscuz: The transition to enter the horde activity
            idle: The idle transition
            owncloud_max_daily: The maximum amount of times to enter the owncloud activity per day.
            owncloud_weight: The propability of entering the owncloud activity.
            ssh_user_max_daily: The maximum amount of times to enter the ssh_user activity per day.
            ssh_user_weight: The propability of entering the ssh_user activity.
            web_browser_max_daily: The maximum amount of times to enter the web_browser activity per day.
            web_browser_weight: The propability of entering the web_browser activity.
            wp_editor_max_daily: The maximum amount of times to enter the wp_editor activity per day.
            wp_editor_weight: The propability of entering the wp_editor activity.
            wpdiscuz_max_daily: The maximum amount of times to enter the wpdiscuz activity per day.
            wpdiscuz_weight: The propability of entering the wpdiscuz activity.
            idle_weight: The propability of entering the idle activity.
        """
        super().__init__(
            name=name,
            transitions=[
                horde,
                owncloud,
                ssh_user,
                web_browser,
                wp_editor,
                wpdiscuz,
                idle,
            ],
            weights=[
                horde_weight,
                owncloud_weight,
                ssh_user_weight,
                web_browser_weight,
                wp_editor_weight,
                wpdiscuz_weight,
                idle_weight,
            ],
        )

        self._counts: Dict[Transition, int] = {
            horde: 0,
            owncloud: 0,
            ssh_user: 0,
            web_browser: 0,
            wp_editor: 0,
            wpdiscuz: 0,
        }

        self._max: Dict[Transition, int] = {
            horde: horde_max_daily,
            owncloud: owncloud_max_daily,
            ssh_user: ssh_user_max_daily,
            web_browser: web_browser_max_daily,
            wp_editor: wp_editor_max_daily,
            wpdiscuz: wpdiscuz_max_daily,
        }
        self.__day = now().date()

    def reset(self):
        super().reset()
        # reset daily transition counts to 0
        for key in self._counts.keys():
            self._counts[key] = 0

    def adapt_before(self, log, context):
        """Checks the current day and resets counters and modifiers on day changes"""
        super().adapt_before(log, context)

        # reset count and modifiers if we have a new day
        current_day = now().date()
        if self.__day != current_day:
            self.__day = current_day
            self.reset()

    def adapt_after(self, log, context, selected):
        """Increases the activity enter counters and disables activities"""
        super().adapt_after(log, context, selected)

        # increase horde count if we selected the transition
        if selected in self._max:
            self._counts[selected] += 1

            # if we reached the limit for a transition set its probability to 0
            if self._counts[selected] >= self._max[selected]:
                self._modifiers[selected] = 0
