"""Unit tests for /src/chess/pieces.py"""

import pytest

from src.chess.pieces import PIECE_FEN, Color, Piece


@pytest.mark.parametrize("char", [char.upper() for char in PIECE_FEN.keys()])
def test_creating_white_piece_from_fen(char: str) -> None:
    """Capital letters are used for white pieces"""
    piece = Piece.from_fen(char)
    assert piece.type == PIECE_FEN[char.lower()]
    assert piece.color == Color.WHITE


@pytest.mark.parametrize("char", [char.lower() for char in PIECE_FEN.keys()])
def test_creating_black_piece_from_fen(char: str) -> None:
    """Lower case letters are used for white pieces"""
    piece = Piece.from_fen(char)
    assert piece.type == PIECE_FEN[char.lower()]
    assert piece.color == Color.BLACK
