from .db import t


class Cancelled(Exception):
    """The user pressed the cancel button."""


class UserError(Exception):
    """A failure with a ready-made, translatable message for the user."""

    def __init__(self, key, /, **params):
        super().__init__(key)
        self.key = key
        self.params = params

    def text(self, uid):
        return t(uid, self.key, **self.params)
