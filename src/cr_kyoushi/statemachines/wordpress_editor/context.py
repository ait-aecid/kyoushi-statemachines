"""The wordpress wordpress editor activities context model classes"""


from faker import Faker
from pydantic import (
    BaseModel,
    Field,
)
from selenium import webdriver


class WordpressEditorContext(BaseModel):
    author: str = Field(
        "Max Mustermann",
        description="The editors name",
    )

    username: str = Field(
        "mmustermann",
        description="The editors username",
    )

    password: str = Field(
        "passwd123",
        description="The editors password",
    )


class Context(BaseModel):
    """Wordpress wordpress editor state machine context class"""

    driver: webdriver.Remote
    """The selenium web driver"""

    main_window: str = Field(
        ...,
        description="The main window of the webdriver",
    )

    fake: Faker
    """Faker instance to use for generating various random content"""

    wp_editor: WordpressEditorContext = Field(
        WordpressEditorContext(),
        description="The wordpress editor activity context",
    )

    class Config:
        arbitrary_types_allowed = True
