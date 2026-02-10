"""
Representation of a single state of a chess game. The part that can be encoded in a FEN string.
"""

from __future__ import annotations

from dataclasses import dataclass
from string import ascii_lowercase
from typing import Optional, Self

from src.chess.castling import CastlingDirection
from src.chess.pieces import FEN_TO_PIECE, Color
from src.chess.square import BOARD_DIMENSIONS, Square
from src.core.exceptions import InvalidFENError

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
VALID_CASTLING_ENCODINGS = [
    "-",
    "K",
    "Q",
    "k",
    "q",
    "KQ",
    "Kk",
    "Kq",
    "Qk",
    "Qq",
    "kq",
    "KQk",
    "KQq",
    "Kkq",
    "Qkq",
    "KQkq",
]


CASTLING_ENCODING_ORDER: tuple[CastlingDirection, ...] = (
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
        [
            direction.value
            for direction in CASTLING_ENCODING_ORDER
            if castling_rights[direction]
        ]
    )
    return castling_chars or "-"


def is_valid_fen(fen: str) -> bool:
    """
    Check if given string follows proper FEN notation.
    """

    # there should be 6 parts to the string
    parts = fen.split(" ")
    if len(parts) != 6:
        return False

    position = parts[0]
    if not is_valid_position(position):
        return False

    color = parts[1]
    if not is_valid_color_code(color):
        return False

    castling = parts[2]
    if not is_valid_castling_rights(castling):
        return False

    en_passant = parts[3]
    if not is_valid_en_passant(en_passant):
        return False

    half_move_counter = parts[4]
    full_move_counter = parts[5]
    if not (
        is_valid_move_counter(half_move_counter)
        and is_valid_move_counter(full_move_counter)
    ):
        return False
    return True


def is_valid_position(position: str) -> bool:
    """Only check the part of the FEN encoding for the board position."""
    num_files, num_ranks = BOARD_DIMENSIONS
    rank_fens = position.split("/")
    if len(rank_fens) != num_ranks:
        return False

    for rank_fen in rank_fens:
        file_count = 0
        for character in rank_fen:
            # make sure every character is valid
            if character.isdigit():
                file_count += int(character)
            elif character.lower() in FEN_TO_PIECE:
                file_count += 1
            else:
                # immediately invalidate if the character is anything else
                return False

        # make sure you are creating a correctly sized board
        if file_count != num_files:
            return False
    return True


def is_valid_color_code(color: str) -> bool:
    return color in {"w", "b"}


def is_valid_castling_rights(castling: str) -> bool:
    """A valid castling encoding has either KQkq, KQk, etc. or a '-' if all rights have been revoked."""
    return castling in VALID_CASTLING_ENCODINGS


def is_valid_en_passant(en_passant: str) -> bool:
    """Valid en passant square encoding should be a square that exists on the board or a '-'"""
    return (en_passant == "-") or is_valid_square(en_passant)


def is_valid_square(square: str) -> bool:
    """Valid square should be a letter for the file + a number for the rank"""
    num_files, num_ranks = BOARD_DIMENSIONS

    # NOTE: The following works as long as we do not go beyond 26 files. Seems like a reasonable assumption for now ;-)
    file_char, rank_char = square[0], square[1:]
    allowed_file_names = ascii_lowercase[:num_files]
    if file_char not in allowed_file_names:
        return False

    if not rank_char.isdigit():
        return False

    if not (1 <= int(rank_char) <= num_ranks):
        return False

    return True


def is_valid_move_counter(counter: str) -> bool:
    return counter.isdigit()


@dataclass
class FENState:
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

        # raise an exception if invalid FEN:
        if not is_valid_fen(fen):
            raise InvalidFENError(f"Cannot interpret supplied string as FEN: {fen}")

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

    @classmethod
    def starting_position(cls) -> Self:
        return cls.from_fen(STARTING_FEN)

    def revoke_castling_rights(self, direction: CastlingDirection) -> None:
        """
        Revoke the right to castle in the given direction.
        ----
        NOTE: Chess doesn't allow a player to regain these rights for the remainder of the game
        """
        self.castling_rights[direction] = False

    def revoke_all_castling_rights(self, color: Color) -> None:
        """Revoke both directions"""
        castling_options = self.castling_options(color)
        for direction in castling_options:
            self.revoke_castling_rights(direction)

    def can_castle(self, color: Color) -> bool:
        """Check at least one of the castling options for the specified color are possible"""
        castling_options = self.castling_options(color)
        return any(self.castling_rights[direction] for direction in castling_options)

    def reset_half_move_counter(self) -> None:
        """Convenience method"""
        self.half_move_clock = 0

    def increment_half_move_counter(self) -> None:
        """Convenience method"""
        self.half_move_clock += 1

    def increment_full_move_counter(self) -> None:
        """Convenience method"""
        self.num_turns += 1

    def castling_options(self, color: Color) -> list[CastlingDirection]:
        """the castling directions corresponding to a particular color"""
        return [
            direction
            for direction in CastlingDirection
            if color.name.lower() in direction.name.lower()
        ]

    def is_same_position(self, other: FENState) -> bool:
        """
        Test if another FEN state is considered the same with regards to the three-fold repetition rule.
        ---

        Three fold repetition checks:
        * board position
        * turn player (color to move)
        * castling rights
        * en passant square

        That is, everything _except_ the turn counter and half move clock.
        """
        return self._repetition_key() == other._repetition_key()

    def _repetition_key(self) -> tuple[str, str, str, str]:
        """Create tuple of the information needed to determine if this position has repeated itself during a game."""
        color_str = self.color_to_move.name.lower()[0]
        castling_str = castling_to_fen(self.castling_rights)
        en_passant_str = (
            self.en_passant_square.to_algebraic() if self.en_passant_square else "-"
        )

        return (self.position, color_str, castling_str, en_passant_str)
