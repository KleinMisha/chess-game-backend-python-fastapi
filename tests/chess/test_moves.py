"""Unit tests for /src/chess/moves.py"""

from unittest.mock import call, patch

import pytest

import src.chess.moves as mv
from src.chess.board import Board
from src.chess.moves import (
    Move,
    PieceType,
    Square,
    candidate_bishop_moves,
    candidate_king_moves,
    candidate_knight_moves,
    candidate_pawn_moves,
    candidate_queen_moves,
    candidate_rook_moves,
    raycasting,
    single_step_move,
)
from src.chess.square import BOARD_DIMENSIONS

PIECE_ON_A8 = "/".join(["r7"] + ["8"] * 8)
PIECE_ON_E5 = "/".join(["8", "8", "8", "3P4", "8", "8", "8", "8"])
EMPTY_FEN = "/".join(["8"] * 8)


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


def test_raycasting_empty_board() -> None:
    """On an empty board, movements should be unrestricted. Should only be restricted by board dimensions"""
    board = Board.from_fen(EMPTY_FEN)
    starting_square = Square.from_algebraic("a5")
    horizontal_moves = [(1, 0), (-1, 0)]
    moves = raycasting(starting_square, board, horizontal_moves)
    assert len(moves) == BOARD_DIMENSIONS[0] - 1
    assert all(move.from_square.file == starting_square.file for move in moves)

    vertical_moves = [(0, 1), (0, -1)]
    moves = raycasting(starting_square, board, vertical_moves)
    assert len(moves) == BOARD_DIMENSIONS[1] - 1
    assert all(move.from_square.rank == starting_square.rank for move in moves)


def test_raycasting_w_enemy_blocker() -> None:
    """
    When running into enemy piece, still include in list of moves

    NOTE: The piece type does not matter here, only the color.
    """
    # Pretend you are playing with the white pieces, you are a piece on d2 and the opponent has a piece on d5
    d2_white_d5_black = "/".join(["8", "8", "8", "3p4", "8", "8", "3P4", "8"])
    board = Board.from_fen(d2_white_d5_black)
    starting_square = Square.from_algebraic("d2")
    vertical_moves = [(0, 1), (0, -1)]
    moves = raycasting(starting_square, board, vertical_moves)
    uci_moves = set([move.to_uci() for move in moves])
    assert uci_moves == set(["d2d1", "d2d3", "d2d4", "d2d5"])

    # Similar test for diagonal moves (just for good measure). Enemy piece is placed on f4 (same diagonal as d2)
    d2_white_f4_black = "/".join(["8", "8", "8", "8", "5p2", "8", "3P4", "8"])
    board = Board.from_fen(d2_white_f4_black)
    starting_square = Square.from_algebraic("d2")
    diagonal_moves = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    moves = raycasting(starting_square, board, diagonal_moves)
    uci_moves = set([move.to_uci() for move in moves])
    assert uci_moves == set(["d2c1", "d2e3", "d2f4", "d2c3", "d2b4", "d2a5", "d2e1"])


def test_raycasting_w_friendly_blocker() -> None:
    """
    When your own piece is blocking, do not include a move to that square in the move list
    """
    # Pretend you are playing with the white pieces, you have pieces on d2 and d5
    d2_white_d5_white = "/".join(["8", "8", "8", "3P4", "8", "8", "3P4", "8"])
    board = Board.from_fen(d2_white_d5_white)
    starting_square = Square.from_algebraic("d2")
    vertical_moves = [(0, 1), (0, -1)]
    moves = raycasting(starting_square, board, vertical_moves)
    uci_moves = set([move.to_uci() for move in moves])
    assert uci_moves == set(["d2d1", "d2d3", "d2d4"])

    # Similar test for diagonal moves (just for good measure). You are playing with the black pieces and have pieces on d2 and f4
    d2_black_f4_black = "/".join(["8", "8", "8", "8", "5p2", "8", "3p4", "8"])
    board = Board.from_fen(d2_black_f4_black)
    starting_square = Square.from_algebraic("d2")
    diagonal_moves = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    moves = raycasting(starting_square, board, diagonal_moves)
    uci_moves = set([move.to_uci() for move in moves])
    assert uci_moves == set(["d2c1", "d2e3", "d2c3", "d2b4", "d2a5", "d2e1"])


def test_raycasting_w_mixed_blockers() -> None:
    """
    Blockers of both your own pieces (cannot move past) as well as your opponent's pieces (capture first one in sight).
    """
    # Place multiple pieces on the same rank, start walking in the middle.
    a1_black_a5_white_a7_white = "/".join(["8", "P7", "8", "P7", "8", "8", "8", "p7"])
    board = Board.from_fen(a1_black_a5_white_a7_white)
    starting_square = Square.from_algebraic("a5")
    vertical_moves = [(0, 1), (0, -1)]
    moves = raycasting(starting_square, board, vertical_moves)
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
    diagonal_moves = [(1, 1), (-1, 1), (1, -1), (-1, -1)]

    # check wiring
    with patch.object(mv, "raycasting") as mock_raycasting:
        moves = candidate_bishop_moves(d4, board)
        mock_raycasting.assert_called_once_with(d4, board, diagonal_moves)

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
    with patch.object(mv, "raycasting") as mock_raycasting:
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
    with patch.object(mv, "raycasting") as mock_raycasting:
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
