from typing import Callable

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.v1 import games, health
from src.core.exceptions import (
    AppError,
    BaseError,
    GameError,
    GameNotFoundError,
    GameStateError,
    NotYourTurnError,
)
from src.db.database import Base, engine

# todo move this into configuration file / environment file (create pydantic settings. )
PROJECT_NAME = "Chess FastAPI."
VERSION = "v1"
API_PREFIX = f"/api/{VERSION}"


def create_exception_handler(
    status_code: int, default_message: str
) -> Callable[[Request, Exception], JSONResponse]:
    """Create a function to use FastAPI's builtin mechanism for adding exception handlers (no need to write a custom decorator or anything.)"""

    def exception_handler(_: Request, exc: Exception) -> JSONResponse:
        message = str(exc) if str(exc) else default_message
        return JSONResponse(
            status_code=status_code,
            content={
                "error": type(exc).__name__,
                "detail": message,
            },
        )

    return exception_handler


def main():

    # ensure all tables are created
    Base.metadata.create_all(bind=engine)

    # Create the application
    app = FastAPI(
        title=PROJECT_NAME,
        version=VERSION,
    )

    # Register routers
    app.include_router(games.router, prefix=API_PREFIX)
    app.include_router(health.router, prefix=API_PREFIX)

    # Register exception handlers using custom exception hierarchy.
    app.add_exception_handler(
        BaseError, handler=create_exception_handler(400, "Caught an error.")
    )
    app.add_exception_handler(
        GameError, handler=create_exception_handler(400, "Invalid game logic.")
    )
    app.add_exception_handler(
        GameStateError,
        handler=create_exception_handler(409, "Cannot perform requested operation."),
    )
    app.add_exception_handler(
        NotYourTurnError,
        handler=create_exception_handler(409, "Please await your turn."),
    )
    app.add_exception_handler(
        AppError, handler=create_exception_handler(400, "Orchestration error.")
    )
    app.add_exception_handler(
        GameNotFoundError, handler=create_exception_handler(404, "Game not found.")
    )

    # Use uvicorn to run the application
    # todo move to docker file (as learning experience)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
