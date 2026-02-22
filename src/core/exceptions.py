"""Custom exception hierarchy"""

from fastapi import Request
from fastapi.responses import JSONResponse


class BaseError(Exception):
    """Custom root exception."""


# --- Domain (Game logic) ---
class GameError(BaseError): ...


class InvalidFENError(GameError): ...


class IllegalMoveError(GameError): ...


class GameStateError(GameError): ...


class NotYourTurnError(GameError): ...


class GameCreationError(GameError): ...


# -- Application (app orchestration, repository, request validation, ...)
class AppError(BaseError): ...


class InvalidRequestError(AppError): ...


class GameNotFoundError(AppError): ...


# --- EXCEPTION HANDLER (FastAPI) ---
HTTP_STATUS_CODES: dict[type[BaseError], int] = {
    InvalidFENError: 400,
    IllegalMoveError: 400,
    GameStateError: 409,
    NotYourTurnError: 409,
    GameCreationError: 400,
    InvalidRequestError: 400,
    GameNotFoundError: 404,
}


def exception_handler(_: Request, exception: BaseError) -> JSONResponse:
    """FastAPI's mechanism for handling exceptions. Will attach to FastAPI instance in main.py entry point."""
    status_code = next(
        (
            code
            for exc_type, code in HTTP_STATUS_CODES.items()
            if isinstance(exception, exc_type)
        ),
        400,  # default value
    )
    return JSONResponse(
        status_code=status_code,
        content={"error": type(exception).__name__, "message": str(exception)},
    )
