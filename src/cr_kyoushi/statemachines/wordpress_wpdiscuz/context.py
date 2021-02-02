"""The wordpress wpdiscuz activities context model classes"""

from faker import Faker
from pydantic import (
    BaseModel,
    Field,
)
from selenium import webdriver


class Context(BaseModel):
    """Wordpress wpDisuz state machine context class"""

    driver: webdriver.Remote
    """The selenium web driver"""

    main_window: str = Field(
        ...,
        description="The main window of the webdriver",
    )

    fake: Faker
    """Faker instance to use for generating various random content"""

    class Config:
        arbitrary_types_allowed = True
