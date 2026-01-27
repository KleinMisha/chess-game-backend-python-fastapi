"""Unit tests for src/chess/fen.py"""

import pytest

from src.chess.fen import (
    CASTLING_RULES,
    VALID_CASTLING_ENCODINGS,
    CastlingDirection,
    CastlingSquares,
    FENState,
    InvalidFENError,
    castling_from_fen,
    castling_to_fen,
    is_valid_castling_rights,
    is_valid_color_code,
    is_valid_en_passant,
    is_valid_fen,
    is_valid_position,
    is_valid_square,
)
from src.chess.pieces import Color
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
    state = FENState.from_fen(fen)
    assert state.to_fen() == fen


@pytest.mark.parametrize("color_str, color", [("w", Color.WHITE), ("b", Color.BLACK)])
def test_color_to_move(color_str: str, color: Color) -> None:
    fen = f"{'/'.join(['8'] * 8)} {color_str} - - 0 1"
    state = FENState.from_fen(fen)
    assert state.color_to_move == color


@pytest.mark.parametrize(
    "en_passant_algebraic, expected_square",
    [("-", None), ("e7", Square.from_algebraic("e7"))],
)
def test_en_passant_square(en_passant_algebraic: str, expected_square: Square) -> None:
    fen = f"{'/'.join(['8'] * 8)} w - {en_passant_algebraic} 0 1"
    state = FENState.from_fen(fen)
    assert state.en_passant_square == expected_square


def test_move_counters() -> None:
    fen = f"{'/'.join(['8'] * 8)} w - - 6 23"
    state = FENState.from_fen(fen)
    assert state.half_move_clock == 6
    assert state.num_turns == 23


@pytest.mark.parametrize(
    "position",
    [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
        "r3k2r/pppq1ppp/2npbn2/4p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1",
        "8/8/8/8/8/8/8/8",
    ],
)
def test_valid_position(position: str) -> None:
    assert is_valid_position(position)


@pytest.mark.parametrize(
    "position",
    [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR/RNBQKBNR",  # an additional rank
        "rnbqkbnr/pppppppp/8/",  # not enough ranks
        "rnbqkbnr/pppppppp/6/23/42/34/PPPPPPPP/RNBQKBNR",  # empty squares exceed number of files
        "rnbqkbnr/pppppppp/8/8/8/8/2P2P42/RNBQKBNR",  # empty squares in between pieces exceeds number of files
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNRRRR",  # number of pieces in the rank exceeds number of files
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/WRTYUIOM",  # bogus codes for the pieces
        "rn@q#bnr/p-ppp-pp/8/8/8/8/PPPPPPPP/RNBQKBNR",  # bogus characters for the pieces
    ],
)
def test_invalid_position(position: str) -> None:
    """Check these bogus positions are invalid"""
    assert not is_valid_position(position)


@pytest.mark.parametrize("castling", VALID_CASTLING_ENCODINGS)
def test_valid_castling(castling: str) -> None:
    assert is_valid_castling_rights(castling)


@pytest.mark.parametrize(
    "castling",
    [
        "KKQ",  # duplicates
        "KQkqKQkq",  # too long (and duplicates)
        "----",
        "%$#&",  # bogus characters
        "KqXQ",  # use a letter outside of K or Q
        "K-kq",  # using a dash when only one of the rights have been revoked
    ],
)
def test_invalid_castling(castling: str) -> None:
    assert not is_valid_castling_rights(castling)


@pytest.mark.parametrize("square", ["a1", "b6", "e5", "h8"])
def test_valid_square(square: str) -> None:
    assert is_valid_square(square)


@pytest.mark.parametrize(
    "square",
    [
        "a9",  # rank beyond range
        "h0",  # rank before range
        "1a",  # wrong order
        "-",
        "a#",
        "x1",  # file beyond the (standard) range
        "!4",
    ],
)
def test_invalid_square(square: str) -> None:
    assert not is_valid_square(square)


@pytest.mark.parametrize("en_passant", ["a1", "h8", "-"])
def test_valid_en_passant(en_passant: str) -> None:
    """include the encoding for 'no en passant square available'."""
    assert is_valid_en_passant(en_passant)


@pytest.mark.parametrize("color", ["w", "b"])
def test_valid_color(color: str) -> None:
    assert is_valid_color_code(color)


@pytest.mark.parametrize(
    "color",
    [
        "white",  # spelling out the color
        "black",  # spelling out the color
        "magenta"  # non-existing color
        "x"  # non-existing color
        "#$!",  # bogus characters
    ],
)
def test_invalid_color(color: str) -> None:
    assert not is_valid_color_code(color)


@pytest.mark.parametrize(
    "fen",
    [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r3k2r/pppq1ppp/2npbn2/4p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 b kq - 3 9",
        "8/8/8/8/8/8/8/8 w - - 0 1",
    ],
)
def test_valid_fen(fen: str) -> None:
    assert is_valid_fen(fen)


@pytest.mark.parametrize(
    "fen",
    [
        "rnbqkbnr/pppppppp/8/8/8/8/XXXXX/8 w KQkq - 0 1",  # invalid position
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR X KQkq - 0 1",  # invalid color,
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w X - 0 1",  # invalid castling
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq 3b 0 1",  # invalid en passant square
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - - 1",  # invalid half-move counter
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 y",  # invalid full move counter
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1 X",  # an additional element
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq 0 1",  # missing element
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1 ",  # trailing space
        " rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # starting space
    ],
)
def test_invalid_fen(fen: str) -> None:
    assert not is_valid_fen(fen)

    with pytest.raises(InvalidFENError):
        FENState.from_fen(fen)


def test_creating_standard_starting_position() -> None:
    state = FENState.starting_position()
    assert state.to_fen() == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_castling_squares_creation() -> None:
    """Test one case, just to have a little contract stating: 'I want to be able to create this dataclass'"""
    castling_squares = CastlingSquares.from_algebraic("e1", "g1", "h1", "f1")
    assert castling_squares.king_from == Square.from_algebraic("e1")
    assert castling_squares.king_to == Square.from_algebraic("g1")
    assert castling_squares.rook_from == Square.from_algebraic("h1")
    assert castling_squares.rook_to == Square.from_algebraic("f1")


@pytest.mark.parametrize(
    "direction,k_from,k_to,r_from,r_to",
    [
        (CastlingDirection.WHITE_KING_SIDE, "e1", "g1", "h1", "f1"),
        (CastlingDirection.WHITE_QUEEN_SIDE, "e1", "c1", "a1", "d1"),
        (CastlingDirection.BLACK_KING_SIDE, "e8", "g8", "h8", "f8"),
        (CastlingDirection.BLACK_QUEEN_SIDE, "e8", "c8", "a8", "d8"),
    ],
)
def test_canonical_castling_rules(
    direction: CastlingDirection, k_from: str, k_to: str, r_from: str, r_to: str
) -> None:
    """Classical castling positional changes of the king and rook."""
    rule = CASTLING_RULES[direction]
    expected = CastlingSquares.from_algebraic(k_from, k_to, r_from, r_to)
    assert expected == rule
