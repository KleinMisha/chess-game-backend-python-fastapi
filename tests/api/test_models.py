import pytest

from src.api.models import CreateGameRequest
from src.core.exceptions import InvalidRequestError
from src.core.shared_types import Color


def test_valid_fen() -> None:
    """happy path: using a structurally valid FEN"""
    valid_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    request = CreateGameRequest(
        player_name="don't hate the player, hate the name.",
        color=Color.BLACK,
        starting_fen=valid_fen,
    )
    assert request.starting_fen == valid_fen


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
