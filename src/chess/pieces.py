"""Defines the types of chess pieces"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class PieceType(Enum):
    EMPTY = auto()
    PAWN = auto()
    KNIGHT = auto()
    BISHOP = auto()
    ROOK = auto()
    QUEEN = auto()
    KING = auto()


class Color(Enum):
    NONE = ""
    WHITE = "w"
    BLACK = "b"


PIECE_FEN: dict[str, PieceType] = {
    "p": PieceType.PAWN,
    "n": PieceType.KNIGHT,
    "b": PieceType.BISHOP,
    "r": PieceType.ROOK,
    "q": PieceType.QUEEN,
    "k": PieceType.KING,
}

# NOTE: The king is of course worth infinite points, it is worth the entire game, but does not count towards point totals usually reported
PIECE_POINTS: dict[PieceType, int] = {
    PieceType.PAWN: 1,
    PieceType.KNIGHT: 3,
    PieceType.BISHOP: 3,
    PieceType.ROOK: 5,
    PieceType.QUEEN: 9,
    PieceType.KING: 0,
}


@dataclass
class Piece:
    type: PieceType
    color: Color
    points: int = field(init=False)

    def __post_init__(self):
        self.points = PIECE_POINTS[self.type]

    @classmethod
    def from_fen(cls, character: str) -> Piece:
        # lower case: Black pieces, upper case: White pieces
        color = Color.WHITE if character.isupper() else Color.BLACK
        piece_type = PIECE_FEN[character.lower()]
        return cls(piece_type, color)

    def promote_to(self, new_type: PieceType) -> None:
        self.type = new_type
