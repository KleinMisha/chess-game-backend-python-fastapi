"""Unit tests for /src/chess/moves.py"""

import pytest

from src.chess.moves import Move, PieceType, Square


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
