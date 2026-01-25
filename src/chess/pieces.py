"""Defines the types of chess pieces"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Self


class PieceType(Enum):
    EMPTY = auto()
    PAWN = auto()
    KNIGHT = auto()
    BISHOP = auto()
    ROOK = auto()
    QUEEN = auto()
    KING = auto()


class Color(Enum):
    NONE = auto()
    WHITE = auto()
    BLACK = auto()


FEN_TO_PIECE: dict[str, PieceType] = {
    "p": PieceType.PAWN,
    "n": PieceType.KNIGHT,
    "b": PieceType.BISHOP,
    "r": PieceType.ROOK,
    "q": PieceType.QUEEN,
    "k": PieceType.KING,
}

PIECE_TO_FEN: dict[PieceType, str] = {value: key for key, value in FEN_TO_PIECE.items()}


PIECE_POINTS: dict[PieceType, int] = {
    PieceType.PAWN: 1,
    PieceType.KNIGHT: 3,
    PieceType.BISHOP: 3,
    PieceType.ROOK: 5,
    PieceType.QUEEN: 9,
}


@dataclass
class Piece:
    type: PieceType
    color: Color
    points: int = field(init=False)

    def __post_init__(self):
        # NOTE: The King's worth is undefined (does not count towards total points), and an empty square should also have zero points
        self.points = PIECE_POINTS.get(self.type, 0)

    @classmethod
    def from_fen(cls, character: str) -> Self:
        # lower case: Black pieces, upper case: White pieces
        color = Color.WHITE if character.isupper() else Color.BLACK
        piece_type = FEN_TO_PIECE[character.lower()]
        return cls(piece_type, color)

    def to_fen(self) -> str:
        return (
            PIECE_TO_FEN[self.type].upper()
            if self.color == Color.WHITE
            else PIECE_TO_FEN[self.type].lower()
        )

    def promote_to(self, new_type: PieceType) -> None:
        self.type = new_type
