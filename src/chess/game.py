"""
The Game class will be the entrypoint into the domain layer for the service layer.
It is responsible for orchestrating all the business logic required to play a turn of the board game -->
passes this information to the service layer, which can then pass it onwards to the API layer.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Self

from src.chess.board import Board
from src.chess.fen_state import FENState
from src.chess.game_model import GameModel
from src.chess.moves import Move
from src.chess.pieces import Color


class Status(Enum):
    WAITING_FOR_PLAYERS = auto()
    IN_PROGRESS = auto()
    CHECKMATE = auto()
    STALEMATE = auto()
    DRAW_REPETITION = auto()
    DRAW_FIFTY_MOVE_RULE = auto()
    ABORTED = auto()


@dataclass
class Game:
    board: Board
    moves: list[Move]
    history: list[str]  # list of FEN strings
    state: FENState
    players: dict[Color, str]
    status: Status

    @classmethod
    def from_model(cls, model: GameModel) -> Self:
        """Define how to construct a Game from the information the Service layer actually has"""
        board = Board.from_fen(model.current_fen.split(" ")[0])
        moves = [Move.from_uci(uci) for uci in model.moves_uci]
        history = model.history_fen
        state = FENState.from_fen(model.current_fen)
        players = {
            color: model.registered_players[color.name.lower()]
            for color in [Color.WHITE, Color.BLACK]
            if color.name.lower() in model.registered_players.keys()
        }
        status = Status[model.status.upper()]

        return cls(board, moves, history, state, players, status)

    def to_model(self) -> GameModel:
        """Encode back into a format the Service layer uses"""

        return GameModel(
            current_fen=self.state.to_fen(),
            history_fen=self.history,
            moves_uci=[move.to_uci() for move in self.moves],
            registered_players={
                "white": self.players[Color.WHITE],
                "black": self.players[Color.BLACK],
            },
            status=self.status.name.lower(),
        )

    @property
    def winner(self) -> Optional[str]:
        """
        For now only works for checkmate.
        Given we know it is checkmate, the player who is requesting to move just got mated and the opponent must be the winner
        """
        if self.status != Status.CHECKMATE:
            return None
        return (
            self.players[Color.WHITE]
            if self.state.color_to_move == Color.BLACK
            else self.players[Color.BLACK]
        )

    def _commit_move(self, move: Move) -> None:
        self.moves.append(move)
