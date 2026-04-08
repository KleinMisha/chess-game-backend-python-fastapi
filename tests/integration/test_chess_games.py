"""Integration tests: Chess games"""

from typing import Any, Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.v1.games import get_chess_service
from src.core.config import config
from src.db.sql_repository import SQLGameRepository
from src.main import app
from src.services.chess_service import ChessService


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Setup FastAPI testclient with dependencies overwritten to use test-setup"""

    # override for app's dependency on the service
    def _override_get_chess_service() -> ChessService:
        """Do not mock the repository, but use a test db (in-memory)."""
        repository = SQLGameRepository(db_session)
        return ChessService(repository)

    app.dependency_overrides[get_chess_service] = _override_get_chess_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


CANONICAL_STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
MOCK_ID = uuid4()


# --- HAPPY PATHS INTEGRATION TESTS ---
@pytest.mark.parametrize(
    "starting_fen, game_name",
    [
        (f, n)
        for f, n in zip(
            [None, "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1"],
            [None, f"test-game-{uuid4()}"],
        )
    ],
)
def test_create_and_retrieve_game(
    starting_fen: str | None, game_name: str | None, client: TestClient
) -> None:
    """
    Create a new  (un)named game with(out) a custom starting FEN, then perform GET request to retrieve that data.
    """
    #  Create a new game via POST /games.
    response = client.post(
        f"{config.api_prefix}/games",
        json={
            "player_name": "FirstPlayer",
            "color": "white",
            "starting_fen": starting_fen,
            "game_name": game_name,
        },
    )
    data = response.json()
    game_id = data["game_id"]

    assert response.status_code == 200

    #  Retrieve the game via GET /games/{game_id}.
    response = client.get(f"{config.api_prefix}/games/{game_id}")
    retrieved_game_data = response.json()
    assert response.status_code == 200
    assert retrieved_game_data["game_id"] == game_id
    assert retrieved_game_data["players"] == {"white": "FirstPlayer"}
    assert (
        retrieved_game_data["fen_state"] == starting_fen
        if starting_fen is not None
        else CANONICAL_STARTING_FEN
    )
    assert retrieved_game_data["game_name"] == game_name


def test_get_all_games(client: TestClient) -> None:
    """
    Test the GET /games endpoint
    ----
    Create a couple (un)named games with(out) a custom starting FEN, then retrieve the entire list.
    """

    # Create the games:
    starting_fens: list[str | None] = [
        None,
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1",
    ]
    game_names: list[str | None] = [None, "named-game"]

    for fen, name in zip(starting_fens, game_names):
        client.post(
            f"{config.api_prefix}/games",
            json={
                "player_name": "FirstPlayer",
                "color": "white",
                "starting_fen": fen,
                "game_name": name,
            },
        )

    # GET request
    response = client.get(f"{config.api_prefix}/games")
    assert response.status_code == 200
    data: list[Any] = response.json()
    assert isinstance(data, list)


def test_join_game(client: TestClient) -> None:
    """
    1. Create a new game via POST /games.
    2. Second player joins the game via POST /games/{game_id}/players

    Assert...
    I. Status codes are 200
    II. both players are joined to the game with the expected colors
    """
    #  Create a new game via POST /games.
    response = client.post(
        f"{config.api_prefix}/games",
        json={
            "player_name": "FirstPlayer",
            "color": "white",
        },
    )
    assert response.status_code == 200

    data = response.json()
    game_id = data["game_id"]

    # Second player joins the game via POST /games/{game_id}/players
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/players",
        json={"player_name": "SecondPlayer"},
    )
    assert response.status_code == 200

    #  Retrieve the game via GET /games/{game_id}.
    response = client.get(f"{config.api_prefix}/games/{game_id}")
    retrieved_game_data = response.json()
    assert response.status_code == 200
    assert retrieved_game_data["game_id"] == game_id
    assert retrieved_game_data["players"] == {
        "white": "FirstPlayer",
        "black": "SecondPlayer",
    }


def test_get_legal_moves(client: TestClient) -> None:
    """
    1. Create a new game via POST /games.
    2. POST /games/{game_id}/players
    3. Call GET /games/{game_id}/legal-moves (for the current player)

    Assertions:
    -----
    I. Status codes are 200
    II. Returned set of legal moves is as expected
    """
    #  Create a new game via POST /games.
    response = client.post(
        f"{config.api_prefix}/games",
        json={
            "player_name": "FirstPlayer",
            "color": "white",
        },
    )
    assert response.status_code == 200

    data = response.json()
    game_id = data["game_id"]

    # Second player joins the game via POST /games/{game_id}/players
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/players",
        json={"player_name": "SecondPlayer"},
    )
    assert response.status_code == 200

    # Player with the white pieces (FirstPlayer) will ask for their legal moves
    # NOTE board is in canonical starting position: 2x 8 pawn moves + 4 knight moves possible = 20 possible moves.

    expected_moves = [
        f"{file}2{file}{rank}" for file in "abcdefgh" for rank in (3, 4)
    ] + ["g1f3", "g1h3", "b1a3", "b1c3"]

    #  GET /games/{game_id}/legal-moves
    response = client.get(
        f"{config.api_prefix}/games/{game_id}/legal-moves",
        params={"player_name": "FirstPlayer"},
    )
    data = response.json()
    assert response.status_code == 200
    assert data["game_id"] == game_id
    assert data["player_name"] == "FirstPlayer"
    assert data["color"] == "white"
    assert set(data["legal_moves"]) == set(expected_moves)


def test_make_legal_move(client: TestClient) -> None:
    """
    1. Create a new game via POST /games.
    2. POST /games/{game_id}/players
    3. Perform a sequence of legal moves via POST /games/{game_id}/moves.


    Assertions
    ----
    I. Status codes are 200
    II. Move history contains moves as expected
    III. FEN state reflects latest game state correctly
    IV. Player turn alternates correctly

    """
    #  Create a new game via POST /games.
    response = client.post(
        f"{config.api_prefix}/games",
        json={
            "player_name": "FirstPlayer",
            "color": "white",
        },
    )
    assert response.status_code == 200

    data = response.json()
    game_id = data["game_id"]

    # Second player joins the game via POST /games/{game_id}/players
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/players",
        json={"player_name": "SecondPlayer"},
    )
    assert response.status_code == 200

    # Perform a sequence of legal moves via POST /games/{game_id}/moves
    moves = [("e2", "e4"), ("e7", "e5"), ("g1", "f3"), ("b8", "c6")]
    for idx, move in enumerate(moves):
        sq_from, sq_to = move
        payload = {
            "player_name": "FirstPlayer" if (idx + 1) % 2 != 0 else "SecondPlayer",
            "from_square": sq_from,
            "to_square": sq_to,
        }
        response = client.post(
            f"{config.api_prefix}/games/{game_id}/moves", json=payload
        )
        assert response.status_code == 200

    #  Retrieve the game via GET /games/{game_id}.
    response = client.get(f"{config.api_prefix}/games/{game_id}")
    retrieved_game_data = response.json()
    assert response.status_code == 200
    assert retrieved_game_data["game_id"] == game_id
    assert retrieved_game_data["players"] == {
        "white": "FirstPlayer",
        "black": "SecondPlayer",
    }
    assert (
        retrieved_game_data["fen_state"]
        == "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
    )
    assert retrieved_game_data["starting_state"] == CANONICAL_STARTING_FEN
    assert retrieved_game_data["move_history"] == [
        f"{sq_from}{sq_to}" for (sq_from, sq_to) in moves
    ]
    assert retrieved_game_data["winner"] is None


def test_delete_game(client: TestClient) -> None:
    """
    1. Create a new game via POST /games.
    3. Delete it from database via DELETE /games/{game_id}

    Assertions
    -------
    I. DELETE request has status code 200
    II. Subsequent GET /games/{game_id} will fail with status code 404 (GameNotFoundError).
    """
    #  Create a new game via POST /games.
    response = client.post(
        f"{config.api_prefix}/games",
        json={
            "player_name": "FirstPlayer",
            "color": "white",
        },
    )
    assert response.status_code == 200

    data = response.json()
    game_id = data["game_id"]

    # DELETE request
    response = client.delete(f"{config.api_prefix}/games/{game_id}")
    assert response.status_code == 200

    # Should not be able to retrieve this game
    response = client.get(f"{config.api_prefix}/games/{game_id}")
    data = response.json()
    assert response.status_code == 404
    assert data["error"] == "GameNotFoundError"


def test_playing_five_turns(client: TestClient) -> None:
    """
    1. Create a new game via POST /games.
    2. POST /games/{game_id}/players
    3a. GET /games/{game_id}/legal-moves
    3b. POST /games/{game_id}/moves (select a legal move from the list)
    3c. GET /games/{game_id}
    4. DELETE /games/{game_id}

    Assertions:
    ------
    I. All steps succeed
    II. Game state updates as expected across different calls.
    III. Can no longer make a move after checkmate is reached.
    """
    #  Create a new game via POST /games.
    response = client.post(
        f"{config.api_prefix}/games",
        json={
            "player_name": "FirstPlayer",
            "color": "white",
        },
    )
    assert response.status_code == 200

    data = response.json()
    game_id = data["game_id"]

    # Second player joins the game via POST /games/{game_id}/players
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/players",
        json={"player_name": "SecondPlayer"},
    )
    assert response.status_code == 200

    # Play a couple of turns
    expected_moves: list[str] = []
    for _ in range(5):
        for player in ["FirstPlayer", "SecondPlayer"]:
            #  GET /games/{game_id}/legal-moves
            response = client.get(
                f"{config.api_prefix}/games/{game_id}/legal-moves",
                params={"player_name": player},
            )
            assert response.status_code == 200

            data = response.json()
            legal_moves = data["legal_moves"]

            # POST the first option of the legal moves
            new_move = legal_moves[0]
            sq_from, sq_to = new_move[:2], new_move[2:]
            payload: dict[str, str] = {
                "player_name": player,
                "from_square": sq_from,
                "to_square": sq_to,
            }
            response = client.post(
                f"{config.api_prefix}/games/{game_id}/moves", json=payload
            )
            assert response.status_code == 200
            expected_moves.append(new_move)

    #  Retrieve the game via GET /games/{game_id}.
    response = client.get(f"{config.api_prefix}/games/{game_id}")
    retrieved_game_data = response.json()
    assert response.status_code == 200
    assert retrieved_game_data["game_id"] == game_id
    assert retrieved_game_data["players"] == {
        "white": "FirstPlayer",
        "black": "SecondPlayer",
    }
    assert (
        retrieved_game_data["fen_state"]
        == "r1bqkbnr/pPpppppp/2n5/8/8/8/1PPPPPPP/RNBQKBNR w KQk - 1 6"
    )
    assert retrieved_game_data["starting_state"] == CANONICAL_STARTING_FEN
    assert retrieved_game_data["move_history"] == expected_moves
    assert retrieved_game_data["winner"] is None

    # Remove record from repository via DELETE /games/{game_id}
    response = client.delete(f"{config.api_prefix}/games/{game_id}")
    assert response.status_code == 200


def test_full_flow_by_game_name(client: TestClient) -> None:
    """
    1. Create a new game via POST /games and specify a game name.
    2. POST /games/{game_name}/players
    3a. GET /games/{game_name}/legal-moves
    3b. POST /games/{game_name}/moves (select a legal move from the list)
    3c. GET /games/{game_name}
    4. DELETE /games/{game_name}
    """
    unique_number = (
        uuid4()
    )  # NOTE: not the same as the game_id, just to make names unique between tests.
    #  Create a new game via POST /games.
    response = client.post(
        f"{config.api_prefix}/games",
        json={
            "player_name": "FirstPlayer",
            "color": "white",
            "game_name": f"Test game {unique_number}",
        },
    )
    assert response.status_code == 200

    data = response.json()
    game_name = data["game_name"]

    # check normalization happened
    expected_name = f"test-game-{unique_number}"
    assert game_name == expected_name

    # Second player joins the game via POST /games/{game_name}/players
    response = client.post(
        f"{config.api_prefix}/games/{game_name}/players",
        json={"player_name": "SecondPlayer"},
    )
    assert response.status_code == 200

    # Play a couple of turns
    expected_moves: list[str] = []
    for _ in range(5):
        for player in ["FirstPlayer", "SecondPlayer"]:
            #  GET /games/{game_name}/legal-moves
            response = client.get(
                f"{config.api_prefix}/games/{game_name}/legal-moves",
                params={"player_name": player},
            )
            assert response.status_code == 200

            data = response.json()
            legal_moves = data["legal_moves"]

            # POST the first option of the legal moves
            new_move = legal_moves[0]
            sq_from, sq_to = new_move[:2], new_move[2:]
            payload: dict[str, str] = {
                "player_name": player,
                "from_square": sq_from,
                "to_square": sq_to,
            }
            response = client.post(
                f"{config.api_prefix}/games/{game_name}/moves", json=payload
            )
            assert response.status_code == 200
            expected_moves.append(new_move)

    #  Retrieve the game via GET /games/{game_name}.
    response = client.get(f"{config.api_prefix}/games/{game_name}")
    retrieved_game_data = response.json()
    assert response.status_code == 200
    assert retrieved_game_data["game_name"] == game_name
    assert retrieved_game_data["players"] == {
        "white": "FirstPlayer",
        "black": "SecondPlayer",
    }
    assert (
        retrieved_game_data["fen_state"]
        == "r1bqkbnr/pPpppppp/2n5/8/8/8/1PPPPPPP/RNBQKBNR w KQk - 1 6"
    )
    assert retrieved_game_data["starting_state"] == CANONICAL_STARTING_FEN
    assert retrieved_game_data["move_history"] == expected_moves
    assert retrieved_game_data["winner"] is None

    # Remove record from repository via DELETE /games/{game_name}
    response = client.delete(f"{config.api_prefix}/games/{game_name}")
    assert response.status_code == 200


def test_equivalence_game_name_and_uuid(client: TestClient) -> None:
    """A GET request to /games/{game_id} should return the same as /games/{game_name}"""
    game_name = f"test-game-{uuid4()}"
    #  Create a new game via POST /games.
    response = client.post(
        f"{config.api_prefix}/games",
        json={"player_name": "FirstPlayer", "color": "white", "game_name": game_name},
    )
    assert response.status_code == 200
    data = response.json()
    game_id = data["game_id"]

    # Second player joins the game
    response = client.post(
        f"{config.api_prefix}/games/{game_name}/players",
        json={"player_name": "SecondPlayer"},
    )
    assert response.status_code == 200

    # Fetch the game by id
    response = client.get(f"{config.api_prefix}/games/{game_id}")
    assert response.status_code == 200
    by_id = response.json()

    # Fetch the game by name
    response = client.get(f"{config.api_prefix}/games/{game_name}")
    assert response.status_code == 200
    by_name = response.json()

    # Test equivalence
    assert by_id == by_name


def test_get_all_game_identifiers(client: TestClient) -> None:
    """GET to /games/identifiers"""
    # Create two games with names
    first_name = f"test-game-{uuid4()}"
    second_name = f"test-game-{uuid4()}"
    response = client.post(
        f"{config.api_prefix}/games",
        json={"player_name": "FirstPlayer", "color": "white", "game_name": first_name},
    )
    assert response.status_code == 200
    data = response.json()
    first_id = data["game_id"]

    response = client.post(
        f"{config.api_prefix}/games",
        json={"player_name": "FirstPlayer", "color": "white", "game_name": second_name},
    )
    assert response.status_code == 200
    data = response.json()
    second_id = data["game_id"]

    # Create a game without a name
    response = client.post(
        f"{config.api_prefix}/games",
        json={"player_name": "FirstPlayer", "color": "white"},
    )
    assert response.status_code == 200
    data = response.json()
    third_id = data["game_id"]

    # Get the game identifiers
    response = client.get(f"{config.api_prefix}/games/identifiers")
    data = response.json()
    retrieved_identifier_pairs = [(item["name"], item["uuid"]) for item in data]
    expected_identifier_pairs: list[tuple[str | None, UUID]] = [
        (first_name, first_id),
        (second_name, second_id),
        (None, third_id),
    ]
    assert all(pair in retrieved_identifier_pairs for pair in expected_identifier_pairs)


def test_create_game_duplicate_name_api(client: TestClient) -> None:
    """Cannot create two games with the same name."""
    # Create the first game
    game_name = f"test-game-{uuid4()}"
    #  Create a new game via POST /games.
    response = client.post(
        f"{config.api_prefix}/games",
        json={"player_name": "FirstPlayer", "color": "white", "game_name": game_name},
    )
    assert response.status_code == 200

    # Attempt to create another game with the same name
    response = client.post(
        f"{config.api_prefix}/games",
        json={"player_name": "SecondPlayer", "color": "black", "game_name": game_name},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "GameCreationError"


def test_no_move_after_checkmate(client: TestClient) -> None:
    """play checkmate, then make sure a subsequent request to move fails (no more legal moves)."""

    # start a game with black about to checkmate white
    ladder_mate_incoming = "4k3/8/8/8/8/7r/6r1/4K3 b - - 0 1"
    response = client.post(
        f"{config.api_prefix}/games",
        json={
            "player_name": "WinnerWinnerChickenDinner",
            "color": "black",
            "starting_fen": ladder_mate_incoming,
        },
    )
    assert response.status_code == 200
    data = response.json()
    game_id = data["game_id"]
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/players",
        json={"player_name": "SnoozerLoser"},
    )
    assert response.status_code == 200

    # black mates white
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/moves",
        json={
            "player_name": "WinnerWinnerChickenDinner",
            "from_square": "h3",
            "to_square": "h1",
        },
    )
    assert response.status_code == 200

    # Check that recorded game is in status of CheckMate
    response = client.get(f"{config.api_prefix}/games/{game_id}")
    assert response.status_code == 200

    retrieved_game_data = response.json()
    assert retrieved_game_data["status"] == "checkmate"
    assert retrieved_game_data["winner"] == "WinnerWinnerChickenDinner"

    # Now white should not be able to move anymore
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/moves",
        json={
            "player_name": "SnoozerLoser",
            "from_square": "e1",
            "to_square": "d1",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"] == "GameStateError"


def test_no_move_after_stalemate(client: TestClient) -> None:
    """play stalemate, then make sure a subsequent request to move fails (no more legal moves)."""

    # start a game with black about to force stalemate
    stalemate_incoming = "4k3/8/8/8/8/4q3/8/7K b - - 0 1"
    response = client.post(
        f"{config.api_prefix}/games",
        json={
            "player_name": "ShouldveCouldveWon",
            "color": "black",
            "starting_fen": stalemate_incoming,
        },
    )
    assert response.status_code == 200
    data = response.json()
    game_id = data["game_id"]
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/players",
        json={"player_name": "LuckyDidNotLose"},
    )
    assert response.status_code == 200

    # black plays into stalemate
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/moves",
        json={
            "player_name": "ShouldveCouldveWon",
            "from_square": "e3",
            "to_square": "f2",
        },
    )
    assert response.status_code == 200

    # Check that recorded game is in status of stalemate
    response = client.get(f"{config.api_prefix}/games/{game_id}")
    assert response.status_code == 200

    retrieved_game_data = response.json()
    assert retrieved_game_data["status"] == "stalemate"
    assert retrieved_game_data["winner"] is None

    # Now white should not be able to move anymore
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/moves",
        json={
            "player_name": "LuckyDidNotLose",
            "from_square": "h1",
            "to_square": "g1",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"] == "GameStateError"


@pytest.mark.parametrize(
    "http_method,endpoint, payload",
    [
        ("get", "", None),
        (
            "post",
            "players",
            {"player_name": "player"},
        ),
        (
            "get",
            "legal-moves",
            {"player_name": "player"},
        ),
        (
            "post",
            "moves",
            {"player_name": "player", "from_square": "a1", "to_square": "a2"},
        ),
    ],
)
def test_game_not_found_error(
    http_method: str,
    endpoint: str,
    payload: dict[str, str] | None,
    client: TestClient,
) -> None:
    """GameNotFoundError with status code 404"""

    client_method = getattr(client, http_method)
    url = f"{config.api_prefix}/games/{MOCK_ID}/{endpoint}"
    if payload:
        response = (
            client_method(url, json=payload)
            if http_method != "get"
            else client_method(url, params=payload)
        )
    else:
        response = client_method(url)

    assert response.status_code == 404
    assert response.json()["error"] == "GameNotFoundError"


def test_cannot_join_game_in_progress(client: TestClient) -> None:
    """Third player attempts to join a game (that is already full)."""
    #  Create a new game via POST /games.
    response = client.post(
        f"{config.api_prefix}/games",
        json={
            "player_name": "FirstPlayer",
            "color": "white",
        },
    )
    assert response.status_code == 200

    data = response.json()
    game_id = data["game_id"]

    # Second player joins the game via POST /games/{game_id}/players
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/players",
        json={"player_name": "SecondPlayer"},
    )
    assert response.status_code == 200

    # Attempt to join with third player
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/players",
        json={"player_name": "ThirdPlayer"},
    )
    assert response.status_code == 409
    assert response.json()["error"] == "GameStateError"

    # check that the game is in progress
    response = client.get(f"{config.api_prefix}/games/{game_id}")
    retrieved_game = response.json()
    assert retrieved_game["status"] == "in progress"


def test_player_cannot_join_twice() -> None:
    """
    TODO Raise a PlayerAlreadyJoinedError when attempting to join a game with the same player name twice.
    TODO this avoids all kinds of issues with turn tracking (say I try to play against myself, then code will not be able to reliably fetch the color I am playing with)
    """


def test_make_illegal_move(client: TestClient) -> None:
    """Game logic breaks down. Status code 400."""
    #  Create a new game via POST /games.
    response = client.post(
        f"{config.api_prefix}/games",
        json={
            "player_name": "FirstPlayer",
            "color": "white",
        },
    )
    assert response.status_code == 200

    data = response.json()
    game_id = data["game_id"]

    # Second player joins the game via POST /games/{game_id}/players
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/players",
        json={"player_name": "SecondPlayer"},
    )
    assert response.status_code == 200

    # FirstPlayer attempts to teleport their queen to the middle of the board
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/moves",
        json={
            "player_name": "FirstPlayer",
            "from_square": "d1",
            "to_square": "d5",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == "IllegalMoveError"


def test_legal_moves_unknown_player_name() -> None:
    """
    NOTE this is conceptually different from "it is your opponent's turn."
    NOTE raise a NotYourTurnError and let message signify it is actually because you are not registered at this game.
    """


@pytest.mark.parametrize(
    "http_method,endpoint, payload",
    [
        (
            "get",
            "legal-moves",
            {"player_name": "SecondPlayer"},
        ),
        (
            "post",
            "moves",
            {"player_name": "SecondPlayer", "from_square": "e7", "to_square": "e5"},
        ),
    ],
)
def test_moving_before_your_turn(
    http_method: str,
    endpoint: str,
    payload: dict[str, str],
    client: TestClient,
) -> None:
    """Request legal-moves / making a legal move during your opponent's turn."""
    #  Create a new game via POST /games.
    response = client.post(
        f"{config.api_prefix}/games",
        json={
            "player_name": "FirstPlayer",
            "color": "white",
        },
    )
    assert response.status_code == 200

    data = response.json()
    game_id = data["game_id"]

    # Second player joins the game via POST /games/{game_id}/players
    response = client.post(
        f"{config.api_prefix}/games/{game_id}/players",
        json={"player_name": "SecondPlayer"},
    )
    assert response.status_code == 200

    # Second player (playing with black) tries to move already
    client_method = getattr(client, http_method)
    url = f"{config.api_prefix}/games/{game_id}/{endpoint}"
    response = (
        client_method(url, json=payload)
        if http_method != "get"
        else client_method(url, params=payload)
    )
    assert response.status_code == 409
    assert response.json()["error"] == "NotYourTurnError"


@pytest.mark.parametrize(
    "http_method,endpoint, payload",
    [
        (
            "get",
            "legal-moves",
            {"player_name": "FirstPlayer"},
        ),
        (
            "post",
            "moves",
            {"player_name": "FirstPlayer", "from_square": "e2", "to_square": "e4"},
        ),
    ],
)
def test_moving_before_game_in_progress(
    http_method: str,
    endpoint: str,
    payload: dict[str, str],
    client: TestClient,
) -> None:
    """Cannot request legal moves / make moves before both players have joined the game."""
    #  Create a new game via POST /games.
    response = client.post(
        f"{config.api_prefix}/games",
        json={
            "player_name": "FirstPlayer",
            "color": "white",
        },
    )
    assert response.status_code == 200

    data = response.json()
    game_id = data["game_id"]

    # Second player (playing with black) tries to move already
    client_method = getattr(client, http_method)
    url = f"{config.api_prefix}/games/{game_id}/{endpoint}"
    response = (
        client_method(url, json=payload)
        if http_method != "get"
        else client_method(url, params=payload)
    )
    assert response.status_code == 409
    assert response.json()["error"] == "GameStateError"

    # check that the game is still waiting for a second player to join
    response = client.get(f"{config.api_prefix}/games/{game_id}")
    retrieved_game = response.json()
    assert retrieved_game["status"] == "waiting for players"
