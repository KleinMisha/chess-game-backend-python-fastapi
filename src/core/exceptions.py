"""Custom exception hierarchy"""


class BaseError(Exception):
    """Custom root exception."""


# --- Domain (Game logic) ---
class GameError(BaseError):
    """Invalid game logic."""


class InvalidFENError(GameError): ...


class IllegalMoveError(GameError): ...


class GameStateError(GameError): ...


class NotYourTurnError(GameError): ...


class GameCreationError(GameError): ...


# -- Application (app orchestration, repository, request validation, ...)
class AppError(BaseError):
    """Application failed to orchestrate communication between Game, repository and API."""


class InvalidRequestError(AppError): ...


class GameNotFoundError(AppError): ...


class NameNotUniqueError(AppError): ...
