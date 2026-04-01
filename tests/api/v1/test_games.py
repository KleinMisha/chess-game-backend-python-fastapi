"""Unit tests for src/api/v1/games.py"""

from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.v1.games import get_chess_service
from src.core.exceptions import (
    GameCreationError,
    GameNotFoundError,
    GameStateError,
    IllegalMoveError,
    NotYourTurnError,
)
from src.core.shared_types import Color, Status
from src.main import app
from src.services.chess_service import (
    GameResponse,
    LegalMovesResponse,
)

client = TestClient(app)


MOCK_FEN_STATE = "8/8/8/8/8/8/8/8 w KQq - 8 24"
MOCK_ID = uuid4()
URL_PREFIX = "api/v1"


def create_mock_game_response() -> GameResponse:
    return GameResponse(
        game_id=MOCK_ID,
        players={"white": "player_white", "black": "player_black"},
        fen_state=MOCK_FEN_STATE,
        starting_state=MOCK_FEN_STATE,
        move_history=[],
        status=Status.IN_PROGRESS,
        winner=None,
    )


def create_mock_legal_moves_response() -> LegalMovesResponse:
    return LegalMovesResponse(
        game_id=MOCK_ID,
        player_name="Mocker McMocker",
        color=Color.WHITE,
        legal_moves=["a1a2", "a2a3"],
    )


# --- POST /games ---
def test_create_game() -> None:

    mock_service = Mock()
    mock_service.create_new_game.return_value = create_mock_game_response()
    app.dependency_overrides[get_chess_service] = lambda: mock_service

    response = client.post(
        f"{URL_PREFIX}/games",
        json={
            "player_name": "Mocker M. Mockerson",
            "color": "white",
            "starting_fen": MOCK_FEN_STATE,
        },
    )

    # successful
    assert response.status_code == 200

    # contract: At least should return a game ID
    data = response.json()
    assert "game_id" in data

    # response model should be a GameResponse
    GameResponse.model_validate(data)


def test_create_game_without_starting_fen() -> None:
    """starting FEN should be optional."""
    mock_service = Mock()
    mock_service.create_new_game.return_value = create_mock_game_response()
    app.dependency_overrides[get_chess_service] = lambda: mock_service

    response = client.post(
        f"{URL_PREFIX}/games",
        json={
            "player_name": "Mocker M. Mockerson",
            "color": "white",
        },
    )

    # successful
    assert response.status_code == 200

    # contract: At least should return a game ID
    data = response.json()
    assert "game_id" in data

    # response model should be a GameResponse
    GameResponse.model_validate(data)


def test_create_game_raises_game_creation_error() -> None:
    """Endpoint might raise a GameCreationError"""
    mock_service = Mock()
    mock_service.create_new_game.side_effect = GameCreationError("Cannot create game.")
    app.dependency_overrides[get_chess_service] = lambda: mock_service

    response = client.post(
        f"{URL_PREFIX}/games",
        json={
            "player_name": "Mocker M. Mockerson",
            "color": "white",
            "starting_fen": MOCK_FEN_STATE,
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "GameCreationError"
    assert data["detail"] == "Cannot create game."


def test_invalid_create_game_request() -> None:
    """Endpoint might raise InvalidRequestError when a structurally invalid FEN string is supplied."""
    mock_service = Mock()
    mock_service.create_new_game.return_value = create_mock_game_response()
    app.dependency_overrides[get_chess_service] = lambda: mock_service

    response = client.post(
        f"{URL_PREFIX}/games",
        json={
            "player_name": "Mocker M. Mockerson",
            "color": "white",
            "starting_fen": "invalid FEN string.",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "InvalidRequestError"


# --- POST /games/{game_id}/players ---
def test_join_game() -> None:
    mock_service = Mock()
    mock_service.join_game.return_value = create_mock_game_response()
    app.dependency_overrides[get_chess_service] = lambda: mock_service

    response = client.post(
        f"{URL_PREFIX}/games/{MOCK_ID}/players", json={"player_name": "second player"}
    )

    assert response.status_code == 200
    data = response.json()
    GameResponse.model_validate(data)


# --- GET /games/{game_id} ---
def test_get_game_state() -> None:
    mock_service = Mock()
    mock_service.get_game_state.return_value = create_mock_game_response()
    app.dependency_overrides[get_chess_service] = lambda: mock_service
    response = client.get(f"{URL_PREFIX}/games/{MOCK_ID}")
    assert response.status_code == 200
    data = response.json()
    assert "fen_state" in data
    GameResponse.model_validate(data)


# --- GET /games/{game_id}/legal-moves ---
def test_get_legal_moves() -> None:
    mock_service = Mock()
    mock_service.legal_moves.return_value = create_mock_legal_moves_response()
    app.dependency_overrides[get_chess_service] = lambda: mock_service
    response = client.get(
        f"{URL_PREFIX}/games/{MOCK_ID}/legal-moves",
        params={"player_name": "Mock McFakeName"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "legal_moves" in data
    LegalMovesResponse.model_validate(data)


# --- POST /games/{game_id}/moves ---
def test_make_move() -> None:
    mock_service = Mock()
    mock_service.make_move.return_value = create_mock_game_response()
    app.dependency_overrides[get_chess_service] = lambda: mock_service
    response = client.post(
        f"{URL_PREFIX}/games/{MOCK_ID}/moves",
        json={"player_name": "player", "from_square": "a1", "to_square": "a2"},
    )
    assert response.status_code == 200
    data = response.json()
    GameResponse.model_validate(data)


def test_make_move_raises_illegal_move_error() -> None:
    """
    When you attempt to make a move that is against the rules.

    status code: 400 (inherited from GameError)
    """
    mock_service = Mock()
    mock_service.make_move.side_effect = IllegalMoveError("Move not allowed.")
    app.dependency_overrides[get_chess_service] = lambda: mock_service
    response = client.post(
        f"{URL_PREFIX}/games/{MOCK_ID}/moves",
        json={"player_name": "player", "from_square": "a1", "to_square": "a2"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "IllegalMoveError"


# --- DELETE /games/{game_id} ---
def test_delete_game() -> None:
    mock_service = Mock()
    mock_service.delete_game.return_value = None
    app.dependency_overrides[get_chess_service] = lambda: mock_service
    response = client.delete(f"{URL_PREFIX}/games/{MOCK_ID}")
    assert response.status_code == 200


# --- EXCEPTION HANDLING (Multiple endpoints that can result in the same exception) ---
@pytest.mark.parametrize(
    "http_method,endpoint, payload, service_method",
    [
        ("get", f"{URL_PREFIX}/games/{MOCK_ID}", None, "get_game_state"),
        (
            "post",
            f"{URL_PREFIX}/games/{MOCK_ID}/players",
            {"player_name": "player"},
            "join_game",
        ),
        (
            "get",
            f"{URL_PREFIX}/games/{MOCK_ID}/legal-moves",
            {"player_name": "player"},
            "legal_moves",
        ),
        (
            "post",
            f"{URL_PREFIX}/games/{MOCK_ID}/moves",
            {"player_name": "player", "from_square": "a1", "to_square": "a2"},
            "make_move",
        ),
    ],
)
def test_game_not_found_error(
    http_method: str,
    endpoint: str,
    payload: dict[str, str] | None,
    service_method: str,
) -> None:
    """
    When a game under the given ID is not found in the repository.

    status code: 404
    """
    mock_service = Mock()
    getattr(mock_service, service_method).side_effect = GameNotFoundError(
        "unknown game ID."
    )
    app.dependency_overrides[get_chess_service] = lambda: mock_service

    client_method = getattr(client, http_method)
    if payload:
        response = (
            client_method(endpoint, json=payload)
            if http_method != "get"
            else client_method(endpoint, params=payload)
        )
    else:
        response = client_method(endpoint)

    assert response.status_code == 404
    assert response.json()["error"] == "GameNotFoundError"


@pytest.mark.parametrize(
    "http_method,endpoint, payload, service_method",
    [
        (
            "post",
            f"{URL_PREFIX}/games/{MOCK_ID}/players",
            {"player_name": "player"},
            "join_game",
        ),
        (
            "get",
            f"{URL_PREFIX}/games/{MOCK_ID}/legal-moves",
            {"player_name": "player"},
            "legal_moves",
        ),
        (
            "post",
            f"{URL_PREFIX}/games/{MOCK_ID}/moves",
            {"player_name": "player", "from_square": "a1", "to_square": "a2"},
            "make_move",
        ),
    ],
)
def test_game_state_error(
    http_method: str,
    endpoint: str,
    payload: dict[str, str] | None,
    service_method: str,
) -> None:
    """
    When an action is not possible given the current status of the game.

    status code: 409
    """
    mock_service = Mock()
    getattr(mock_service, service_method).side_effect = GameStateError(
        "Cannot perform operation during this stage of the game."
    )
    app.dependency_overrides[get_chess_service] = lambda: mock_service

    client_method = getattr(client, http_method)
    if payload:
        response = (
            client_method(endpoint, json=payload)
            if http_method != "get"
            else client_method(endpoint, params=payload)
        )
    else:
        response = client_method(endpoint)

    assert response.status_code == 409
    assert response.json()["error"] == "GameStateError"


@pytest.mark.parametrize(
    "http_method,endpoint, payload, service_method",
    [
        (
            "get",
            f"{URL_PREFIX}/games/{MOCK_ID}/legal-moves",
            {"player_name": "player"},
            "legal_moves",
        ),
        (
            "post",
            f"{URL_PREFIX}/games/{MOCK_ID}/moves",
            {"player_name": "player", "from_square": "a1", "to_square": "a2"},
            "make_move",
        ),
    ],
)
def test_not_your_turn_error(
    http_method: str,
    endpoint: str,
    payload: dict[str, str] | None,
    service_method: str,
) -> None:
    """
    When you are trying to check your legal moves / make a move during your opponent's turn.

    status code: 409
    """
    mock_service = Mock()
    getattr(mock_service, service_method).side_effect = NotYourTurnError(
        "Wait for opponent to make a move first."
    )
    app.dependency_overrides[get_chess_service] = lambda: mock_service

    client_method = getattr(client, http_method)
    if payload:
        response = (
            client_method(endpoint, json=payload)
            if http_method != "get"
            else client_method(endpoint, params=payload)
        )
    else:
        response = client_method(endpoint)

    assert response.status_code == 409
    assert response.json()["error"] == "NotYourTurnError"
