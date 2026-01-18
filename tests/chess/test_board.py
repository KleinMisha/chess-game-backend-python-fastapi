"""Unit tests for /src/chess/board.py"""

import pytest

from src.chess.board import Board, Color, Move, Piece, PieceType, Square

STARTING_POSITION_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
EMPTY_FEN = "/".join(["8"] * 8)


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


@pytest.mark.parametrize("uci_move", ["e2e4", "a1a5", "d2e4", "g3a7"])
def test_single_move_updates(uci_move: str) -> None:
    """Play a single move / update the board. Checks that the square it left from is set to empty and piece is now at target square

    NOTE: I am not making legal moves perse. Not the responsibility of this function to test that
    """
    board = Board.from_fen(STARTING_POSITION_FEN)
    move = Move.from_uci(uci_move)
    moving_piece = board.piece(move.from_square)
    board.apply_move(move)
    assert board.piece(move.from_square) == Piece(PieceType.EMPTY, Color.NONE)
    assert board.piece(move.to_square) == moving_piece


def test_making_a_series_of_moves() -> None:
    """Play a couple of typical moves, including taking pieces, check moves are applied correctly, material gets updated appropriately, etc."""
    board = Board.from_fen(STARTING_POSITION_FEN)
    e4_e5 = [Move.from_uci("e2e4"), Move.from_uci("d7d5")]
    board.apply_moves(e4_e5)
    e_takes_d = Move.from_uci("e4d5")
    board.apply_move(e_takes_d)
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
    board.apply_moves(more_moves)
    assert board.piece(Square.from_algebraic("d5")) == Piece(
        PieceType.QUEEN, Color.WHITE
    )
    assert all(
        board.piece(Square.from_algebraic(sq)) == Piece(PieceType.EMPTY, Color.NONE)
        for sq in ["f3", "f6", "c3", "d8"]
    )
