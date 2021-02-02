from pydantic import BaseModel


class BaseInfo(BaseModel):
    """Base class for context info models"""

    def clear(self):
        """Resets the info object to its initial state.

        i.e., all fields are `None`
        """
        for field in self.__fields__:
            self.__setattr__(field, None)
