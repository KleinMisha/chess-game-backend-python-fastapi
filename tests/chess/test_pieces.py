"""Unit tests for /src/chess/pieces.py"""

import pytest

from src.chess.pieces import PIECE_FEN, Color, Piece, PieceType


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


@pytest.mark.parametrize("color", [c for c in Color])
def test_promotion_to_queen(color: Color) -> None:
    """Promote a piece to Queen. Make sure that the class is mutable (and not changed to frozen or something), and does not by accident change the color"""
    piece = Piece(PieceType.PAWN, color)
    piece.promote_to(PieceType.QUEEN)
    assert piece.type == PieceType.QUEEN
    assert piece.color == color
