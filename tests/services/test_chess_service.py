"""Unit tests for src/services/chess_service.py"""

from typing import Generator, Optional
from uuid import UUID, uuid4

import pytest

from src.core.exceptions import BaseError
from src.core.models import GameModel
from src.core.shared_types import Color, Status
from src.services.chess_service import (
    ChessService,
    CreateGameRequest,
    GameResponse,
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
        self._names: dict[str, UUID] = {}

    def create_game(
        self, game: GameModel, name: Optional[str] = None
    ) -> tuple[GameModel, UUID]:
        """Store new game and return the stored data + newly created game ID."""
        game_id = uuid4()
        self._games[game_id] = game

        if name is not None:
            self._names[name] = game_id
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

    def name_exists(self, name: str) -> bool:
        """Check if there already is a record with the suggested alias."""
        return name in self._names

    def get_id_by_name(self, name: str) -> UUID | None:
        """Find the game ID with the given name (alias)."""
        return self._names.get(name, None)

    def get_name_by_id(self, game_id: UUID) -> str | None:
        """Find the game name (if any) for the game with the given ID."""
        return next(
            (name for name in self._names if self._names[name] == game_id), None
        )

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
    assert response.game_name is None

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


def test_create_new_game_with_name(mock_repository: MockRepository) -> None:
    """Check that creating a game with a specified name works."""
    game_name = "my-game"
    player_name = "Mocker M. Mockerson"
    mock_request = CreateGameRequest(
        game_name=game_name,
        player_name=player_name,
        color=Color.WHITE,
        starting_fen=MOCK_FEN_STATE,
    )
    repository = mock_repository
    service = ChessService(repository)
    response = service.create_new_game(mock_request)

    # Check response structure
    assert isinstance(response, GameResponse)
    assert isinstance(response.game_id, UUID)
    assert isinstance(response.game_name, str)

    # Check response data
    assert response.game_name == game_name
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


@pytest.mark.parametrize(
    "game_name",
    [
        "my_game",  # snake-case
        "My-Game",  # upper-case
        "My game",  # spaces
    ],
)
def test_create_new_game_normalizes_name(
    mock_repository: MockRepository, game_name: str
) -> None:
    """Check that persisted name is normalized / preprocessed."""

    expected_normalized_name = "my-game"
    player_name = "Mocker M. Mockerson"
    mock_request = CreateGameRequest(
        game_name=game_name,
        player_name=player_name,
        color=Color.WHITE,
        starting_fen=MOCK_FEN_STATE,
    )
    repository = mock_repository
    service = ChessService(repository)
    response = service.create_new_game(mock_request)

    # Check response structure
    assert isinstance(response, GameResponse)
    assert isinstance(response.game_id, UUID)
    assert isinstance(response.game_name, str)

    # Check response data
    assert response.game_name == expected_normalized_name


@pytest.mark.parametrize(
    "empty_string",
    [
        "",  # simple empty string
        " ",  # one white-space
        "    ",  # bunch of white-spaces
    ],
)
def test_create_new_game_with_empty_name(
    mock_repository: MockRepository, empty_string: str
) -> None:
    """Do not persist game name if request has empty string"""
    player_name = "Mocker M. Mockerson"
    mock_request = CreateGameRequest(
        game_name=empty_string,
        player_name=player_name,
        color=Color.WHITE,
        starting_fen=MOCK_FEN_STATE,
    )
    repository = mock_repository
    service = ChessService(repository)
    response = service.create_new_game(mock_request)

    # Check response structure
    assert isinstance(response, GameResponse)
    assert isinstance(response.game_id, UUID)
    assert response.game_name is None


@pytest.mark.parametrize(
    "game_name",
    [
        "my-game",  # already normalized
        "my_game",  # snake-case
        "My-Game",  # upper-case
        "My game",  # spaces
    ],
)
def test_create_game_with_duplicate_name(
    mock_repository: MockRepository, game_name: str
) -> None:
    """Attempt to make a new game, whose supplied name matches an existing record after normalization."""
    # All of the candidate names result in this same normalized name:
    normalized_name = "my-game"

    # create first game
    player_name = "Mocker M. Mockerson"
    mock_request = CreateGameRequest(
        game_name=normalized_name,
        player_name=player_name,
        color=Color.WHITE,
        starting_fen=MOCK_FEN_STATE,
    )
    repository = mock_repository
    service = ChessService(repository)
    _ = service.create_new_game(mock_request)

    # Attempt to create another game, but the normalized name already exists
    player_name = "He who snoozeth is he who loseth."
    mock_request = CreateGameRequest(
        game_name=game_name,
        player_name=player_name,
        color=Color.WHITE,
        starting_fen=MOCK_FEN_STATE,
    )
    with pytest.raises(BaseError):
        _ = service.create_new_game(mock_request)


def test_create_with_invalid_fen(mock_repository: MockRepository) -> None:
    """Make sure service propagates the exceptions."""
    player_name = "Mocker M. Mockerson"
    mock_request = CreateGameRequest(
        player_name=player_name,
        color=Color.BLACK,
        starting_fen=" ".join(["mock"] * 6),
    )

    # Test any top-level custom exception is raised (specific exception types are responsibility of other layers)
    with pytest.raises(BaseError):
        repository = mock_repository
        service = ChessService(repository)
        _ = service.create_new_game(mock_request)


# --- SERVICE - JOIN GAME ----
def test_second_player_joins_game_by_uuid_str(mock_repository: MockRepository) -> None:
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
    request = JoinGameRequest(player_name=second_name)
    response = service.join_game(str(create_response.game_id), request)

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


def test_second_player_joins_game_by_name(mock_repository: MockRepository) -> None:
    """Join a game using the alias / game-name."""
    # make sure to create a game first (otherwise nothing in repository)
    game_name = "my-game"
    player_name = "Mocker M. Mockerson"
    create_request = CreateGameRequest(
        game_name=game_name,
        player_name=player_name,
        color=Color.WHITE,
        starting_fen=MOCK_FEN_STATE,
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    # second player should now join the game
    second_name = "Mock McMock"
    request = JoinGameRequest(player_name=second_name)
    response = service.join_game(game_name, request)

    # Check response structure
    assert isinstance(response, GameResponse)

    # Check response data
    assert response.game_name == game_name
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
    request = JoinGameRequest(player_name=second_name)
    repository = mock_repository
    service = ChessService(repository)
    with pytest.raises(BaseError):
        _ = service.join_game(str(non_existing_game), request)


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
    response = service.get_game_state(str(create_response.game_id))

    # Check response structure
    assert response is not None
    assert isinstance(response, GameResponse)

    # Check response data
    assert response.fen_state == MOCK_FEN_STATE
    assert response.starting_state == MOCK_FEN_STATE
    assert response.players == {Color.WHITE: player_name}
    assert response.move_history == []


def test_get_existing_game_state_by_name(mock_repository: MockRepository) -> None:
    """Fetching a game by name should result in the same as fetching it by ID."""
    game_name = "my-game"
    player_name = "Mocker M. Mockerson"
    create_request = CreateGameRequest(
        game_name=game_name,
        player_name=player_name,
        color=Color.WHITE,
        starting_fen=MOCK_FEN_STATE,
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    # retrieve the persisted game --> result should be the same as in test above
    response_by_id = service.get_game_state(str(create_response.game_id))
    response_by_name = service.get_game_state(game_name)
    assert response_by_name == response_by_id


def test_attempt_to_find_unknown_game(mock_repository: MockRepository) -> None:
    """Ensure exception is raised when trying to look up a game with an unknown ID."""
    non_existing_id = uuid4()
    with pytest.raises(BaseError):
        repository = mock_repository
        service = ChessService(repository)
        _ = service.get_game_state(str(non_existing_id))


def test_attempt_to_find_unknown_game_name(mock_repository: MockRepository) -> None:
    """Ensure exception is raised when trying to look up a game with unknown name."""
    wrong_name = "Not the correct name"
    game_name = "my-game"
    player_name = "Mocker M. Mockerson"
    create_request = CreateGameRequest(
        game_name=game_name,
        player_name=player_name,
        color=Color.WHITE,
        starting_fen=MOCK_FEN_STATE,
    )
    repository = mock_repository
    service = ChessService(repository)
    _ = service.create_new_game(create_request)
    with pytest.raises(BaseError):
        _ = service.get_game_state(wrong_name)


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
    join_request = JoinGameRequest(player_name=player_black)
    _ = service.join_game(str(create_response.game_id), join_request)

    # It is white to move - ask for available legal moves
    request = LegalMovesRequest(player_name=player_white)
    response = service.legal_moves(str(create_response.game_id), request)

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
    join_request = JoinGameRequest(player_name=player_black)
    _ = service.join_game(str(create_response.game_id), join_request)

    # It is white to move - ask for legal moves for player with BLACK pieces.
    with pytest.raises(BaseError):
        request = LegalMovesRequest(player_name=player_black)
        _ = service.legal_moves(str(create_response.game_id), request)


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
    with pytest.raises(BaseError):
        request = LegalMovesRequest(player_name=player_white)
        _ = service.legal_moves(str(create_response.game_id), request)


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
    join_request = JoinGameRequest(player_name=player_black)
    _ = service.join_game(str(create_response.game_id), join_request)

    # White checkmates black:
    ladder_mate = MoveRequest(
        player_name=player_white,
        from_square="h7",
        to_square="h8",
    )
    response_after_mate = service.make_move(str(create_response.game_id), ladder_mate)
    assert response_after_mate.winner == player_white

    # Game is over: Black cannot request any legal moves
    with pytest.raises(BaseError):
        request = LegalMovesRequest(player_name=player_black)

        _ = service.legal_moves(str(create_response.game_id), request)


# --- SERVICE - MAKE MOVE ---
def test_make_legal_move(mock_repository: MockRepository) -> None:
    """Attempt a legal move during your turn. Should result in a GameResponse."""
    game_name = "my-game"
    player_white = "Whitey McWhite"
    create_request = CreateGameRequest(
        game_name=game_name,
        player_name=player_white,
        color=Color.WHITE,
        starting_fen="k7/8/8/8/8/8/8/K7 w - - 8 24",
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    player_black = "Blackey McBlack"
    join_request = JoinGameRequest(player_name=player_black)
    _ = service.join_game(str(create_response.game_id), join_request)

    # make a legal move
    request = MoveRequest(
        player_name=player_white,
        from_square="a1",
        to_square="a2",
    )
    response = service.make_move(str(create_response.game_id), request)

    # Check response structure
    assert isinstance(response, GameResponse)

    # Check response data
    assert response.game_id == create_response.game_id
    assert response.fen_state == "k7/8/8/8/8/8/K7/8 b - - 9 24"
    assert response.starting_state == "k7/8/8/8/8/8/8/K7 w - - 8 24"
    assert response.move_history == ["a1a2"]
    assert response.winner is None
    assert response.game_name == game_name

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
    join_request = JoinGameRequest(player_name=player_black)
    _ = service.join_game(str(create_response.game_id), join_request)

    # Attempt an illegal move (some random squares)
    with pytest.raises(BaseError):
        request = MoveRequest(
            player_name=player_white,
            from_square="d1",
            to_square="h2",
        )
        _ = service.make_move(str(create_response.game_id), request)


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
    join_request = JoinGameRequest(player_name=player_black)
    _ = service.join_game(str(create_response.game_id), join_request)

    # White to move - Black attempts to move already
    with pytest.raises(BaseError):
        request = MoveRequest(
            player_name=player_black,
            from_square="a8",
            to_square="a7",
        )
        _ = service.make_move(str(create_response.game_id), request)


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
    with pytest.raises(BaseError):
        request = MoveRequest(
            player_name=player_white,
            from_square="a1",
            to_square="a2",
        )
        _ = service.make_move(str(create_response.game_id), request)


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
    join_request = JoinGameRequest(player_name=player_black)
    _ = service.join_game(str(create_response.game_id), join_request)

    # White checkmates black:
    ladder_mate = MoveRequest(
        player_name=player_white,
        from_square="h7",
        to_square="h8",
    )
    response_after_mate = service.make_move(str(create_response.game_id), ladder_mate)
    assert response_after_mate.winner == player_white

    # Black should no longer be able to move
    with pytest.raises(BaseError):
        request = MoveRequest(
            player_name=player_black,
            from_square="a8",
            to_square="a7",
        )
        _ = service.make_move(str(create_response.game_id), request)


def test_attempt_move_after_stalemate(mock_repository: MockRepository) -> None:
    """Service must propagate error raised by Game upwards."""

    player_white = "Whitey McWhite"
    create_request = CreateGameRequest(
        player_name=player_white,
        color=Color.WHITE,
        starting_fen="k7/6R1/7R/8/8/8/K7/8 w - - 0 1",
    )
    repository = mock_repository
    service = ChessService(repository)
    create_response = service.create_new_game(create_request)

    player_black = "Blackey McBlack"
    join_request = JoinGameRequest(player_name=player_black)
    _ = service.join_game(str(create_response.game_id), join_request)

    # White forces stalemate:
    stalemate = MoveRequest(
        player_name=player_white,
        from_square="h6",
        to_square="b6",
    )
    response_after_stalemate = service.make_move(
        str(create_response.game_id), stalemate
    )
    assert response_after_stalemate.winner is None

    # Black should no longer be able to move
    with pytest.raises(BaseError):
        request = MoveRequest(
            player_name=player_black,
            from_square="a8",
            to_square="a7",
        )
        _ = service.make_move(str(create_response.game_id), request)


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
    service.delete_game(str(create_response.game_id))

    # should no longer exist in repository
    with pytest.raises(BaseError):
        _ = service.get_game_state(str(create_response.game_id))
