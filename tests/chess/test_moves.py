"""Unit tests for /src/chess/moves.py"""

from unittest.mock import call, patch

import pytest

import src.chess.moves as mv
from src.chess.board import Board
from src.chess.moves import (
    Color,
    Move,
    Piece,
    PieceType,
    Square,
    candidate_bishop_moves,
    candidate_king_moves,
    candidate_knight_moves,
    candidate_pawn_moves,
    candidate_queen_moves,
    candidate_rook_moves,
    is_attacked_by_bishop,
    is_attacked_by_king,
    is_attacked_by_knight,
    is_attacked_by_pawn,
    is_attacked_by_queen,
    is_attacked_by_rook,
    raycasting_attack,
    raycasting_move,
    single_step_attack,
    single_step_move,
    squares_between_on_rank,
)
from src.chess.square import BOARD_DIMENSIONS

PIECE_ON_A8 = "/".join(["r7"] + ["8"] * 8)
PIECE_ON_E5 = "/".join(["8", "8", "8", "3P4", "8", "8", "8", "8"])
EMPTY_FEN = "/".join(["8"] * 8)


# -- MOVE CREATION, ENCODING/DECODING UCI NOTATION ---
@pytest.mark.parametrize(
    "uci_move, from_uci, to_uci",
    [
        ("e2e4", "e2", "e4"),
        ("a1a5", "a1", "a5"),
        ("d2e4", "d2", "e4"),
        ("g3a7", "g3", "a7"),
    ],
)
def test_creating_move_from_uci(uci_move: str, from_uci: str, to_uci: str) -> None:
    """Creating logic / parsing of UCI notation for the move should be <from_square><to_square>"""
    move = Move.from_uci(uci_move)
    expected_starting_square = Square.from_algebraic(from_uci)
    expected_target_square = Square.from_algebraic(to_uci)
    assert move.from_square == expected_starting_square
    assert move.to_square == expected_target_square


@pytest.mark.parametrize(
    "uci_move, from_uci, to_uci",
    [
        ("e2e4", "e2", "e4"),
        ("a1a5", "a1", "a5"),
        ("d2e4", "d2", "e4"),
        ("g3a7", "g3", "a7"),
    ],
)
def test_converting_into_uci(uci_move: str, from_uci: str, to_uci: str) -> None:
    """Test parsing the move into a UCI denoted move."""
    from_square = Square.from_algebraic(from_uci)
    to_square = Square.from_algebraic(to_uci)
    move = Move(from_square, to_square)
    assert move.to_uci() == uci_move


def test_creating_move_incl_promotion() -> None:
    """Creation logic including promotion"""
    move = Move.from_uci("e7e8q")
    assert move.from_square == Square.from_algebraic("e7")
    assert move.to_square == Square.from_algebraic("e8")
    assert move.promote_to == PieceType.QUEEN


def test_converting_into_uci_incl_promotion() -> None:
    """Test inverse operation of creating UCI denoted move back"""
    move = Move.from_uci("e7e8q")
    assert move.to_uci() == "e7e8q"


# --- MOVEMENT RULES ---
def test_raycasting_move_empty_board() -> None:
    """On an empty board, movements should be unrestricted. Should only be restricted by board dimensions"""
    board = Board.from_fen(EMPTY_FEN)
    starting_square = Square.from_algebraic("a5")
    horizontal_moves = [(1, 0), (-1, 0)]
    moves = raycasting_move(starting_square, board, horizontal_moves)
    assert len(moves) == BOARD_DIMENSIONS[0] - 1
    assert all(move.from_square.file == starting_square.file for move in moves)

    vertical_moves = [(0, 1), (0, -1)]
    moves = raycasting_move(starting_square, board, vertical_moves)
    assert len(moves) == BOARD_DIMENSIONS[1] - 1
    assert all(move.from_square.rank == starting_square.rank for move in moves)


def test_raycasting_move_w_enemy_blocker() -> None:
    """
    When running into enemy piece, still include in list of moves

    NOTE: The piece type does not matter here, only the color.
    """
    # Pretend you are playing with the white pieces, you are a piece on d2 and the opponent has a piece on d5
    d2_white_d5_black = "/".join(["8", "8", "8", "3p4", "8", "8", "3P4", "8"])
    board = Board.from_fen(d2_white_d5_black)
    starting_square = Square.from_algebraic("d2")
    vertical_moves = [(0, 1), (0, -1)]
    moves = raycasting_move(starting_square, board, vertical_moves)
    uci_moves = set([move.to_uci() for move in moves])
    assert uci_moves == set(["d2d1", "d2d3", "d2d4", "d2d5"])

    # Similar test for diagonal moves (just for good measure). Enemy piece is placed on f4 (same diagonal as d2)
    d2_white_f4_black = "/".join(["8", "8", "8", "8", "5p2", "8", "3P4", "8"])
    board = Board.from_fen(d2_white_f4_black)
    starting_square = Square.from_algebraic("d2")
    diagonal_moves = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    moves = raycasting_move(starting_square, board, diagonal_moves)
    uci_moves = set([move.to_uci() for move in moves])
    assert uci_moves == set(["d2c1", "d2e3", "d2f4", "d2c3", "d2b4", "d2a5", "d2e1"])


def test_raycasting_move_w_friendly_blocker() -> None:
    """
    When your own piece is blocking, do not include a move to that square in the move list
    """
    # Pretend you are playing with the white pieces, you have pieces on d2 and d5
    d2_white_d5_white = "/".join(["8", "8", "8", "3P4", "8", "8", "3P4", "8"])
    board = Board.from_fen(d2_white_d5_white)
    starting_square = Square.from_algebraic("d2")
    vertical_moves = [(0, 1), (0, -1)]
    moves = raycasting_move(starting_square, board, vertical_moves)
    uci_moves = set([move.to_uci() for move in moves])
    assert uci_moves == set(["d2d1", "d2d3", "d2d4"])

    # Similar test for diagonal moves (just for good measure). You are playing with the black pieces and have pieces on d2 and f4
    d2_black_f4_black = "/".join(["8", "8", "8", "8", "5p2", "8", "3p4", "8"])
    board = Board.from_fen(d2_black_f4_black)
    starting_square = Square.from_algebraic("d2")
    diagonal_moves = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    moves = raycasting_move(starting_square, board, diagonal_moves)
    uci_moves = set([move.to_uci() for move in moves])
    assert uci_moves == set(["d2c1", "d2e3", "d2c3", "d2b4", "d2a5", "d2e1"])


def test_raycasting_move_w_mixed_blockers() -> None:
    """
    Blockers of both your own pieces (cannot move past) as well as your opponent's pieces (capture first one in sight).
    """
    # Place multiple pieces on the same rank, start walking in the middle.
    a1_black_a5_white_a7_white = "/".join(["8", "P7", "8", "P7", "8", "8", "8", "p7"])
    board = Board.from_fen(a1_black_a5_white_a7_white)
    starting_square = Square.from_algebraic("a5")
    vertical_moves = [(0, 1), (0, -1)]
    moves = raycasting_move(starting_square, board, vertical_moves)
    uci_moves = set([move.to_uci() for move in moves])
    assert uci_moves == set(["a5a4", "a5a3", "a5a2", "a5a1", "a5a6"])


def test_single_move_in_bounds() -> None:
    """
    Allow for a move that keeps you within bounds
    NOTE: piece type does not matter for testing this logic (only color w.r.t other squares matters)
    """
    d4_white = "/".join(["8", "8", "8", "8", "3P4", "8", "8", "8"])
    board = Board.from_fen(d4_white)
    step = [(-2, 4)]
    d4 = Square.from_algebraic("d4")
    moves = single_step_move(d4, board, step)
    assert len(moves) == 1
    assert moves[0].to_uci() == "d4b8"


def test_single_move_out_of_bounds() -> None:
    """Attempt to move your piece outside of the board: Should return empty list"""
    d4_white = "/".join(["8", "8", "8", "8", "3P4", "8", "8", "8"])
    board = Board.from_fen(d4_white)
    step = [(42, 23)]  # something ridiculous that for sure is too large of a step
    d4 = Square.from_algebraic("d4")
    moves = single_step_move(d4, board, step)
    assert len(moves) == 0


def test_single_step_w_enemy_blocker() -> None:
    """Move to a location that includes opponents piece"""
    d4_white_d5_black = "/".join(["8", "8", "8", "3p4", "3P4", "8", "8", "8"])
    board = Board.from_fen(d4_white_d5_black)
    step = [(0, 1)]
    d4 = Square.from_algebraic("d4")
    moves = single_step_move(d4, board, step)
    assert len(moves) == 1
    assert moves[0].to_uci() == "d4d5"

    # Check reverse case, just for good measure
    d5 = Square.from_algebraic("d5")
    step = [(0, -1)]
    moves = single_step_move(d5, board, step)
    assert len(moves) == 1
    assert moves[0].to_uci() == "d5d4"


def test_single_step_w_friendly_blocker() -> None:
    """Cannot go to a square already occupied by your own piece"""
    d4_white_d5_white = "/".join(["8", "8", "8", "3P4", "3P4", "8", "8", "8"])
    board = Board.from_fen(d4_white_d5_white)
    step = [(0, 1)]
    d4 = Square.from_algebraic("d4")
    moves = single_step_move(d4, board, step)
    assert len(moves) == 0

    # Check once using opposite colored pieces, to be sure.
    d4_black_d5_black = "/".join(["8", "8", "8", "3p4", "3p4", "8", "8", "8"])
    board = Board.from_fen(d4_black_d5_black)
    step = [(0, 1)]
    d4 = Square.from_algebraic("d4")
    moves = single_step_move(d4, board, step)
    assert len(moves) == 0


def test_candidate_bishop_moves() -> None:
    """
    Test methods are called correctly

    NOTE: It technically does not matter what type of piece I will place on the board. This wiring is handled before entering this function.
    """
    d4_white = "/".join(["8", "8", "8", "8", "3B4", "8", "8", "8"])
    board = Board.from_fen(d4_white)
    d4 = Square.from_algebraic("d4")
    diagonal_moves = [(1, 1), (1, -1), (-1, 1), (-1, -1)]

    # check wiring
    with patch.object(mv, "raycasting_move") as mock_raycasting:
        moves = candidate_bishop_moves(d4, board)
        args, _ = mock_raycasting.call_args
        assert args[0] == d4
        assert args[1] == board
        assert set(args[2]) == set(diagonal_moves)

    # check behavior: make sure no typo in directions
    moves = candidate_bishop_moves(d4, board)
    assert len(moves) == 13


def test_candidate_rook_moves() -> None:
    """
    Test methods are called correctly

    NOTE: It technically does not matter what type of piece I will place on the board. This wiring is handled before entering this function.
    """
    d4_white = "/".join(["8", "8", "8", "8", "3R4", "8", "8", "8"])
    board = Board.from_fen(d4_white)
    d4 = Square.from_algebraic("d4")
    horizontal_moves = [(0, 1), (0, -1)]
    vertical_moves = [(1, 0), (-1, 0)]

    # check wiring
    with patch.object(mv, "raycasting_move") as mock_raycasting:
        moves = candidate_rook_moves(d4, board)
        mock_raycasting.assert_has_calls(
            [call(d4, board, horizontal_moves), call(d4, board, vertical_moves)],
            any_order=True,
        )

    # check behavior: make sure no typo in directions
    moves = candidate_rook_moves(d4, board)
    assert len(moves) == 14


def test_candidate_queen_moves() -> None:
    """
    Test methods are called correctly

    NOTE: It technically does not matter what type of piece I will place on the board. This wiring is handled before entering this function.
    """
    d4_white = "/".join(["8", "8", "8", "8", "3Q4", "8", "8", "8"])
    board = Board.from_fen(d4_white)
    d4 = Square.from_algebraic("d4")
    horizontal_moves = [(0, 1), (0, -1)]
    vertical_moves = [(1, 0), (-1, 0)]
    diagonal_moves = [(1, 1), (-1, 1), (1, -1), (-1, -1)]

    # check wiring
    with patch.object(mv, "raycasting_move") as mock_raycasting:
        moves = candidate_queen_moves(d4, board)
        mock_raycasting.assert_has_calls(
            [
                call(d4, board, horizontal_moves),
                call(d4, board, vertical_moves),
                call(d4, board, diagonal_moves),
            ],
            any_order=True,
        )

    # check behavior: make sure no typo in directions
    moves = candidate_queen_moves(d4, board)
    assert len(moves) == 27


def test_candidate_knight_moves() -> None:
    """
    Test methods are called correctly

    NOTE: It technically does not matter what type of piece I will place on the board. This wiring is handled before entering this function.
    """
    d4_white = "/".join(["8", "8", "8", "8", "3N4", "8", "8", "8"])
    board = Board.from_fen(d4_white)
    d4 = Square.from_algebraic("d4")
    L_shaped = [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]

    # check wiring
    with patch.object(mv, "single_step_move") as mock_single_step:
        moves = candidate_knight_moves(d4, board)
        mock_single_step.assert_called_once_with(d4, board, L_shaped)

    # check behavior: make sure no typo in directions
    moves = candidate_knight_moves(d4, board)
    assert len(moves) == 8


def test_candidate_king_moves() -> None:
    """
    Test methods are called correctly

    NOTE: It technically does not matter what type of piece I will place on the board. This wiring is handled before entering this function.
    """
    d4_white = "/".join(["8", "8", "8", "8", "3K4", "8", "8", "8"])
    board = Board.from_fen(d4_white)
    d4 = Square.from_algebraic("d4")
    adjacent_squares = [
        (0, 1),
        (0, -1),
        (1, 0),
        (-1, 0),
        (1, 1),
        (1, -1),
        (-1, 1),
        (-1, -1),
    ]

    # check wiring
    with patch.object(mv, "single_step_move") as mock_single_step:
        moves = candidate_king_moves(d4, board)
        mock_single_step.assert_called_once_with(d4, board, adjacent_squares)

    # check behavior: make sure no typo in directions
    moves = candidate_king_moves(d4, board)
    assert len(moves) == 8


def test_white_pawn_push() -> None:
    """white pawns move up the board"""
    d4_white = "/".join(["8", "8", "8", "8", "3P4", "8", "8", "8"])
    board = Board.from_fen(d4_white)
    d4 = Square.from_algebraic("d4")
    up_the_board = [(0, 1)]

    # check wiring
    with patch.object(mv, "single_step_move") as mock_single_step:
        moves = candidate_pawn_moves(d4, board)
        mock_single_step.assert_called_once_with(d4, board, up_the_board)

    # check behavior: make sure no typo in directions
    moves = candidate_pawn_moves(d4, board)
    assert len(moves) == 1
    assert moves[0].to_uci() == "d4d5"


def test_black_pawn_push() -> None:
    """black pawns move down the board"""
    d4_black = "/".join(["8", "8", "8", "8", "3p4", "8", "8", "8"])
    board = Board.from_fen(d4_black)
    d4 = Square.from_algebraic("d4")
    down_the_board = [(0, -1)]

    # check wiring
    with patch.object(mv, "single_step_move") as mock_single_step:
        moves = candidate_pawn_moves(d4, board)
        mock_single_step.assert_called_once_with(d4, board, down_the_board)

    # check behavior: make sure no typo in directions
    moves = candidate_pawn_moves(d4, board)
    assert len(moves) == 1
    assert moves[0].to_uci() == "d4d3"


def test_white_pawn_takes() -> None:
    """Include enemy pawn on diagonal squares"""
    d4_white_e5_c5_e3_c3_black = "/".join(
        ["8", "8", "8", "2p1p3", "3P4", "2p1p3", "8", "8"]
    )
    board = Board.from_fen(d4_white_e5_c5_e3_c3_black)
    d4 = Square.from_algebraic("d4")

    # make sure ONLY the diagonals on the correct rank are included
    moves = candidate_pawn_moves(d4, board)
    uci_moves = set([move.to_uci() for move in moves])
    assert len(moves) == 3
    assert uci_moves == set(["d4d5", "d4e5", "d4c5"])


def test_black_pawn_takes() -> None:
    """Include enemy pawn on diagonal squares"""
    d4_black_e5_c5_e3_c3_white = "/".join(
        ["8", "8", "8", "2P1P3", "3p4", "2P1P3", "8", "8"]
    )
    board = Board.from_fen(d4_black_e5_c5_e3_c3_white)
    d4 = Square.from_algebraic("d4")

    # make sure ONLY the diagonals on the correct rank are included
    moves = candidate_pawn_moves(d4, board)
    uci_moves = set([move.to_uci() for move in moves])
    assert len(moves) == 3
    assert uci_moves == set(["d4d3", "d4e3", "d4c3"])


# --- ATTACK RULES ---
def test_raycasting_attack_empty_board() -> None:
    """Sanity check: with the board empty, no square should be under attack."""
    board = Board.from_fen(EMPTY_FEN)
    a5 = Square.from_algebraic("a5")
    on_same_file = [(1, 0), (-1, 0)]
    on_same_rank = [(0, 1), (0, -1)]
    diagonals = [(1, 1), (-1, 1), (1, -1), (-1, -1)]

    assert not raycasting_attack(a5, Color.WHITE, PieceType.ROOK, board, on_same_file)
    assert not raycasting_attack(a5, Color.BLACK, PieceType.ROOK, board, on_same_rank)
    assert not raycasting_attack(a5, Color.WHITE, PieceType.ROOK, board, diagonals)
    assert not raycasting_attack(a5, Color.BLACK, PieceType.PAWN, board, on_same_rank)


def test_raycasting_attack_w_attacker_on_same_file() -> None:
    """
    Black rook on A8 should be able to attack squares on the a-file, or on the 8th rank.
    Test that raycasting algorithm correctly finds the enemy piece on the file, that is of the correct type and color.
    """
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    a5 = Square.from_algebraic("a5")

    # attacker
    black_rook = Piece.from_fen("r")
    a8 = Square.from_algebraic("a8")
    board.place_piece(black_rook, a8)

    on_same_rank = [(1, 0), (-1, 0)]
    on_same_file = [(0, 1), (0, -1)]

    # a5 is under attack by a8:
    assert raycasting_attack(a5, Color.BLACK, PieceType.ROOK, board, on_same_file)

    # a5 is not under attack by anything on the 5th rank
    assert not raycasting_attack(a5, Color.BLACK, PieceType.ROOK, board, on_same_rank)

    # a5 is under attack by a BLACK rook
    assert not raycasting_attack(a5, Color.WHITE, PieceType.ROOK, board, on_same_file)

    # a5 is under attack by a black ROOK
    assert not raycasting_attack(a5, Color.BLACK, PieceType.QUEEN, board, on_same_file)


def test_raycasting_attack_w_blocker_on_same_file() -> None:
    """
    Block the attack by placing an additional friendly piece in between the attacker and the first piece.
    """
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    a5 = Square.from_algebraic("a5")

    # attacker
    black_rook = Piece.from_fen("r")
    a8 = Square.from_algebraic("a8")
    board.place_piece(black_rook, a8)

    # blocker
    white_rook = Piece.from_fen("R")
    a6 = Square.from_algebraic("a6")
    board.place_piece(white_rook, a6)
    on_same_file = [(0, 1), (0, -1)]

    # a8 cannot attack a5 due to blocker on a6:
    assert not raycasting_attack(a5, Color.BLACK, PieceType.ROOK, board, on_same_file)


def test_raycasting_attack_w_attacker_on_same_rank() -> None:
    """
    Check raycasting correctly identifies an attacker located on the same rank
    NOTE: Piece type does not matter for this unit test
    """
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    a5 = Square.from_algebraic("a5")

    # attacker
    black_rook = Piece.from_fen("r")
    e5 = Square.from_algebraic("e5")
    board.place_piece(black_rook, e5)

    on_same_rank = [(1, 0), (-1, 0)]
    # a5 attacked by piece on the same rank (e5)
    assert raycasting_attack(a5, Color.BLACK, PieceType.ROOK, board, on_same_rank)


def test_raycasting_attack_w_blocker_on_same_rank() -> None:
    """
    Block the attack by placing an additional friendly piece in between the attacker and the first piece.
    """
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    a5 = Square.from_algebraic("a5")

    # attacker
    black_rook = Piece.from_fen("r")
    e5 = Square.from_algebraic("e5")
    board.place_piece(black_rook, e5)

    # blocker
    white_pawn = Piece.from_fen("P")
    c5 = Square.from_algebraic("c5")
    board.place_piece(white_pawn, c5)
    on_same_rank = [(1, 0), (-1, 0)]

    # e5 cannot attack a5 due to blocker on c5:
    assert not raycasting_attack(a5, Color.BLACK, PieceType.ROOK, board, on_same_rank)


def test_raycasting_attack_w_attacker_on_same_diagonal() -> None:
    """
    Check raycasting correctly identifies an attacker located on the same diagonal
    NOTE: Piece type does not matter for this unit test
    """
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    a1 = Square.from_algebraic("a1")

    # attacker
    black_rook = Piece.from_fen("r")
    e5 = Square.from_algebraic("e5")
    board.place_piece(black_rook, e5)

    diagonals = [(1, 1), (-1, 1), (-1, 1), (-1, -1)]
    # Enemy piece e5 sees a1 on the same diagonal
    assert raycasting_attack(a1, Color.BLACK, PieceType.ROOK, board, diagonals)


def test_raycasting_attack_w_blocker_on_same_diagonal() -> None:
    """
    Block the attack by placing an additional friendly piece in between the attacker and the first piece.
    """
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    a1 = Square.from_algebraic("a1")

    # attacker
    black_rook = Piece.from_fen("r")
    e5 = Square.from_algebraic("e5")
    board.place_piece(black_rook, e5)

    # blocker
    white_bishop = Piece.from_fen("B")
    c3 = Square.from_algebraic("c3")
    board.place_piece(white_bishop, c3)

    diagonals = [(1, 1), (-1, 1), (-1, 1), (-1, -1)]
    # Enemy piece e5 no longer sees a1  because of piece in between them on the same diagonal
    assert not raycasting_attack(a1, Color.BLACK, PieceType.ROOK, board, diagonals)


def test_raycasting_attack_wrong_color() -> None:
    """Check that raycasting checks for the piece color."""
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    a5 = Square.from_algebraic("a5")

    # attacker
    black_rook = Piece.from_fen("r")
    a8 = Square.from_algebraic("a8")
    board.place_piece(black_rook, a8)

    on_same_file = [(0, 1), (0, -1)]

    # a5 is under attack by a BLACK rook
    assert not raycasting_attack(a5, Color.WHITE, PieceType.ROOK, board, on_same_file)


def test_raycasting_attack_wrong_piece_type() -> None:
    """Check that raycasting checks for the piece type."""
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    a5 = Square.from_algebraic("a5")

    # attacker
    black_rook = Piece.from_fen("r")
    a8 = Square.from_algebraic("a8")
    board.place_piece(black_rook, a8)

    on_same_file = [(0, 1), (0, -1)]

    # a5 is under attack by a BLACK rook
    assert not raycasting_attack(a5, Color.WHITE, PieceType.PAWN, board, on_same_file)
    assert not raycasting_attack(a5, Color.WHITE, PieceType.BISHOP, board, on_same_file)
    assert not raycasting_attack(a5, Color.WHITE, PieceType.KNIGHT, board, on_same_file)


def test_single_step_attack() -> None:
    """
    Find the attacker
    NOTE: piece type does not matter for testing this logic (only color w.r.t other squares matters)
    """

    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    c2 = Square.from_algebraic("c2")

    # attacker
    black_rook = Piece.from_fen("r")
    a6 = Square.from_algebraic("a6")
    board.place_piece(black_rook, a6)

    step = [(-2, 4)]
    assert single_step_attack(c2, Color.BLACK, PieceType.ROOK, board, step)


def test_single_step_attack_blocker_does_not_matter() -> None:
    """
    As this function will be used only for PAWNS/KINGS (that move to adjacent squares) and knights (which are allowed to jump over pieces)
    blocker should not matter.
    NOTE: Again tested this with an artificial attacking rule
    """
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    c2 = Square.from_algebraic("c2")

    # attacker
    black_rook = Piece.from_fen("r")
    a2 = Square.from_algebraic("a2")
    board.place_piece(black_rook, a2)

    # "blocker"
    white_rook = Piece.from_fen("R")
    b2 = Square.from_algebraic("b2")
    board.place_piece(white_rook, b2)

    step = [(-2, 0)]
    assert single_step_attack(c2, Color.BLACK, PieceType.ROOK, board, step)


def test_single_step_attack_wrong_color() -> None:
    """Check attacker must be of specified color"""
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    c2 = Square.from_algebraic("c2")

    # attacker
    black_rook = Piece.from_fen("r")
    a2 = Square.from_algebraic("a2")
    board.place_piece(black_rook, a2)

    step = [(-2, 0)]
    assert not single_step_attack(c2, Color.WHITE, PieceType.ROOK, board, step)


def test_single_step_attack_wrong_piece_type() -> None:
    """Check attacker must be of specified piece type"""
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    c2 = Square.from_algebraic("c2")

    # attacker
    black_rook = Piece.from_fen("r")
    a2 = Square.from_algebraic("a2")
    board.place_piece(black_rook, a2)

    step = [(-2, 0)]
    assert not single_step_attack(c2, Color.BLACK, PieceType.PAWN, board, step)
    assert not single_step_attack(c2, Color.BLACK, PieceType.BISHOP, board, step)
    assert not single_step_attack(c2, Color.BLACK, PieceType.QUEEN, board, step)


def test_bishop_attack() -> None:
    """
    Test methods are called correctly + bishops take diagonally
    """
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    a1 = Square.from_algebraic("a1")

    # attacker
    black_rook = Piece.from_fen("b")
    e5 = Square.from_algebraic("e5")
    board.place_piece(black_rook, e5)

    diagonals = [(1, 1), (1, -1), (-1, 1), (-1, -1)]

    # check wiring and logic for good measure
    with patch.object(mv, "raycasting_attack") as mock_raycasting:
        is_attacked_by_bishop(a1, Color.BLACK, board)
        mock_raycasting.assert_called_once()

        args, _ = mock_raycasting.call_args
        assert args[0] == a1
        assert args[1] == Color.BLACK
        assert args[2] == PieceType.BISHOP
        assert args[3] == board
        assert set(args[4]) == set(diagonals)

    # ensure behavior is correct:
    assert is_attacked_by_bishop(a1, Color.BLACK, board)


def test_rook_attack() -> None:
    """Test methods are called correctly + rooks take either horizontally or vertically"""

    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    a1 = Square.from_algebraic("a1")

    # attacker
    black_rook = Piece.from_fen("r")
    e1 = Square.from_algebraic("e1")
    board.place_piece(black_rook, e1)

    on_same_file = [(0, 1), (0, -1)]
    on_same_rank = [(-1, 0), (1, 0)]
    straights = on_same_file + on_same_rank
    with patch.object(mv, "raycasting_attack") as mock_raycasting:
        is_attacked_by_rook(a1, Color.BLACK, board)
        mock_raycasting.assert_called_once()
        args, _ = mock_raycasting.call_args
        assert args[0] == a1
        assert args[1] == Color.BLACK
        assert args[2] == PieceType.ROOK
        assert args[3] == board
        assert set(args[4]) == set(straights)

    # ensure behavior is correct:
    assert is_attacked_by_rook(a1, Color.BLACK, board)


def test_queen_attack() -> None:
    """Test methods are called correctly + Queens can take like rooks and like bishops"""

    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    a1 = Square.from_algebraic("a1")

    # attacker
    black_queen = Piece.from_fen("q")
    e1 = Square.from_algebraic("e1")
    board.place_piece(black_queen, e1)

    on_same_file = [(0, 1), (0, -1)]
    on_same_rank = [(1, 0), (-1, 0)]
    diagonals = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    straights = on_same_rank + on_same_file
    with patch.object(mv, "raycasting_attack") as mock_raycasting:
        is_attacked_by_queen(a1, Color.BLACK, board)
        mock_raycasting.assert_called()
        assert mock_raycasting.call_count <= 2
        if mock_raycasting.call_count == 2:
            mock_raycasting.assert_has_calls(
                [
                    call(a1, Color.BLACK, PieceType.QUEEN, board, diagonals),
                    call(a1, Color.BLACK, PieceType.QUEEN, board, straights),
                ],
                any_order=True,
            )
        elif mock_raycasting.call_count == 1:
            args, _ = mock_raycasting.call_args
            assert args[0] == a1
            assert args[1] == Color.BLACK
            assert args[2] == PieceType.QUEEN
            assert args[3] == board
            assert set(args[4]) == set(straights + diagonals)

    # ensure behavior is correct:
    assert is_attacked_by_queen(a1, Color.BLACK, board)


def test_knight_attack() -> None:
    """Test methods are called correctly + knights take moving in L-shapes"""
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    a1 = Square.from_algebraic("a1")

    # attacker
    black_knight = Piece.from_fen("n")
    b3 = Square.from_algebraic("b3")
    board.place_piece(black_knight, b3)

    L_shaped = [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]

    # check wiring
    with patch.object(mv, "single_step_attack") as mock_single_step:
        is_attacked_by_knight(a1, Color.BLACK, board)
        mock_single_step.assert_called_once_with(
            a1, Color.BLACK, PieceType.KNIGHT, board, L_shaped
        )

    # ensure behavior is correct:
    assert is_attacked_by_knight(a1, Color.BLACK, board)


def test_king_attack() -> None:
    """Test methods are called correctly + king can take on adjacent square."""
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    a1 = Square.from_algebraic("a1")

    # attacker
    black_king = Piece.from_fen("k")
    b2 = Square.from_algebraic("b2")
    board.place_piece(black_king, b2)

    adjacent_squares = [
        (0, 1),
        (0, -1),
        (1, 0),
        (-1, 0),
        (1, 1),
        (1, -1),
        (-1, 1),
        (-1, -1),
    ]

    # check wiring
    with patch.object(mv, "single_step_attack") as mock_single_step:
        is_attacked_by_king(a1, Color.BLACK, board)
        mock_single_step.assert_called_once_with(
            a1, Color.BLACK, PieceType.KING, board, adjacent_squares
        )

    # ensure behavior is correct:
    assert is_attacked_by_king(a1, Color.BLACK, board)


def test_white_pawn_attack() -> None:
    """Test methods are called correctly + white pawns take diagonally while moving UP the board"""
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    c3 = Square.from_algebraic("c3")

    # attacker
    white_pawn = Piece.from_fen("P")
    b2 = Square.from_algebraic("b2")
    board.place_piece(white_pawn, b2)

    white_pawn_take = [(-1, 1), (1, 1)]
    inverse_takes = [(f * -1, r * -1) for (f, r) in white_pawn_take]

    # check wiring
    with patch.object(mv, "single_step_attack") as mock_single_step:
        is_attacked_by_pawn(c3, Color.WHITE, board)
        mock_single_step.assert_called_once_with(
            c3, Color.WHITE, PieceType.PAWN, board, inverse_takes
        )

    # ensure behavior is correct:
    assert is_attacked_by_pawn(c3, Color.WHITE, board)


def test_black_pawn_attack() -> None:
    """Test methods are called correctly + white pawns take diagonally while moving UP the board"""
    board = Board.from_fen(EMPTY_FEN)

    # square under investigation
    c3 = Square.from_algebraic("c3")

    # attacker
    black_pawn = Piece.from_fen("p")
    d4 = Square.from_algebraic("d4")
    board.place_piece(black_pawn, d4)

    black_pawn_take = [(-1, -1), (1, -1)]
    inverse_takes = [(f * -1, r * -1) for (f, r) in black_pawn_take]

    # check wiring
    with patch.object(mv, "single_step_attack") as mock_single_step:
        is_attacked_by_pawn(c3, Color.BLACK, board)
        mock_single_step.assert_called_once_with(
            c3, Color.BLACK, PieceType.PAWN, board, inverse_takes
        )

    # ensure behavior is correct:
    assert is_attacked_by_pawn(c3, Color.BLACK, board)


# -- CASTLING RULES --


def test_squares_between_on_rank_higher_rank() -> None:
    """check the algorithm correctly identifies the squares to the right"""
    a1 = Square.from_algebraic("a1")
    b1 = Square.from_algebraic("b1")
    c1 = Square.from_algebraic("c1")
    d1 = Square.from_algebraic("d1")
    e1 = Square.from_algebraic("e1")
    f1 = Square.from_algebraic("f1")
    g1 = Square.from_algebraic("g1")
    h1 = Square.from_algebraic("h1")

    # first check from board edge to board edge
    squares_found = squares_between_on_rank(a1, h1)
    assert len(squares_found) == 6
    assert set(squares_found) == {b1, c1, d1, e1, f1, g1}

    # now check for two intermediate squares
    squares_found = squares_between_on_rank(b1, e1)
    assert len(squares_found) == 2
    assert set(squares_found) == {c1, d1}


def test_squares_between_rank_lower_rank() -> None:
    """check the algorithm correctly identifies the squares to the left"""
    a1 = Square.from_algebraic("a1")
    b1 = Square.from_algebraic("b1")
    c1 = Square.from_algebraic("c1")
    d1 = Square.from_algebraic("d1")
    e1 = Square.from_algebraic("e1")
    f1 = Square.from_algebraic("f1")
    g1 = Square.from_algebraic("g1")
    h1 = Square.from_algebraic("h1")

    # first check from board edge to board edge
    squares_found = squares_between_on_rank(h1, a1)
    assert len(squares_found) == 6
    assert set(squares_found) == {b1, c1, d1, e1, f1, g1}

    # now check for two intermediate squares
    squares_found = squares_between_on_rank(g1, d1)
    assert len(squares_found) == 2
    assert set(squares_found) == {e1, f1}


def test_squares_between_symmetry() -> None:
    """Squares between a and b should also be squares between b and a."""

    b6 = Square.from_algebraic("b6")
    g6 = Square.from_algebraic("g6")

    b_to_g = squares_between_on_rank(b6, g6)
    g_to_b = squares_between_on_rank(g6, b6)
    assert set(b_to_g) == set(g_to_b)


def test_no_squares_between_adjacent_files() -> None:
    """Two adjacent squares have no intervening square(s)."""
    a8 = Square.from_algebraic("a8")
    b8 = Square.from_algebraic("b8")
    squares_found = squares_between_on_rank(a8, b8)
    assert squares_found == []


def test_between_squares_on_rank_invalid() -> None:
    """Squares not on the same rank? Should raise a ValueError"""
    a8 = Square.from_algebraic("a8")
    c5 = Square.from_algebraic("c5")
    with pytest.raises(ValueError):
        squares_between_on_rank(a8, c5)
