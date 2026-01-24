"""Unit tests for /src/chess/pieces.py"""

import pytest

from src.chess.pieces import FEN_TO_PIECE, PIECE_TO_FEN, Color, Piece, PieceType


@pytest.mark.parametrize("char", [char.upper() for char in FEN_TO_PIECE.keys()])
def test_creating_white_piece_from_fen(char: str) -> None:
    """Capital letters are used for white pieces"""
    piece = Piece.from_fen(char)
    assert piece.type == FEN_TO_PIECE[char.lower()]
    assert piece.color == Color.WHITE


@pytest.mark.parametrize("char", [char.lower() for char in FEN_TO_PIECE.keys()])
def test_creating_black_piece_from_fen(char: str) -> None:
    """Lower case letters are used for white pieces"""
    piece = Piece.from_fen(char)
    assert piece.type == FEN_TO_PIECE[char.lower()]
    assert piece.color == Color.BLACK


@pytest.mark.parametrize(
    "piece_type",
    [piece_type for piece_type in PieceType if piece_type != PieceType.EMPTY],
)
def test_white_pieces_to_fen(piece_type: PieceType) -> None:
    """Capital letters are used for the white pieces"""
    piece = Piece(piece_type, Color.WHITE)
    assert piece.to_fen() == PIECE_TO_FEN[piece_type].upper()


@pytest.mark.parametrize(
    "piece_type",
    [piece_type for piece_type in PieceType if piece_type != PieceType.EMPTY],
)
def test_black_pieces_to_fen(piece_type: PieceType) -> None:
    """Lower case letters are used for the white pieces"""
    piece = Piece(piece_type, Color.BLACK)
    assert piece.to_fen() == PIECE_TO_FEN[piece_type].lower()


@pytest.mark.parametrize("color", [c for c in Color])
def test_promotion_to_queen(color: Color) -> None:
    """Promote a piece to Queen. Make sure that the class is mutable (and not changed to frozen or something), and does not by accident change the color"""
    piece = Piece(PieceType.PAWN, color)
    piece.promote_to(PieceType.QUEEN)
    assert piece.type == PieceType.QUEEN
    assert piece.color == color
