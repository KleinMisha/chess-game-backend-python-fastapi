"""
Type definitions used across layers
"""

from enum import StrEnum


class Status(StrEnum):
    WAITING_FOR_PLAYERS = "waiting for players"
    IN_PROGRESS = "in progress"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    DRAW_REPETITION = "draw by repetition"
    DRAW_FIFTY_HALF_MOVE_RULE = "draw by 50 half-moves"


# --- Color and PieceType DO NOT contain options for empty squares. Moved that to src/chess/squares.py
# --- # TODO refactor Piece class to accept Optional[PieceType] and Optional[Color], then should change some of the checks/logic in moves.py. But hopefully doable
# --- NOTE For now, just use the same names (Color and PieceType) as that reads clearly and let the imports show which versions are used in what part of the code


class Color(StrEnum):
    WHITE = "white"
    BLACK = "black"


class PieceType(StrEnum):
    PAWN = "pawn"
    KNIGHT = "knight"
    BISHOP = "bishop"
    ROOK = "rook"
    QUEEN = "queen"
    KING = "king"
