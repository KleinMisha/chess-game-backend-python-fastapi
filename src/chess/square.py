"""
A square on the board

(placed in its own module as multiple other modules need to import it)
"""

from __future__ import annotations

from dataclasses import dataclass

# Chess board is always 8x8. Just in case we want to try some funky stuff, make it adjustable
BOARD_DIMENSIONS = (8, 8)


@dataclass(frozen=True)
class Square:
    file: int
    rank: int

    @classmethod
    def from_algebraic(cls, sq: str) -> Square:
        """Algebraic notation: 'a1' - 'h8' get converted to (1,1) - (8,8)"""
        file = ord(sq[0]) - ord("a") + 1
        rank = int(sq[1])
        return cls(file, rank)

    def to_algebraic(self) -> str:
        return f"{chr(self.file + ord('a') - 1)}{self.rank}"

    def is_within_bounds(self) -> bool:
        return (1 <= self.file <= BOARD_DIMENSIONS[0]) and (
            1 <= self.rank <= BOARD_DIMENSIONS[1]
        )
