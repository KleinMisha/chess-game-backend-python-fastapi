"""Unit tests for src/chess/position.py"""

import pytest

from src.chess.pieces import Color
from src.chess.position import (
    CastlingDirection,
    PositionState,
    castling_from_fen,
    castling_to_fen,
)
from src.chess.square import Square


@pytest.mark.parametrize(
    "fen, expected_rights",
    [
        ("KQkq", {direction: True for direction in CastlingDirection}),
        (
            "KQk",
            {
                CastlingDirection.WHITE_KING_SIDE: True,
                CastlingDirection.WHITE_QUEEN_SIDE: True,
                CastlingDirection.BLACK_KING_SIDE: True,
                CastlingDirection.BLACK_QUEEN_SIDE: False,
            },
        ),
        (
            "KQ",
            {
                CastlingDirection.WHITE_KING_SIDE: True,
                CastlingDirection.WHITE_QUEEN_SIDE: True,
                CastlingDirection.BLACK_KING_SIDE: False,
                CastlingDirection.BLACK_QUEEN_SIDE: False,
            },
        ),
        ("-", {direction: False for direction in CastlingDirection}),
    ],
)
def test_castling_from_fen(
    fen: str, expected_rights: dict[CastlingDirection, bool]
) -> None:
    """Check encoding of castling rights is correctly decoded"""
    castling_rights = castling_from_fen(fen)
    assert castling_rights == expected_rights


@pytest.mark.parametrize(
    "expected_fen, rights",
    [
        ("KQkq", {direction: True for direction in CastlingDirection}),
        (
            "KQk",
            {
                CastlingDirection.WHITE_KING_SIDE: True,
                CastlingDirection.WHITE_QUEEN_SIDE: True,
                CastlingDirection.BLACK_KING_SIDE: True,
                CastlingDirection.BLACK_QUEEN_SIDE: False,
            },
        ),
        (
            "KQ",
            {
                CastlingDirection.WHITE_KING_SIDE: True,
                CastlingDirection.WHITE_QUEEN_SIDE: True,
                CastlingDirection.BLACK_KING_SIDE: False,
                CastlingDirection.BLACK_QUEEN_SIDE: False,
            },
        ),
        ("-", {direction: False for direction in CastlingDirection}),
    ],
)
def test_castling_to_fen(
    expected_fen: str, rights: dict[CastlingDirection, bool]
) -> None:
    """Check castling rights get correctly encoded"""
    assert castling_to_fen(rights) == expected_fen


@pytest.mark.parametrize(
    "fen",
    [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r3k2r/pppq1ppp/2npbn2/4p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 b kq - 3 9",
        "8/8/8/8/8/8/8/8 w - - 0 1",
    ],
)
def test_fen_parsing_roundtrip(fen: str) -> None:
    """Create a PositionState from FEN, convert back to FEN to check if the order of elements in the FEN string are parsed correctly"""
    state = PositionState.from_fen(fen)
    assert state.to_fen() == fen


@pytest.mark.parametrize("color_str, color", [("w", Color.WHITE), ("b", Color.BLACK)])
def test_color_to_move(color_str: str, color: Color) -> None:
    fen = f"{'/'.join(['8'] * 8)} {color_str} - - 0 1"
    state = PositionState.from_fen(fen)
    assert state.color_to_move == color


@pytest.mark.parametrize(
    "en_passant_algebraic, expected_square",
    [("-", None), ("e7", Square.from_algebraic("e7"))],
)
def test_en_passant_square(en_passant_algebraic: str, expected_square: Square) -> None:
    fen = f"{'/'.join(['8'] * 8)} w - {en_passant_algebraic} 0 1"
    state = PositionState.from_fen(fen)
    assert state.en_passant_square == expected_square


def test_move_counters() -> None:
    fen = f"{'/'.join(['8'] * 8)} w - - 6 23"
    state = PositionState.from_fen(fen)
    assert state.half_move_clock == 6
    assert state.num_turns == 23
