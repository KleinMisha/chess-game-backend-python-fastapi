"""Helpers for implementing Castling rules. Need to be imported by multiple sources"""

from dataclasses import dataclass
from enum import Enum
from typing import Self

from src.chess.square import Square


class CastlingDirection(Enum):
    """The four castling directions. Values represent their encodings in FEN string."""

    WHITE_KING_SIDE = "K"
    WHITE_QUEEN_SIDE = "Q"
    BLACK_KING_SIDE = "k"
    BLACK_QUEEN_SIDE = "q"


@dataclass(frozen=True)
class CastlingSquares:
    """
    Store the squares where king/rook start from/end up in by castling.
    NOTE: If castling rights have not been revoked, we already know the king / rook are still at their starting squares.
    """

    king_from: Square
    king_to: Square
    rook_from: Square
    rook_to: Square

    @classmethod
    def from_algebraic(cls, k_from: str, k_to: str, r_from: str, r_to: str) -> Self:
        """Convenience method: to make mapping shown below (from CastlingDirection) more readable"""
        king_from = Square.from_algebraic(k_from)
        king_to = Square.from_algebraic(k_to)
        rook_from = Square.from_algebraic(r_from)
        rook_to = Square.from_algebraic(r_to)
        return cls(king_from, king_to, rook_from, rook_to)


# The moves (in classical chess) made when castling
CASTLING_RULES: dict[CastlingDirection, CastlingSquares] = {
    CastlingDirection.WHITE_KING_SIDE: CastlingSquares.from_algebraic(
        "e1", "g1", "h1", "f1"
    ),
    CastlingDirection.WHITE_QUEEN_SIDE: CastlingSquares.from_algebraic(
        "e1", "c1", "a1", "d1"
    ),
    CastlingDirection.BLACK_KING_SIDE: CastlingSquares.from_algebraic(
        "e8", "g8", "h8", "f8"
    ),
    CastlingDirection.BLACK_QUEEN_SIDE: CastlingSquares.from_algebraic(
        "e8", "c8", "a8", "d8"
    ),
}
