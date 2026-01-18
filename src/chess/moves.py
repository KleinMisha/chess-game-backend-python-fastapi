"""

Calculating legal moves. Here is where most of the the rules of chess are encoded

Key idea: Use strategy pattern to define legal move sets for each piece type.

"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Optional, Protocol

from src.chess.pieces import PIECE_FEN, Color, Piece, PieceType
from src.chess.square import Square


class CastlingDirection(Enum):
    """Rights will be revoked during the game. Enum prevents silly typos/ inconsistent naming later in the application."""

    WHITE_KING_SIDE = auto()
    WHITE_QUEEN_SIDE = auto()
    BLACK_KING_SIDE = auto()
    BLACK_QUEEN_SIDE = auto()


class Board(Protocol):
    """Just the parts the movement strategies need"""

    def piece(self, square: Square) -> Piece: ...
    def empty_squares(self) -> list[Square]: ...


@dataclass
class Move:
    """basic definition of a move to be made"""

    from_square: Square
    to_square: Square
    promote_to: Optional[PieceType] = None
    castle: Optional[CastlingDirection] = None
    is_en_passant: bool = False

    @classmethod
    def from_uci(cls, uci: str) -> Move:
        """
        Universal Chess Interface:
        ---
        ---
        One of the standard chess notations for moves

        examples:
        * "e2e5": move the piece that was on e4 to e5
        * "e7e8q" : (pawn) moves from e7 to e8 and promotes to a queen (the q)
        * "e1g1": the king moved from

        NOTE: Castling / En Passant will be set later by Game class
        """
        from_sq = Square.from_algebraic(uci[:2])
        to_sq = Square.from_algebraic(uci[2:4])
        move = cls(from_sq, to_sq)
        if len(uci) == 5:
            move.promote_to = PIECE_FEN[uci[4]]
        return move

    def to_uci(self) -> str:
        """Convert into UCI notation"""
        piece_char = next((k for k, v in PIECE_FEN.items() if v == self.promote_to), "")
        return f"{self.from_square.to_algebraic()}{self.to_square.to_algebraic()}{piece_char}"


def raycasting(
    square: Square, board: Board, directions: list[tuple[int, int]]
) -> list[Move]:
    """
    The main trick we use to check the 'line of sight of a piece'.
    We define move directions and move along them until we hit another piece or
    the edge of the board.

    ---
    Algorithm is supposed to be O(N) and the main method chess engines use.
    """

    player_color = board.piece(square).color
    opponent_color = Color.WHITE if player_color == Color.BLACK else Color.BLACK

    moves: list[Move] = []
    empty_squares = board.empty_squares()
    for df, dr in directions:
        file = square.file
        rank = square.rank
        while True:
            file += df
            rank += dr
            target_square = Square(file, rank)
            if not target_square.is_within_bounds():
                break

            if target_square not in empty_squares:
                # only need to add the first occupied square found if it is the opponent's: then it can be captured.
                if board.piece(target_square).color == opponent_color:
                    moves.append(Move(from_square=square, to_square=target_square))
                break

            moves.append(Move(from_square=square, to_square=target_square))
    return moves


def single_step_move(
    square: Square, board: Board, deltas: list[tuple[int, int]]
) -> list[Move]:
    """Raycasting is for sliding pieces. This is the equivalent for pawns, kings, and knights that just can move a single step along a direction"""
    moves: list[Move] = []
    for df, dr in deltas:
        new_file = square.file + df
        new_rank = square.rank + dr
        target_square = Square(new_file, new_rank)
        if not target_square.is_within_bounds():
            continue

        player_color = board.piece(square).color
        square_available = board.piece(target_square).color != player_color
        if square_available:
            moves.append(Move(from_square=square, to_square=target_square))

    return moves


def candidate_pawn_moves(square: Square, board: Board) -> list[Move]:
    """
    A pawn:
    - moves by a single square forward.
    - It can move by two in their first move (so when on their starting rank)
    - takes diagonally

    NOTE: En passant will be taken care of in the Game class
    """
    moves: list[Move] = []
    # Pawn pushes : Black moves down the board, White moves up the board
    pawn_push = [(0, 1)] if board.piece(square).color == Color.WHITE else [(0, -1)]
    moves.extend(single_step_move(square, board, pawn_push))

    # pawns take diagonally:
    pawn_takes = (
        [(1, 1), (-1, 1)]
        if board.piece(square).color == Color.WHITE
        else [(1, -1), (-1, -1)]
    )
    for df, dr in pawn_takes:
        new_file = square.file + df
        new_rank = square.rank + dr
        target_square = Square(new_file, new_rank)
        player_color = board.piece(square).color
        opponent_color = Color.WHITE if player_color == Color.BLACK else Color.BLACK
        is_opponent_piece = board.piece(target_square).color == opponent_color

        if target_square.is_within_bounds() and is_opponent_piece:
            moves.append(Move(from_square=square, to_square=target_square))
    return moves


def candidate_knight_moves(square: Square, board: Board) -> list[Move]:
    """Knights always much such that |delta_rank| + |delta_file| = 3"""
    knight_deltas = [
        (2, 1),
        (2, -1),
        (-2, 1),
        (-2, -1),
        (1, 2),
        (1, -2),
        (-1, 2),
        (-1, -2),
    ]
    return single_step_move(square, board, knight_deltas)


def candidate_bishop_moves(square: Square, board: Board) -> list[Move]:
    """Bishops move diagonally: |delta_rank| = |delta_file|"""
    diagonals = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    return raycasting(square, board, diagonals)


def candidate_rook_moves(square: Square, board: Board) -> list[Move]:
    """Rooks move either horizontally or vertically"""
    stay_on_rank = [(1, 0), (-1, 0)]
    stay_on_file = [(0, 1), (0, -1)]
    horizontal_moves = raycasting(square, board, stay_on_rank)
    vertical_moves = raycasting(square, board, stay_on_file)
    return horizontal_moves + vertical_moves


def candidate_queen_moves(square: Square, board: Board) -> list[Move]:
    """
    The Queen combines the rook moves (horizontal + vertical movements) and bishop moves (diagonal movement)
    """
    diagonal_moves = candidate_bishop_moves(square, board)
    horizontal_and_vertical_moves = candidate_rook_moves(square, board)
    return diagonal_moves + horizontal_and_vertical_moves


def candidate_king_moves(square: Square, board: Board) -> list[Move]:
    """
    The king can move by a single square at the time.

    Castling is modelled as a special king move.
    """
    king_deltas = [
        (0, 1),
        (0, -1),
        (1, 0),
        (-1, 0),
        (1, 1),
        (1, -1),
        (-1, 1),
        (-1, -1),
    ]
    return single_step_move(square, board, king_deltas)


# Strategy pattern:
CandidateMovesFn = Callable[[Square, Board], list[Move]]
MOVEMENT_RULES: dict[PieceType, CandidateMovesFn] = {
    PieceType.PAWN: candidate_pawn_moves,
    PieceType.KNIGHT: candidate_knight_moves,
    PieceType.BISHOP: candidate_bishop_moves,
    PieceType.ROOK: candidate_rook_moves,
    PieceType.QUEEN: candidate_queen_moves,
    PieceType.KING: candidate_king_moves,
}
