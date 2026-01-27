"""The Game board implements all rules that effect the `position` (in chess: the configuration of pieces on the board)"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Self

from src.chess.moves import MOVEMENT_RULES, CandidateMovesFn, Move
from src.chess.pieces import Color, Piece, PieceType
from src.chess.square import BOARD_DIMENSIONS, Square


@dataclass
class Board:
    position: dict[Square, Piece]

    @classmethod
    def from_fen(cls, fen_str: str) -> Self:
        """Construct a board using a given FEN string.

        That is, we supply the first part of the FEN string that denotes the board position
        ex. standard starting position:
        rnbkqbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBKQBNR
        means:
        * black pieces are on the 8th rank, starting with rook on h8, knight on g8, etc.
        * pawns cover 7th rank entirely
        * ranks 6 through 3 have 8 consecutive empty squares
        * rank 2 are the white pawns (capital letters)
        * 1st rank are the white pieces. Again, left-to-right reads h1-a1.
        """
        position: dict[Square, Piece] = {}
        fen_by_ranks = fen_str.split("/")
        for rank_idx, fen_one_rank in enumerate(fen_by_ranks):
            # FEN string is read from top rank (8th) to bottom rank (1st)
            rank = BOARD_DIMENSIONS[1] - rank_idx
            # ... but the first character is the a-file, so reads in normal direction
            file = 1
            for character in fen_one_rank:
                if character.isalpha():
                    # simple case: a letter directly denotes the piece that should be created
                    position[Square(file, rank)] = Piece.from_fen(character)
                    file += 1
                else:
                    # A number denotes the amount of empty pieces after each other
                    for _ in range(int(character)):
                        position[Square(file, rank)] = Piece(
                            PieceType.EMPTY, Color.NONE
                        )
                        file += 1
        return cls(position)

    def to_fen(self) -> str:
        """Ranks are separated by slashes in FEN string."""
        return "/".join(
            self._rank_to_fen(rank) for rank in range(BOARD_DIMENSIONS[1], 0, -1)
        )

    def _rank_to_fen(self, rank: int) -> str:
        """FEN string of a single rank"""
        fen_characters: list[str] = []
        empty_count = 0
        for file in range(1, BOARD_DIMENSIONS[0] + 1):
            piece = self.piece(Square(file, rank))

            if piece.type != PieceType.EMPTY:
                if empty_count > 0:
                    fen_characters.append(str(empty_count))
                    empty_count = 0
                fen_characters.append(piece.to_fen())
            else:
                empty_count += 1

        # if the entire rank is empty, then we still place this number in the string
        if empty_count > 0:
            fen_characters.append(str(empty_count))
        return "".join(fen_characters)

    def piece(self, square: Square) -> Piece:
        return self.position[square]

    def locate_pieces(self, piece_type: PieceType) -> list[Square]:
        return [
            square
            for square, piece in self.position.items()
            if piece.type == piece_type
        ]

    def locate_color(self, color: Color) -> list[Square]:
        return [
            square for square, piece in self.position.items() if piece.color == color
        ]

    def empty_squares(self) -> list[Square]:
        """Convenience method: Will call this one the most probably"""
        # TODO: If I ONLY need this version, just remove the previous method and move the logic into here
        return self.locate_pieces(PieceType.EMPTY)

    def generate_candidate_moves(self, color: Color) -> list[Move]:
        """
        Before knowing the set of legal moves, we use raycasting to find candidate moves, which will later be tested for legality
        (making sure it does not put yourself in check.)

        ---
        NOTE: En passant rule is taken care of in the Game class later.
        """
        current_board = deepcopy(self)
        candidate_moves: list[Move] = []
        same_color_pieces_loc = self.locate_color(color)
        for starting_square in same_color_pieces_loc:
            piece_type = self.piece(starting_square).type
            movement_rule: CandidateMovesFn = MOVEMENT_RULES[piece_type]
            piece_moves = movement_rule(starting_square, current_board)
            candidate_moves.extend(piece_moves)
        return candidate_moves

    def move_piece(self, move: Move) -> None:
        """Update the position on the board"""
        piece_that_moved = self.piece(move.from_square)
        self.position[move.from_square] = Piece(PieceType.EMPTY, Color.NONE)
        self.position[move.to_square] = piece_that_moved

    def move_pieces(self, moves: list[Move]) -> None:
        """convenience method to apply multiple moves (if you quickly want to start a board in a given position reached after some moves)"""
        for move in moves:
            self.move_piece(move)

    def count_material(self) -> dict[Color, int]:
        """Tally the points of material each player has on the board"""
        return {
            color: self._count_material_player(color)
            for color in Color
            if color != Color.NONE
        }

    def _player_pieces(self, color: Color) -> list[Piece]:
        """find all pieces of a given color"""
        return [piece for piece in self.position.values() if piece.color == color]

    def _count_material_player(self, color: Color) -> int:
        """Tally the points of material for a specific player"""
        return sum([piece.points for piece in self._player_pieces(color)])
