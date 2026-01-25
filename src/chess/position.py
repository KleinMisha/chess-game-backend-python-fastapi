"""
Representation of a single position on the board. The part that can be encoded in a FEN string.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Self

from src.chess.pieces import Color
from src.chess.square import Square


class CastlingDirection(Enum):
    """Rights will be revoked during the game. Enum prevents silly typos/ inconsistent naming later in the application."""

    WHITE_KING_SIDE = "K"
    WHITE_QUEEN_SIDE = "Q"
    BLACK_KING_SIDE = "k"
    BLACK_QUEEN_SIDE = "q"


CASTLING_ORDER: tuple[CastlingDirection, ...] = (
    CastlingDirection.WHITE_KING_SIDE,
    CastlingDirection.WHITE_QUEEN_SIDE,
    CastlingDirection.BLACK_KING_SIDE,
    CastlingDirection.BLACK_QUEEN_SIDE,
)


def castling_from_fen(castle_fen: str) -> dict[CastlingDirection, bool]:
    """parse the part of the FEN string that encodes castling rights"""
    return {
        direction: (direction.value in castle_fen) for direction in CastlingDirection
    }


def castling_to_fen(castling_rights: dict[CastlingDirection, bool]) -> str:
    """create the part of the FEN string that encodes castling rights"""
    castling_chars = "".join(
        [direction.value for direction in CASTLING_ORDER if castling_rights[direction]]
    )
    return castling_chars or "-"


@dataclass
class PositionState:
    """
    Data that can be constructed from a FEN string.
    ----

    FEN, or Forsyth-Edwards Notation, is a standard notation for describing a particular board position of a chess game.
    The purpose of FEN is to provide all the necessary information to restart a game from a particular position.

    <board position string><active color><castling rights><en passant square><# half move clock><number turns played>

    * The string to describe the board position is described in the Board class
    * The active color is either "w" or "b"
    * Castling rights are denoted as "k" for king-side or "q" for queen-side. Capital letters for the white pieces, small letters for the black pieces.
        In the starting position: KQkq (all rights available), and as rights get revoked a "-" is used instead of the designated letter.
    * The en passant square indicates the square a piece can move to / take on. If not available a "-" is used.
    * The half move clock count the number of moves made since the last pawn move or capture. (Used for a rule that says a draw is reached when this number reaches 50)
    * The number of turns starts at 1 and increments after every move black makes.

    ex) The standard starting position has a FEN
    rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
    i.e. it is white to move, all castling options available, no en passant square, no half moves and we are in the first turn.
    """

    position: str
    color_to_move: Color
    castling_rights: dict[CastlingDirection, bool]
    en_passant_square: Optional[Square]
    half_move_clock: int
    num_turns: int

    @classmethod
    def from_fen(cls, fen: str) -> Self:
        """Parse the FEN into data"""
        # extract the different components. FEN is space separated
        (
            position,
            active_color,
            castling_str,
            en_passant_algebraic,
            half_move_clock,
            num_turns,
        ) = fen.split(" ")

        # Check which color is to move
        color_to_move = Color.WHITE if active_color == "w" else Color.BLACK

        # check the castling rights. Basically just check for "-", as the order in which it gets notated is always the same
        castling_rights = castling_from_fen(castling_str)

        # parse en passant target square
        en_passant_square = (
            Square.from_algebraic(en_passant_algebraic)
            if en_passant_algebraic != "-"
            else None
        )

        # convert the turn counts into integers
        half_move_clock = int(half_move_clock)
        num_turns = int(num_turns)
        return cls(
            position,
            color_to_move,
            castling_rights,
            en_passant_square,
            half_move_clock,
            num_turns,
        )

    def to_fen(self) -> str:
        """reverse operation: write a FEN from the given data"""
        active_color = "w" if self.color_to_move == Color.WHITE else "b"
        castling_str = castling_to_fen(self.castling_rights)

        en_passant_algebraic = (
            self.en_passant_square.to_algebraic()
            if self.en_passant_square is not None
            else "-"
        )
        half_move_clock = str(self.half_move_clock)
        num_turns = str(self.num_turns)

        fen = f"{self.position} {active_color} {castling_str} {en_passant_algebraic} {half_move_clock} {num_turns}"
        return fen
