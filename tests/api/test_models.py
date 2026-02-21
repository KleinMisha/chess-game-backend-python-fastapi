from uuid import UUID, uuid4

import pytest

from src.api.models import CreateGameRequest, MoveRequest
from src.core.exceptions import InvalidRequestError
from src.core.shared_types import Color


@pytest.fixture
def mock_id() -> UUID:
    return uuid4()


# -- Validation - CreateGameRequest --
def test_valid_fen() -> None:
    """Test that CreateGameRequest accepts a valid FEN string."""

    valid_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    request = CreateGameRequest(
        player_name="don't hate the player, hate the name.",
        color=Color.BLACK,
        starting_fen=valid_fen,
    )
    assert request.starting_fen == valid_fen


def test_starting_fen_is_optional() -> None:
    """Should be able to not supply a starting FEN, and validator just returns None."""
    request = CreateGameRequest(
        player_name="don't hate the player, hate the name.",
        color=Color.BLACK,
        starting_fen=None,
    )
    assert request.starting_fen is None


@pytest.mark.parametrize(
    "invalid_fen",
    [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0",  # only 5 space-separated values
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1 extra",  # too many space-separated values
    ],
)
def test_invalid_fen(invalid_fen: str) -> None:
    """Structurally invalid FEN: more or less than 6 space-separated fields."""

    with pytest.raises(InvalidRequestError):
        _ = CreateGameRequest(
            player_name="don't hate the player, hate the name.",
            color=Color.BLACK,
            starting_fen=invalid_fen,
        )


# -- Validation - MoveRequest --
def test_valid_square_names(mock_id: UUID) -> None:
    """Test that MoveRequest accepts correctly written squares in algebraic notation."""
    e2 = "e2"
    e4 = "e4"
    request = MoveRequest(
        game_id=mock_id, player_name="bladiblidiboo", from_square=e2, to_square=e4
    )
    assert request.from_square == e2
    assert request.to_square == e4


@pytest.mark.parametrize(
    "square",
    [
        "nonsense",  # anything more than two characters.
        "11",  # First character is not a letter
        "aa",  # second character is not a number
    ],
)
def test_invalid_from_square(mock_id: UUID, square: str) -> None:
    """Test that an exception is raised when using invalid square name."""
    e2 = "e2"

    with pytest.raises(InvalidRequestError):
        _ = MoveRequest(
            game_id=mock_id,
            player_name="bladiblidiboo",
            from_square=square,
            to_square=e2,
        )


@pytest.mark.parametrize(
    "square",
    [
        "nonsense",  # anything more than two characters.
        "11",  # First character is not a letter
        "aa",  # second character is not a number
    ],
)
def test_invalid_to_square(mock_id: UUID, square: str) -> None:
    """Test that an exception is raised when using invalid square name."""
    e2 = "e2"
    with pytest.raises(InvalidRequestError):
        _ = MoveRequest(
            game_id=mock_id,
            player_name="bladiblidiboo",
            from_square=e2,
            to_square=square,
        )
