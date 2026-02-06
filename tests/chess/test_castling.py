"""unit tests for src/chess/castling.py"""

from src.chess.castling import CastlingSquares, Square


def test_castling_squares_creation() -> None:
    """Test one case, just to have a little contract stating: 'I want to be able to create this dataclass'"""
    castling_squares = CastlingSquares.from_algebraic("e1", "g1", "h1", "f1")
    assert castling_squares.king_from == Square.from_algebraic("e1")
    assert castling_squares.king_to == Square.from_algebraic("g1")
    assert castling_squares.rook_from == Square.from_algebraic("h1")
    assert castling_squares.rook_to == Square.from_algebraic("f1")
