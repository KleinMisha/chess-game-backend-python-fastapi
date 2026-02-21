"""Unit tests for src/services/chess_service.py"""

from typing import Generator
from uuid import UUID, uuid4

import pytest

from src.core.exceptions import GameError
from src.core.models import GameModel
from src.core.shared_types import Color, Status
from src.services.chess_service import (
    ChessService,
    CreateGameRequest,
    DeleteGameRequest,
    GameResponse,
    GetGameRequest,
    JoinGameRequest,
    LegalMovesRequest,
    LegalMovesResponse,
    MoveRequest,
)

# --- MOCK DEPENDENCIES ----
MOCK_FEN_STATE = "8/8/8/8/8/8/8/8 w KQq - 8 24"


class MockRepository:
    """Mock the GameRepository using a dictionary of game models."""

    def __init__(self) -> None:
        self._games: dict[UUID, GameModel] = {}

    def create_game(self, game: GameModel) -> tuple[GameModel, UUID]:
        """Store new game and return the stored data + newly created game ID."""
        game_id = uuid4()
        self._games[game_id] = game
        return game, game_id

    def get_game(self, game_id: UUID) -> GameModel | None:
        """Get game by ID, if record exists."""
        return self._games.get(game_id)

    def update_game(self, game_id: UUID, game: GameModel) -> GameModel | None:
        """Add new info to existing record."""
        if game_id not in self._games:
            return None
        self._games[game_id] = game
        return game

    def delete_game(self, game_id: UUID) -> GameModel | None:
        """Remove a game's record."""
        self._games.pop(game_id, None)

    def clear(self) -> None:
        """Clear the repository (useful in between tests)"""
        self._games.clear()


@pytest.fixture
def mock_repository() -> Generator[MockRepository]:
    """Ensures to clear the repository between tests"""
    repo = MockRepository()
    try:
        yield repo
    finally:
        repo.clear()


# --- SERVICE - CREATE NEW GAME ----
def test_create_a_new_game(mock_repository: MockRepository) -> None:
    """Check that new game is created, persisted in repo, and return has the appropriate information."""

    player_name = "Mocker M. Mockerson"
    mock_request = CreateGameRequest(
        player_name=player_name, color=Color.WHITE, starting_fen=MOCK_FEN_STATE
    )
    repository = mock_repository
    service = ChessService(repository)
    response = service.create_new_game(mock_request)

    # Check response structure
    assert isinstance(response, GameResponse)
    assert isinstance(response.game_id, UUID)

    # Check response data
    assert response.fen_state == MOCK_FEN_STATE
    assert response.starting_state == MOCK_FEN_STATE
    assert response.players == {Color.WHITE: player_name}
    assert response.move_history == []

    # Check persisted data
    stored_game = repository.get_game(response.game_id)
    assert stored_game is not None
    assert stored_game.current_fen == MOCK_FEN_STATE
    assert stored_game.history_fen == []
    assert stored_game.moves_uci == []
    assert stored_game.registered_players == {Color.WHITE: player_name}
    assert stored_game.status == Status.WAITING_FOR_PLAYERS


def test_create_with_invalid_fen(mock_repository: MockRepository) -> None:
    """Make sure service propagates the exceptions."""
    player_name = "Mocker M. Mockerson"
    mock_request = CreateGameRequest(
        player_name=player_name,
        color=Color.BLACK,
        starting_fen=" ".join(["mock"] * 6),
    )

    # Test any top-level custom exception is raised (specific exception types are responsibility of other layers)
    with pytest.raises(GameError):
        repository = mock_repository
        service = ChessService(repository)
        _ = service.create_new_game(mock_request)


# --- SERVICE - JOIN GAME ----
def test_second_player_joins_game(mock_repository: MockRepository) -> None:
    """Create a new game and let second player join"""

    # make sure to create a game first (otherwise nothing in repository)
    player_name = "Mocker M. Mockerson"
    create_request = CreateGameRequest(
        player_name=player_name, color=Color.WHITE, starting_fen=MOCK_FEN_STATE
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    # second player should now join the game
    second_name = "Mock McMock"
    request = JoinGameRequest(game_id=create_response.game_id, player_name=second_name)
    response = service.join_game(request)

    # Check response structure
    assert isinstance(response, GameResponse)

    # Check response data
    assert response.game_id == create_response.game_id
    assert response.fen_state == MOCK_FEN_STATE
    assert response.starting_state == MOCK_FEN_STATE
    assert response.players == {Color.WHITE: player_name, Color.BLACK: second_name}
    assert response.move_history == []

    # Check persisted data
    stored_game = repository.get_game(response.game_id)
    assert stored_game is not None
    assert stored_game.current_fen == MOCK_FEN_STATE
    assert stored_game.history_fen == []
    assert stored_game.moves_uci == []
    assert stored_game.registered_players == {
        Color.WHITE: player_name,
        Color.BLACK: second_name,
    }
    assert stored_game.status == Status.IN_PROGRESS


def test_cannot_join_before_first_player(mock_repository: MockRepository) -> None:
    """A GameError should be raised (GameStatusError) if attempting to join a not yet existing game."""
    second_name = "Mock McMock"
    non_existing_game = uuid4()
    request = JoinGameRequest(game_id=non_existing_game, player_name=second_name)
    repository = mock_repository
    service = ChessService(repository)
    with pytest.raises(GameError):
        _ = service.join_game(request)


# --- SERVICE - GET GAME ----
def test_get_existing_game_state(mock_repository: MockRepository) -> None:
    """Retrieve a game from the repository from an ID generated during creation."""
    player_name = "Mocker M. Mockerson"
    create_request = CreateGameRequest(
        player_name=player_name, color=Color.WHITE, starting_fen=MOCK_FEN_STATE
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    # retrieve the persisted game
    request = GetGameRequest(game_id=create_response.game_id)
    response = service.get_game_state(request)

    # Check response structure
    assert response is not None
    assert isinstance(response, GameResponse)

    # Check response data
    assert response.fen_state == MOCK_FEN_STATE
    assert response.starting_state == MOCK_FEN_STATE
    assert response.players == {Color.WHITE: player_name}
    assert response.move_history == []


def test_attempt_to_find_unknown_game(mock_repository: MockRepository) -> None:
    """Ensure exception is raised when trying to look up a game with an unknown ID."""
    non_existing_id = uuid4()
    with pytest.raises(GameError):
        request = GetGameRequest(game_id=non_existing_id)
        repository = mock_repository
        service = ChessService(repository)
        _ = service.get_game_state(request)


# --- SERVICE - LEGAL MOVES ----
def test_getting_legal_moves(mock_repository: MockRepository) -> None:
    """Given a proper LegalMovesRequest, does the service return the expected LegalMovesResponse?"""
    player_white = "Whitey McWhite"
    create_request = CreateGameRequest(
        player_name=player_white,
        color=Color.WHITE,
        starting_fen="k7/8/8/8/8/8/8/K7 w - - 8 24",
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    player_black = "Blackey McBlack"
    join_request = JoinGameRequest(
        game_id=create_response.game_id, player_name=player_black
    )
    _ = service.join_game(join_request)

    # It is white to move - ask for available legal moves
    request = LegalMovesRequest(
        game_id=create_response.game_id, player_name=player_white
    )
    response = service.legal_moves(request)

    # Check response structure
    assert isinstance(response, LegalMovesResponse)

    # Check response data
    assert response.game_id == create_response.game_id
    assert response.color == Color.WHITE
    assert response.player_name == player_white
    assert set(response.legal_moves) == set(["a1b1", "a1a2", "a1b2"])


def test_getting_legal_moves_before_your_turn(mock_repository: MockRepository) -> None:
    """Service must propagate error raised by Game upwards."""

    player_white = "Whitey McWhite"
    create_request = CreateGameRequest(
        player_name=player_white,
        color=Color.WHITE,
        starting_fen="k7/8/8/8/8/8/8/K7 w - - 8 24",
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    player_black = "Blackey McBlack"
    join_request = JoinGameRequest(
        game_id=create_response.game_id, player_name=player_black
    )
    _ = service.join_game(join_request)

    # It is white to move - ask for legal moves for player with BLACK pieces.
    with pytest.raises(GameError):
        request = LegalMovesRequest(
            game_id=create_response.game_id, player_name=player_black
        )
        _ = service.legal_moves(request)


def test_attempt_legal_moves_before_second_player(
    mock_repository: MockRepository,
) -> None:
    """Service must propagate error raised by Game upwards."""
    player_white = "Whitey McWhite"
    create_request = CreateGameRequest(
        player_name=player_white,
        color=Color.WHITE,
        starting_fen="k7/8/8/8/8/8/8/K7 w - - 8 24",
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    # Second player did not join yet - already ask for legal moves.
    with pytest.raises(GameError):
        request = LegalMovesRequest(
            game_id=create_response.game_id, player_name=player_white
        )
        _ = service.legal_moves(request)


def test_attempt_legal_moves_after_checkmate(mock_repository: MockRepository) -> None:
    """Service must propagate error raised by Game upwards."""

    player_white = "Whitey McWhite"
    create_request = CreateGameRequest(
        player_name=player_white,
        color=Color.WHITE,
        starting_fen="k7/6RR/8/8/8/8/K7/8 w - - 0 1",
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    player_black = "Blackey McBlack"
    join_request = JoinGameRequest(
        game_id=create_response.game_id, player_name=player_black
    )
    _ = service.join_game(join_request)

    # White checkmates black:
    ladder_mate = MoveRequest(
        game_id=create_response.game_id,
        player_name=player_white,
        from_square="h7",
        to_square="h8",
    )
    _ = service.make_move(ladder_mate)

    # Game is over: Black cannot request any legal moves
    with pytest.raises(GameError):
        request = LegalMovesRequest(
            game_id=create_response.game_id, player_name=player_black
        )

        _ = service.legal_moves(request)


# --- SERVICE - MAKE MOVE ---
def test_make_legal_move(mock_repository: MockRepository) -> None:
    """Attempt a legal move during your turn. Should result in a GameResponse."""
    player_white = "Whitey McWhite"
    create_request = CreateGameRequest(
        player_name=player_white,
        color=Color.WHITE,
        starting_fen="k7/8/8/8/8/8/8/K7 w - - 8 24",
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    player_black = "Blackey McBlack"
    join_request = JoinGameRequest(
        game_id=create_response.game_id, player_name=player_black
    )
    _ = service.join_game(join_request)

    # make a legal move
    request = MoveRequest(
        game_id=create_response.game_id,
        player_name=player_white,
        from_square="a1",
        to_square="a2",
    )
    response = service.make_move(request)

    # Check response structure
    assert isinstance(response, GameResponse)

    # Check response data
    assert response.game_id == create_response.game_id
    assert response.fen_state == "k7/8/8/8/8/8/K7/8 b - - 9 24"
    assert response.starting_state == "k7/8/8/8/8/8/8/K7 w - - 8 24"
    assert response.move_history == ["a1a2"]

    # Check persisted data
    stored_game = repository.get_game(response.game_id)
    assert stored_game is not None
    assert stored_game.current_fen == "k7/8/8/8/8/8/K7/8 b - - 9 24"
    assert stored_game.history_fen == ["k7/8/8/8/8/8/8/K7 w - - 8 24"]
    assert stored_game.moves_uci == ["a1a2"]


def test_attempt_illegal_move(mock_repository: MockRepository) -> None:
    """Service must propagate error raised by Game upwards."""
    player_white = "Whitey McWhite"
    create_request = CreateGameRequest(
        player_name=player_white,
        color=Color.WHITE,
        starting_fen="k7/8/8/8/8/8/8/K7 w - - 8 24",
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    player_black = "Blackey McBlack"
    join_request = JoinGameRequest(
        game_id=create_response.game_id, player_name=player_black
    )
    _ = service.join_game(join_request)

    # Attempt an illegal move (some random squares)
    with pytest.raises(GameError):
        request = MoveRequest(
            game_id=create_response.game_id,
            player_name=player_white,
            from_square="d1",
            to_square="h2",
        )
        _ = service.make_move(request)


def test_attempt_move_before_your_turn(mock_repository: MockRepository) -> None:
    """Service must propagate error raised by Game upwards."""
    player_white = "Whitey McWhite"
    create_request = CreateGameRequest(
        player_name=player_white,
        color=Color.WHITE,
        starting_fen="k7/8/8/8/8/8/8/K7 w - - 8 24",
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    player_black = "Blackey McBlack"
    join_request = JoinGameRequest(
        game_id=create_response.game_id, player_name=player_black
    )
    _ = service.join_game(join_request)

    # White to move - Black attempts to move already
    with pytest.raises(GameError):
        request = MoveRequest(
            game_id=create_response.game_id,
            player_name=player_black,
            from_square="a8",
            to_square="a7",
        )
        _ = service.make_move(request)


def test_attempt_move_before_second_player(mock_repository: MockRepository) -> None:
    """Service must propagate error raised by Game upwards."""
    player_white = "Whitey McWhite"
    create_request = CreateGameRequest(
        player_name=player_white,
        color=Color.WHITE,
        starting_fen="k7/8/8/8/8/8/8/K7 w - - 8 24",
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    # Attempt an illegal move (some random squares)
    with pytest.raises(GameError):
        request = MoveRequest(
            game_id=create_response.game_id,
            player_name=player_white,
            from_square="a1",
            to_square="a2",
        )
        _ = service.make_move(request)


def test_attempt_move_after_checkmate(mock_repository: MockRepository) -> None:
    """Service must propagate error raised by Game upwards."""
    player_white = "Whitey McWhite"
    create_request = CreateGameRequest(
        player_name=player_white,
        color=Color.WHITE,
        starting_fen="k7/6RR/8/8/8/8/K7/8 w - - 0 1",
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    player_black = "Blackey McBlack"
    join_request = JoinGameRequest(
        game_id=create_response.game_id, player_name=player_black
    )
    _ = service.join_game(join_request)

    # White checkmates black:
    ladder_mate = MoveRequest(
        game_id=create_response.game_id,
        player_name=player_white,
        from_square="h7",
        to_square="h8",
    )
    _ = service.make_move(ladder_mate)

    # Black should no longer be able to move
    with pytest.raises(GameError):
        request = MoveRequest(
            game_id=create_response.game_id,
            player_name=player_black,
            from_square="a8",
            to_square="a7",
        )
        _ = service.make_move(request)


# --- SERVICE - DELETE GAME ---
def test_delete_game_from_repository(mock_repository: MockRepository) -> None:
    """A game should no longer be available in the repository after a properly processed request."""

    create_request = CreateGameRequest(
        player_name="Mocker McMocker",
        color=Color.WHITE,
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    # delete the game
    request = DeleteGameRequest(game_id=create_response.game_id)
    service.delete_game(request)

    # should no longer exist in repository
    with pytest.raises(GameError):
        get_request = GetGameRequest(game_id=create_response.game_id)
        _ = service.get_game_state(get_request)
