"""
Geometry/Base movement and capturing/attacking rules

Key idea: Use strategy pattern to define legal move sets for each piece type.


Legality is checked later by Game
"""

from dataclasses import dataclass
from typing import Callable, Optional, Protocol, Self

from src.chess.castling import CastlingDirection, CastlingSquares
from src.chess.pieces import FEN_TO_PIECE, PIECE_TO_FEN, Color, Piece, PieceType
from src.chess.square import BOARD_DIMENSIONS, Square


class Board(Protocol):
    """Just the parts the movement strategies need"""

    def piece(self, square: Square) -> Piece: ...
    def empty_squares(self) -> list[Square]: ...


Vector = tuple[int, int]


@dataclass
class Move:
    """basic definition of a move to be made"""

    from_square: Square
    to_square: Square
    promote_to: Optional[PieceType] = None
    castling_direction: Optional[CastlingDirection] = None
    is_en_passant: bool = False

    @classmethod
    def from_uci(cls, uci: str) -> Self:
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
            move.promote_to = FEN_TO_PIECE[uci[4]]
        return move

    def to_uci(self) -> str:
        """Convert into UCI notation"""
        piece_char = PIECE_TO_FEN[self.promote_to] if self.promote_to else ""
        return f"{self.from_square.to_algebraic()}{self.to_square.to_algebraic()}{piece_char}"


# --- MOVEMENT RULES ---
def raycasting_move(
    square: Square, board: Board, directions: list[Vector]
) -> list[Move]:
    """
    Raycasting algorithm
    -----

    ---
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


def single_step_move(square: Square, board: Board, deltas: list[Vector]) -> list[Move]:
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
    pawn_push: list[Vector] = (
        [(0, 1)] if board.piece(square).color == Color.WHITE else [(0, -1)]
    )
    moves.extend(single_step_move(square, board, pawn_push))

    # pawns take diagonally:
    pawn_takes: list[Vector] = (
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
    knight_deltas: list[Vector] = [
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
    diagonals: list[Vector] = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    return raycasting_move(square, board, diagonals)


def candidate_rook_moves(square: Square, board: Board) -> list[Move]:
    """Rooks move either horizontally or vertically"""
    stay_on_rank = [(1, 0), (-1, 0)]
    stay_on_file = [(0, 1), (0, -1)]
    horizontal_moves = raycasting_move(square, board, stay_on_rank)
    vertical_moves = raycasting_move(square, board, stay_on_file)
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

    Castling is modelled as a special king move (handled separately).
    """
    king_deltas: list[Vector] = [
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


# -- STRATEGY PATTERN: MOVEMENT RULES ---
CandidateMovesFn = Callable[[Square, Board], list[Move]]
MOVEMENT_RULES: dict[PieceType, CandidateMovesFn] = {
    PieceType.PAWN: candidate_pawn_moves,
    PieceType.KNIGHT: candidate_knight_moves,
    PieceType.BISHOP: candidate_bishop_moves,
    PieceType.ROOK: candidate_rook_moves,
    PieceType.QUEEN: candidate_queen_moves,
    PieceType.KING: candidate_king_moves,
}


# --- CAPTURING RULES / ATTACKING RULES ---
def raycasting_attack(
    square: Square,
    by_color: Color,
    by_piece_type: PieceType,
    board: Board,
    directions: list[Vector],
) -> bool:
    """
    Raycasting algorithm for attacks.
    ---

    ---
    Similar to raycasting moves.
    However, where `raycasting_move()` determines
    _"What is the line-of-sight of the piece standing on the specified square?"_


    This function determines:
    _"Is the piece standing on the specified square in the line-of-sight of a piece of the specified color and that
    is allowed to move along the given direction?"_


    We define move directions and move along them until we hit another piece or
    the edge of the board.

    ---
    Returns TRUE if the piece encountered is an opponent's piece or the specified type.
    """

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
                # only need to find the first occupied square found if it is the opponent's: then your piece is under attack.
                piece_found = board.piece(target_square)
                if (piece_found.color == by_color) and (
                    piece_found.type == by_piece_type
                ):
                    return True
                break
    return False


def single_step_attack(
    square: Square,
    by_color: Color,
    by_piece_type: PieceType,
    board: Board,
    deltas: list[Vector],
) -> bool:
    """
    Raycasting is for sliding pieces. This is the equivalent for pawns, kings, and knights that just can move a single step along a direction.
    Hence, they also can only attack along a single direction.

    ---
    Returns TRUE if the piece encountered is an opponent's piece or the specified type.
    """
    for df, dr in deltas:
        new_file = square.file + df
        new_rank = square.rank + dr
        target_square = Square(new_file, new_rank)
        if not target_square.is_within_bounds():
            continue

        # NOTE: PieceType and Color already include the case of an empty square (so 'piece found in the broad sense here')
        piece_found = board.piece(target_square)
        if (piece_found.color == by_color) and (piece_found.type == by_piece_type):
            return True
        continue

    return False


def is_attacked_by_pawn(square: Square, by_color: Color, board: Board) -> bool:
    """
    Pawns take diagonally
    ----

    NOTE: Pawn moves are not symmetric, so to check IF a white pawn could move into your square -->
    Must look one rank DOWN the board. That is, you are asking "Could a white pawn, that moves UP the board, take on the specified square?"

    Hence, vectors are exactly opposite to the ones used to check if you could move to a square by taking (see `candidate_pawn_moves()`)
    """
    inverse_pawn_take_deltas: list[Vector] = (
        [(1, -1), (-1, -1)] if by_color == Color.WHITE else [(1, 1), (-1, 1)]
    )
    return single_step_attack(
        square, by_color, PieceType.PAWN, board, inverse_pawn_take_deltas
    )


def is_attacked_by_knight(square: Square, by_color: Color, board: Board) -> bool:
    """Knights always much such that |delta_rank| + |delta_file| = 3"""
    knight_deltas: list[Vector] = [
        (2, 1),
        (2, -1),
        (-2, 1),
        (-2, -1),
        (1, 2),
        (1, -2),
        (-1, 2),
        (-1, -2),
    ]
    return single_step_attack(square, by_color, PieceType.KNIGHT, board, knight_deltas)


def is_attacked_by_bishop(square: Square, by_color: Color, board: Board) -> bool:
    """Bishops move diagonally: |delta_rank| = |delta_file|"""
    diagonals: list[Vector] = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    return raycasting_attack(square, by_color, PieceType.BISHOP, board, diagonals)


def is_attacked_by_rook(square: Square, by_color: Color, board: Board) -> bool:
    """Rooks move either horizontally or vertically"""
    horizontal = [(1, 0), (-1, 0)]
    vertical = [(0, 1), (0, -1)]
    straights: list[Vector] = horizontal + vertical
    return raycasting_attack(square, by_color, PieceType.ROOK, board, straights)


def is_attacked_by_queen(square: Square, by_color: Color, board: Board) -> bool:
    """
    The Queen combines the rook moves (horizontal + vertical movements) and bishop moves (diagonal movement)
    """
    horizontal = [(1, 0), (-1, 0)]
    vertical = [(0, 1), (0, -1)]
    straights: list[Vector] = horizontal + vertical
    diagonals: list[Vector] = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    queen_on_straight = raycasting_attack(
        square, by_color, PieceType.QUEEN, board, straights
    )
    queen_on_diagonal = raycasting_attack(
        square, by_color, PieceType.QUEEN, board, diagonals
    )
    return queen_on_straight or queen_on_diagonal


def is_attacked_by_king(square: Square, by_color: Color, board: Board) -> bool:
    """
    The king can move by a single square at the time.
    """
    king_deltas: list[Vector] = [
        (0, 1),
        (0, -1),
        (1, 0),
        (-1, 0),
        (1, 1),
        (1, -1),
        (-1, 1),
        (-1, -1),
    ]
    return single_step_attack(square, by_color, PieceType.KING, board, king_deltas)


# --- STRATEGY PATTERN: ATTACKING RULES ---
IsAttackedFn = Callable[[Square, Color, Board], bool]
ATTACK_RULES: dict[PieceType, IsAttackedFn] = {
    PieceType.PAWN: is_attacked_by_pawn,
    PieceType.KNIGHT: is_attacked_by_knight,
    PieceType.BISHOP: is_attacked_by_bishop,
    PieceType.ROOK: is_attacked_by_rook,
    PieceType.QUEEN: is_attacked_by_queen,
    PieceType.KING: is_attacked_by_king,
}


# -- CASTLING MOVES ---
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


def castling_king_squares(direction: CastlingDirection) -> tuple[Square, Square]:
    """convert the castling rule into a move of the king + the castling direction set properly"""
    rule = CASTLING_RULES[direction]
    return rule.king_from, rule.king_to


def castling_rook_squares(direction: CastlingDirection) -> tuple[Square, Square]:
    rule = CASTLING_RULES[direction]
    return rule.rook_from, rule.rook_to


def squares_between_on_rank(from_square: Square, to_square: Square) -> list[Square]:
    """
    Find the squares in between the two squares specified that are on the same rank

    Needed for checking if you can still castle (the Board will check which of those are empty etc.)

    """

    if from_square.rank != to_square.rank:
        # todo  check if worth making this a custom error. It is right in between
        # todo "expected error by invalid input" and "incorrect programming / should never happen if backend is done well"
        raise ValueError(
            f"squares_between_on_rank requires both squares to lie on the same rank. \n from: {from_square}\n to:{to_square}"
        )

    difference_in_files = to_square.file - from_square.file
    search_direction: Vector = (1, 0) if difference_in_files > 0 else (-1, 0)
    squares_found: list[Square] = []
    df, _ = search_direction
    square = from_square
    while True:
        file = square.file
        rank = square.rank
        file += df
        try_square = Square(file, rank)
        if try_square == to_square:
            break

        squares_found.append(try_square)
        square = try_square

    return squares_found


def candidate_castling_move(direction: CastlingDirection) -> Move:
    king_from, king_to = castling_king_squares(direction)
    return Move(king_from, king_to, castling_direction=direction)


# -- EN PASSANT MOVES ---
def en_passant_moves(
    en_passant_square: Square, color: Color, board: Board
) -> list[Move]:
    """Given a target en passant square, check the adjacent files (in the rank one up/down from the en passant square) for pawns of the correct color."""

    # white moves UP the board, black moves DOWN:
    # NOTE: En passant square is indication of the opponent's pawn.
    opposite_direction = -1 if color == Color.WHITE else 1

    # if there is a pawn on the adjacent file: Add this move to the list
    moves: list[Move] = []
    for df in [-1, 1]:
        maybe_pawn_square = Square(
            file=en_passant_square.file + df,
            rank=en_passant_square.rank + opposite_direction,
        )
        piece_on_square = board.piece(maybe_pawn_square)
        own_pawn = Piece(PieceType.PAWN, color)
        if piece_on_square == own_pawn:
            moves.append(
                Move(
                    from_square=maybe_pawn_square,
                    to_square=en_passant_square,
                    is_en_passant=True,
                )
            )

    return moves


# -- PAWN PROMOTION MOVES --
PROMOTION_OPTIONS: list[PieceType] = [
    PieceType.KNIGHT,
    PieceType.BISHOP,
    PieceType.ROOK,
    PieceType.QUEEN,
]


def is_pawn_push_to_promotion_square(move: Move, board: Board) -> bool:
    """check if the move is a pawn push and if it reaches either the first or the final rank"""
    moving_piece = board.piece(move.from_square)
    is_pawn_move = moving_piece.type == PieceType.PAWN
    target_square = move.to_square
    reaches_promotion_square = target_square.rank in [1, BOARD_DIMENSIONS[1]]
    return is_pawn_move and reaches_promotion_square


def pawn_pushes_w_promotion(pawn_push: Move) -> list[Move]:
    """Return multiple copies of the pawn push with the piece type to promote into filled in."""
    return [
        Move(
            from_square=pawn_push.from_square,
            to_square=pawn_push.to_square,
            promote_to=piece_type,
        )
        for piece_type in PROMOTION_OPTIONS
    ]
