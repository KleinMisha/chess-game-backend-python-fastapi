"""Unit tests for /src/chess/square.py"""

from string import ascii_lowercase

import pytest

from src.chess.square import BOARD_DIMENSIONS, Square


@pytest.mark.parametrize(
    "file, rank, notation",
    [
        (file, rank, f"{ascii_lowercase[file - 1]}{rank}")
        for file in range(1, 9)
        for rank in range(1, 9)
    ],
)
def test_creating_from_algebraic(file: int, rank: int, notation: str) -> None:
    """Simply checks if the notation for 'a1' indeed maps to file 1, rank 1, etc."""
    square = Square.from_algebraic(notation)
    assert square.file == file
    assert square.rank == rank


@pytest.mark.parametrize(
    "file, rank, notation",
    [
        (file, rank, f"{ascii_lowercase[file - 1]}{rank}")
        for file in range(1, 9)
        for rank in range(1, 9)
    ],
)
def test_to_algebraic_notation(file: int, rank: int, notation: str) -> None:
    """Test the reverse, so the square on the 1st file and 1st rank should be denoted as a1"""
    square = Square(file, rank)
    assert square.to_algebraic() == notation


def test_square_within_bounds() -> None:
    """happy case: pieces within the dimensions of the board"""
    for file in range(1, BOARD_DIMENSIONS[0] + 1):
        for rank in range(1, BOARD_DIMENSIONS[1] + 1):
            square = Square(file, rank)
            assert square.is_within_bounds()


def test_square_out_of_bounds() -> None:
    """Later can check an appropriate error is raised (or whatever I expect to happen)"""
    square = Square(BOARD_DIMENSIONS[0] + 1, BOARD_DIMENSIONS[1] + 1)
    assert not square.is_within_bounds()

    square = Square(-1, -1)
    assert not square.is_within_bounds()
