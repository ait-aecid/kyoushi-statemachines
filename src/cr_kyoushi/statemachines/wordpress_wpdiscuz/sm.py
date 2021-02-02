"""Statemachine that only idles or executes the wordpress wpDiscuz activity."""

from datetime import datetime
from typing import (
    List,
    Optional,
)

from faker import Faker

from cr_kyoushi.simulation import sm
from cr_kyoushi.simulation.config import get_seed
from cr_kyoushi.simulation.model import WorkSchedule
from cr_kyoushi.simulation.states import State

from ..core.selenium import (
    SeleniumConfig,
    get_webdriver,
    install_webdriver,
)
from .config import StatemachineConfig
from .context import Context


__all__ = ["Statemachine", "StatemachineFactory"]


class Statemachine(sm.WorkHoursStatemachine):
    """Wordpress wpDiscuz activity state machine"""

    _selenium_config: SeleniumConfig
    _webdriver_path: Optional[str]

    def __init__(
        self,
        initial_state: str,
        states: List[State],
        selenium_config: SeleniumConfig,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        work_schedule: Optional[WorkSchedule] = None,
        max_errors: int = 0,
    ):
        super().__init__(
            initial_state,
            states,
            start_time=start_time,
            end_time=end_time,
            work_schedule=work_schedule,
            max_errors=max_errors,
        )
        self._selenium_config = selenium_config
        self._webdriver_path = None
        self.context: Optional[Context] = None
        # seed faker random with global seed
        Faker.seed(get_seed())
        self.fake: Faker = Faker()

    def setup_context(self):
        # we assume we only install once at the start of the sm
        if self._webdriver_path is None:
            self._webdriver_path = install_webdriver(self._selenium_config)

        driver = get_webdriver(
            self._selenium_config,
            self._webdriver_path,
        )

        self.context = Context(
            driver=driver,
            main_window=driver.current_window_handle,
            fake=self.fake,
        )

    def destroy_context(self):
        if self.context is not None:
            self.context.driver.quit()

    def _resume_work(self):
        self.current_state = self.initial_state
        # reset context
        self.destroy_context()
        self.setup_context()


class StatemachineFactory(sm.StatemachineFactory):
    """Wordpress wpDiscuz activity state machine factory"""

    @property
    def name(self) -> str:
        return "WordpressWpDiscuzStatemachineFactory"

    @property
    def config_class(self):
        return StatemachineConfig

    def build(self, config: StatemachineConfig):

        return Statemachine(
            initial_state="selecting_activity",
            states=[
                # ToDo
            ],
            selenium_config=config.selenium,
            start_time=config.start_time,
            end_time=config.end_time,
            work_schedule=config.schedule,
            max_errors=config.max_errors,
        )
