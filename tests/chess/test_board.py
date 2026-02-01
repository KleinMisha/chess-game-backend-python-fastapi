"""Unit tests for /src/chess/board.py"""

from contextlib import AbstractContextManager
from typing import Any, Callable, Literal
from unittest.mock import Mock, patch

import pytest

from src.chess.board import Board, Color, Move, Square
from src.chess.pieces import PIECE_TO_FEN, Piece, PieceType

STARTING_POSITION_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
EMPTY_FEN = "/".join(["8"] * 8)
PatchContext = AbstractContextManager[None]
PieceColors = Literal[Color.WHITE, Color.BLACK]


@pytest.fixture
def board_with_single_piece() -> Callable[[PieceType, PieceColors, str], Board]:
    """Call the inner function that will be returned with the desired piece type, color, and square"""

    def _create_board(
        piece_type: PieceType,
        color: PieceColors,
        square_name: str = "d4",
    ) -> Board:
        if color == Color.WHITE:
            fen_char = PIECE_TO_FEN[piece_type].upper()
        elif color == Color.BLACK:
            fen_char = PIECE_TO_FEN[piece_type].lower()

        file_idx = ord(square_name[0]) - ord("a")
        rank_idx = 8 - int(square_name[1])

        fen_rows = ["8"] * 8
        fen_rows[rank_idx] = f"{file_idx}{fen_char}{7 - file_idx}"
        fen = "/".join(fen_rows)
        return Board.from_fen(fen)

    return _create_board


@pytest.fixture
def patch_candidate_move_functions() -> Callable[
    [Any], tuple[PatchContext, dict[PieceType, Mock]]
]:
    """Call the inner method with the desired return value for all the functions"""

    def _patch_functions(
        return_value: Any,
    ) -> tuple[PatchContext, dict[PieceType, Mock]]:
        mock_rules: dict[PieceType, Mock] = {}

        for piece_type in PieceType:
            if piece_type == PieceType.EMPTY:
                continue
            mock_rules[piece_type] = Mock(return_value=return_value)

        ctx = patch.dict("src.chess.board.MOVEMENT_RULES", mock_rules)
        return ctx, mock_rules

    return _patch_functions


@pytest.fixture
def patch_attack_rule_functions() -> Callable[
    [], tuple[PatchContext, dict[PieceType, Mock]]
]:
    """Call the inner method with the desired return value for all the functions"""

    def _patch_functions() -> tuple[PatchContext, dict[PieceType, Mock]]:
        mock_rules: dict[PieceType, Mock] = {}

        for piece_type in PieceType:
            if piece_type == PieceType.EMPTY:
                continue
            # return FALSE to ensure all methods must be called (no early break out of the test for attacker)
            mock_rules[piece_type] = Mock(return_value=False)

        ctx = patch.dict("src.chess.board.ATTACK_RULES", mock_rules)
        return ctx, mock_rules

    return _patch_functions


# -- CREATION LOGIC ---
def test_creating_board_in_starting_position() -> None:
    """Make sure board position is correctly initialized using a partial FEN string

    Using the standard opening position
    """
    board = Board.from_fen(STARTING_POSITION_FEN)

    # top rank: black pieces
    assert board.piece(Square(1, 8)) == Piece(PieceType.ROOK, Color.BLACK)
    assert board.piece(Square(2, 8)) == Piece(PieceType.KNIGHT, Color.BLACK)
    assert board.piece(Square(3, 8)) == Piece(PieceType.BISHOP, Color.BLACK)
    assert board.piece(Square(4, 8)) == Piece(PieceType.QUEEN, Color.BLACK)
    assert board.piece(Square(5, 8)) == Piece(PieceType.KING, Color.BLACK)
    assert board.piece(Square(6, 8)) == Piece(PieceType.BISHOP, Color.BLACK)
    assert board.piece(Square(7, 8)) == Piece(PieceType.KNIGHT, Color.BLACK)
    assert board.piece(Square(8, 8)) == Piece(PieceType.ROOK, Color.BLACK)

    # 7th rank: black pawns
    for file in range(1, 9):
        assert board.piece(Square(file, 7)) == Piece(PieceType.PAWN, Color.BLACK)

    # 6th, 5th, 4th, 3rd ranks all empty
    for rank in range(3, 7):
        for file in range(1, 9):
            assert board.piece(Square(file, rank)) == Piece(PieceType.EMPTY, Color.NONE)

    # 2nd rank: white pawns
    for file in range(1, 9):
        assert board.piece(Square(file, 2)) == Piece(PieceType.PAWN, Color.WHITE)

    # 1st rank: white pieces
    assert board.piece(Square(1, 1)) == Piece(PieceType.ROOK, Color.WHITE)
    assert board.piece(Square(2, 1)) == Piece(PieceType.KNIGHT, Color.WHITE)
    assert board.piece(Square(3, 1)) == Piece(PieceType.BISHOP, Color.WHITE)
    assert board.piece(Square(4, 1)) == Piece(PieceType.QUEEN, Color.WHITE)
    assert board.piece(Square(5, 1)) == Piece(PieceType.KING, Color.WHITE)
    assert board.piece(Square(6, 1)) == Piece(PieceType.BISHOP, Color.WHITE)
    assert board.piece(Square(7, 1)) == Piece(PieceType.KNIGHT, Color.WHITE)
    assert board.piece(Square(8, 1)) == Piece(PieceType.ROOK, Color.WHITE)


def test_creating_board_after_e4() -> None:
    """Say, white moves the pawn from e2 to e4, and I want to load up the board in this position"""
    e4_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR"
    board = Board.from_fen(e4_fen)

    # black did not move:
    assert board.piece(Square(1, 8)) == Piece(PieceType.ROOK, Color.BLACK)
    assert board.piece(Square(2, 8)) == Piece(PieceType.KNIGHT, Color.BLACK)
    assert board.piece(Square(3, 8)) == Piece(PieceType.BISHOP, Color.BLACK)
    assert board.piece(Square(4, 8)) == Piece(PieceType.QUEEN, Color.BLACK)
    assert board.piece(Square(5, 8)) == Piece(PieceType.KING, Color.BLACK)
    assert board.piece(Square(6, 8)) == Piece(PieceType.BISHOP, Color.BLACK)
    assert board.piece(Square(7, 8)) == Piece(PieceType.KNIGHT, Color.BLACK)
    assert board.piece(Square(8, 8)) == Piece(PieceType.ROOK, Color.BLACK)

    # 7th rank: black pawns
    for file in range(1, 9):
        assert board.piece(Square(file, 7)) == Piece(PieceType.PAWN, Color.BLACK)

    # 6th and 5th rank empty
    for rank in [6, 5]:
        for file in range(1, 9):
            assert board.piece(Square(file, rank)) == Piece(PieceType.EMPTY, Color.NONE)

    # 4th rank now contains one white pawn on the e-file (the 5th file)
    for file in range(1, 9):
        if file == 5:
            continue
        assert board.piece(Square(file, 4)) == Piece(PieceType.EMPTY, Color.NONE)

    assert board.piece(Square(5, 4)) == Piece(PieceType.PAWN, Color.WHITE)

    # 3rd rank is empty
    for file in range(1, 9):
        assert board.piece(Square(file, 3)) == Piece(PieceType.EMPTY, Color.NONE)

    # 2nd rank has 7 pawns, one empty square on the e file
    for file in range(1, 9):
        if file == 5:
            continue
        assert board.piece(Square(file, 2)) == Piece(PieceType.PAWN, Color.WHITE)

    assert board.piece(Square(5, 2)) == Piece(PieceType.EMPTY, Color.NONE)

    # 1st rank still has all the white pieces in starting position:
    assert board.piece(Square(1, 1)) == Piece(PieceType.ROOK, Color.WHITE)
    assert board.piece(Square(2, 1)) == Piece(PieceType.KNIGHT, Color.WHITE)
    assert board.piece(Square(3, 1)) == Piece(PieceType.BISHOP, Color.WHITE)
    assert board.piece(Square(4, 1)) == Piece(PieceType.QUEEN, Color.WHITE)
    assert board.piece(Square(5, 1)) == Piece(PieceType.KING, Color.WHITE)
    assert board.piece(Square(6, 1)) == Piece(PieceType.BISHOP, Color.WHITE)
    assert board.piece(Square(7, 1)) == Piece(PieceType.KNIGHT, Color.WHITE)
    assert board.piece(Square(8, 1)) == Piece(PieceType.ROOK, Color.WHITE)


def test_creating_board_mid_game() -> None:
    """Create a board from a game after a bunch of random moves (incl a couple of captures and castling just for good measure)"""

    random_position = "2kr1b1r/p1p1pppp/2p2n2/3q2B1/6Q1/2NP4/PPP2PPP/R4RK1"
    board = Board.from_fen(random_position)
    assert board.piece(Square(1, 8)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(2, 8)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(3, 8)) == Piece(PieceType.KING, Color.BLACK)
    assert board.piece(Square(4, 8)) == Piece(PieceType.ROOK, Color.BLACK)
    assert board.piece(Square(5, 8)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(6, 8)) == Piece(PieceType.BISHOP, Color.BLACK)
    assert board.piece(Square(7, 8)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(8, 8)) == Piece(PieceType.ROOK, Color.BLACK)

    assert board.piece(Square(1, 7)) == Piece(PieceType.PAWN, Color.BLACK)
    assert board.piece(Square(2, 7)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(3, 7)) == Piece(PieceType.PAWN, Color.BLACK)
    assert board.piece(Square(4, 7)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(5, 7)) == Piece(PieceType.PAWN, Color.BLACK)
    assert board.piece(Square(6, 7)) == Piece(PieceType.PAWN, Color.BLACK)
    assert board.piece(Square(7, 7)) == Piece(PieceType.PAWN, Color.BLACK)
    assert board.piece(Square(8, 7)) == Piece(PieceType.PAWN, Color.BLACK)

    assert board.piece(Square(1, 6)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(2, 6)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(3, 6)) == Piece(PieceType.PAWN, Color.BLACK)
    assert board.piece(Square(4, 6)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(5, 6)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(6, 6)) == Piece(PieceType.KNIGHT, Color.BLACK)
    assert board.piece(Square(7, 6)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(8, 6)) == Piece(PieceType.EMPTY, Color.NONE)

    assert board.piece(Square(1, 5)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(2, 5)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(3, 5)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(4, 5)) == Piece(PieceType.QUEEN, Color.BLACK)
    assert board.piece(Square(5, 5)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(6, 5)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(7, 5)) == Piece(PieceType.BISHOP, Color.WHITE)
    assert board.piece(Square(8, 5)) == Piece(PieceType.EMPTY, Color.NONE)

    assert board.piece(Square(1, 4)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(2, 4)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(3, 4)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(4, 4)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(5, 4)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(6, 4)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(7, 4)) == Piece(PieceType.QUEEN, Color.WHITE)
    assert board.piece(Square(8, 4)) == Piece(PieceType.EMPTY, Color.NONE)

    assert board.piece(Square(1, 3)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(2, 3)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(3, 3)) == Piece(PieceType.KNIGHT, Color.WHITE)
    assert board.piece(Square(4, 3)) == Piece(PieceType.PAWN, Color.WHITE)
    assert board.piece(Square(5, 3)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(6, 3)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(7, 3)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(8, 3)) == Piece(PieceType.EMPTY, Color.NONE)

    assert board.piece(Square(1, 2)) == Piece(PieceType.PAWN, Color.WHITE)
    assert board.piece(Square(2, 2)) == Piece(PieceType.PAWN, Color.WHITE)
    assert board.piece(Square(3, 2)) == Piece(PieceType.PAWN, Color.WHITE)
    assert board.piece(Square(4, 2)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(5, 2)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(6, 2)) == Piece(PieceType.PAWN, Color.WHITE)
    assert board.piece(Square(7, 2)) == Piece(PieceType.PAWN, Color.WHITE)
    assert board.piece(Square(8, 2)) == Piece(PieceType.PAWN, Color.WHITE)

    assert board.piece(Square(1, 1)) == Piece(PieceType.ROOK, Color.WHITE)
    assert board.piece(Square(2, 1)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(3, 1)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(4, 1)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(5, 1)) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(Square(6, 1)) == Piece(PieceType.ROOK, Color.WHITE)
    assert board.piece(Square(7, 1)) == Piece(PieceType.KING, Color.WHITE)
    assert board.piece(Square(8, 1)) == Piece(PieceType.EMPTY, Color.NONE)


def test_creating_empty_board() -> None:
    """Board with no pieces on it"""
    board = Board.from_fen(EMPTY_FEN)
    assert all(
        board.piece(Square(file, rank)) == Piece(PieceType.EMPTY, Color.NONE)
        for file in range(1, 9)
        for rank in range(1, 9)
    )


# -- COUNTING MATERIAL --
def test_no_material_left() -> None:
    """With only the kings left, the players should have zero points of material"""
    #  empty board
    board = Board.from_fen(EMPTY_FEN)

    # place the kings somewhere manually
    board.position[Square(4, 4)] = Piece(PieceType.KING, Color.WHITE)
    board.position[Square(6, 8)] = Piece(PieceType.KING, Color.BLACK)
    assert board.count_material() == {Color.WHITE: 0, Color.BLACK: 0}


def test_starting_material() -> None:
    """Starting amount of material for each player:

    * 8 pawns = 8 pts
    * 2x rook  = 2x5 = 10 pts
    * 2x knight = 2x3 = 6 pts
    * 2x bishop = 2x3 = 6pts
    * 1x queen  = 9 pts
    -->> 39 points
    """
    board = Board.from_fen(STARTING_POSITION_FEN)
    assert board.count_material() == {Color.WHITE: 39, Color.BLACK: 39}


def test_material_mid_game() -> None:
    """Check once more when players do not have equal amount of material"""
    random_position = """r1bqk1nr/pppp1ppp/8/4b3/3nP3/8/PPP1QPPP/RNB1KB1R"""
    board = Board.from_fen(random_position)

    # White has lost one knight and one pawn
    white_points = 39 - 1 - 3
    # Black has lost just a pawn
    black_points = 39 - 1
    assert board.count_material() == {
        Color.WHITE: white_points,
        Color.BLACK: black_points,
    }


# -- LOCATING PIECES --
def test_locating_pawns() -> None:
    """Locating the pawns in the starting position"""
    board = Board.from_fen(STARTING_POSITION_FEN)
    pawns = board.locate_pieces(PieceType.PAWN)
    assert len(pawns) == 16
    assert all((square.rank == 2) or (square.rank == 7) for square in pawns)


def test_empty_pieces() -> None:
    """Locating the empty pieces. Make sure you do not find any other piece when the board is completely empty"""
    board = Board.from_fen(EMPTY_FEN)
    empty_squares = board.empty_squares()
    assert len(empty_squares) == 64
    assert len(empty_squares) == len(board.position)

    # check you do not find any other piece (spot check)
    assert len(board.locate_pieces(PieceType.ROOK)) == 0
    assert len(board.locate_pieces(PieceType.PAWN)) == 0
    assert len(board.locate_pieces(PieceType.QUEEN)) == 0


@pytest.mark.parametrize("player_color", [Color.WHITE, Color.BLACK])
def test_locating_color(player_color: Color) -> None:
    """Locate all pieces (incl. pawns) in the starting position"""
    opponent_color = Color.WHITE if player_color == Color.BLACK else Color.BLACK
    board = Board.from_fen(STARTING_POSITION_FEN)
    player_pieces = board.locate_color(player_color)
    assert len(player_pieces) == 16
    assert all(board.piece(square).color == player_color for square in player_pieces)
    assert not any(
        (board.piece(square).color == opponent_color)
        or (board.piece(square).color == Color.NONE)
        for square in player_pieces
    )


@pytest.mark.parametrize(
    "color, king_square",
    [(color, sq) for color in [Color.BLACK, Color.WHITE] for sq in ["a1", "d4", "d8"]],
)
def test_finding_the_king(color: PieceColors, king_square: str) -> None:
    """Make sure you locate the king of the specified color at the correct location"""

    # set up the board with the king on the correct location
    board = Board.from_fen(EMPTY_FEN)
    expected_square = Square.from_algebraic(king_square)
    expected_king = Piece(PieceType.KING, color)
    board.place_piece(expected_king, expected_square)

    # add the other piece at some other location
    h8 = Square.from_algebraic("h8")
    opposite_color = Color.WHITE if color == Color.BLACK else Color.BLACK
    wrong_king = Piece(PieceType.KING, opposite_color)
    board.place_piece(wrong_king, h8)

    # add some additional decoys on the board
    f3 = Square.from_algebraic("f3")
    f2 = Square.from_algebraic("f2")
    a2 = Square.from_algebraic("a2")
    black_pawn = Piece.from_fen("p")
    white_bishop = Piece.from_fen("B")
    white_queen = Piece.from_fen("Q")
    board.place_piece(black_pawn, f3)
    board.place_piece(white_bishop, f2)
    board.place_piece(white_queen, a2)

    # locate the king
    found_square = board.king_square(color)
    assert found_square == expected_square

    # make sure it is the actual piece we intend to find
    found_piece = board.piece(found_square)
    assert found_piece == expected_king


# --- PIECE MOVEMENTS / BOARD UPDATES ---
@pytest.mark.parametrize("uci_move", ["e2e4", "a1a5", "d2e4", "g3a7"])
def test_single_move_updates(uci_move: str) -> None:
    """Play a single move / update the board. Checks that the square it left from is set to empty and piece is now at target square

    NOTE: I am not making legal moves perse. Not the responsibility of this function to test that
    """
    board = Board.from_fen(STARTING_POSITION_FEN)
    move = Move.from_uci(uci_move)
    moving_piece = board.piece(move.from_square)
    board.move_piece(move)
    assert board.piece(move.from_square) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(move.to_square) == moving_piece


def test_making_a_series_of_moves() -> None:
    """Play a couple of typical moves, including taking pieces, check moves are applied correctly, material gets updated appropriately, etc."""
    board = Board.from_fen(STARTING_POSITION_FEN)
    e4_e5 = [Move.from_uci("e2e4"), Move.from_uci("d7d5")]
    board.move_pieces(e4_e5)
    e_takes_d = Move.from_uci("e4d5")
    board.move_piece(e_takes_d)
    assert board.count_material() == {Color.WHITE: 39, Color.BLACK: 38}
    assert board.piece(Square.from_algebraic("d5")) == Piece(
        PieceType.PAWN, Color.WHITE
    )
    assert board.piece(Square.from_algebraic("e4")) == Piece(
        PieceType.EMPTY, Color.NONE
    )

    # a series of takes on the same square
    more_moves = [
        Move.from_uci("c8f5"),
        Move.from_uci("b1c3"),
        Move.from_uci("g8f6"),
        Move.from_uci("d1f3"),
        Move.from_uci("d8d5"),
        Move.from_uci("c3d5"),
        Move.from_uci("f6d5"),
        Move.from_uci("f3d5"),
    ]
    board.move_pieces(more_moves)
    assert board.piece(Square.from_algebraic("d5")) == Piece(
        PieceType.QUEEN, Color.WHITE
    )
    assert all(
        board.piece(Square.from_algebraic(sq)) == Piece(PieceType.EMPTY, Color.NONE)
        for sq in ["f3", "f6", "c3", "d8"]
    )


@pytest.mark.parametrize(
    "color, piece_type",
    [
        (c, pt)
        for c in [Color.WHITE, Color.BLACK]
        for pt in PieceType
        if pt != PieceType.EMPTY
    ],
)
def test_generating_candidate_moves(
    color: PieceColors,
    piece_type: PieceType,
    board_with_single_piece: Callable[[PieceType, PieceColors, str], Board],
    patch_candidate_move_functions: Callable[
        [Any], tuple[PatchContext, dict[PieceType, Mock]]
    ],
) -> None:
    """Test strategy pattern is implemented properly. Checks you only called the correct function and no other."""
    board: Board = board_with_single_piece(piece_type, color, "d4")

    expected_return: list[str] = [f"{piece_type.name.lower()}_move_list"]
    patch_ctx, mock_fns = patch_candidate_move_functions(expected_return)
    with patch_ctx:
        actual_return = board.generate_candidate_moves(color)
        assert actual_return == expected_return

        for pt in PieceType:
            if pt == PieceType.EMPTY:
                continue
            if pt == piece_type:
                mock_fns[pt].assert_called_once()
            else:
                mock_fns[pt].assert_not_called()


# -- ATTACK DETECTION --
@pytest.mark.parametrize("color", [Color.WHITE, Color.BLACK])
def test_attack_detection(
    color: PieceColors,
    patch_attack_rule_functions: Callable[
        [], tuple[PatchContext, dict[PieceType, Mock]]
    ],
) -> None:
    """Test strategy pattern is implemented properly. Checks you attempt attack detection for every piece type once."""

    # on an empty board we should for sure call all the strategies
    board = Board.from_fen(EMPTY_FEN)
    a1 = Square.from_algebraic("a1")
    patch_ctx, mock_fns = patch_attack_rule_functions()
    with patch_ctx:
        board.is_square_attacked(a1, color)

        for pt in PieceType:
            print(pt)
            if pt == PieceType.EMPTY:
                continue
            mock_fns[pt].assert_called_once()


@pytest.mark.parametrize("color", [Color.WHITE, Color.BLACK])
def test_check_detection(color: PieceColors) -> None:
    """Make sure Board.is_check() calls the correct methods. Attack detection logic already tested."""

    board = Board.from_fen(EMPTY_FEN)
    opposite_color = Color.BLACK if color == Color.WHITE else Color.WHITE
    with (
        patch.object(board, attribute="is_square_attacked") as mock_attack_detection,
        patch.object(
            board, attribute="king_square", return_value="king_square"
        ) as mock_king_finder,
    ):
        board.is_check(color)
        mock_king_finder.assert_called_once_with(color)
        mock_attack_detection.assert_called_once_with("king_square", opposite_color)


# -- ENCODING BOARD IN FEN --
@pytest.mark.parametrize(
    "fen",
    [
        STARTING_POSITION_FEN,
        EMPTY_FEN,
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
        "2kr1b1r/p1p1pppp/2p2n2/3q2B1/6Q1/2NP4/PPP2PPP/R4RK1",
    ],
)
def test_writing_board_to_fen(fen: str) -> None:
    """Check if parsing the dictionary of pieces correctly converted back into the FEN string"""
    board = Board.from_fen(fen)
    assert board.to_fen() == fen
