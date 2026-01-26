"""
The Game class will be the entrypoint into the domain layer for the service layer.
It is responsible for orchestrating all the business logic required to play a turn of the board game -->
passes this information to the service layer, which can then pass it onwards to the API layer.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Self

from src.chess.board import Board
from src.chess.fen import FENState
from src.chess.game_model import GameModel
from src.chess.moves import Move
from src.chess.pieces import Color
from src.core.exceptions import GameStateError


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

        # Validation
        status_name = model.status.replace(" ", "_").upper()
        if status_name not in Status.__members__:
            raise GameStateError(
                f"Invalid status code: {model.status!r}. \nPick one from {','.join([status.name.lower() for status in Status])}"
            )

        # create the Game
        board = Board.from_fen(model.current_fen.split(" ")[0])
        moves = [Move.from_uci(uci) for uci in model.moves_uci]
        history = model.history_fen
        state = FENState.from_fen(model.current_fen)
        players = {
            color: model.registered_players[color.name.lower()]
            for color in [Color.WHITE, Color.BLACK]
            if color.name.lower() in model.registered_players.keys()
        }
        status = Status[status_name]

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

    @classmethod
    def new_game(
        cls, player: str, color: str, starting_fen: Optional[str] = None
    ) -> Self:
        """To start a new game with the player using the pieces with the indicated color."""

        state = (
            FENState.from_fen(starting_fen)
            if starting_fen
            else FENState.starting_position()
        )
        board = Board.from_fen(state.position)
        available_colors = [c.name for c in Color if c != Color.NONE]
        if color.upper() not in available_colors:
            raise GameStateError(
                f"Color {color} not in {','.join([c.lower() for c in available_colors])}."
            )
        player_color = Color[color.upper()]
        return cls(
            board=board,
            moves=[],
            history=[],
            state=state,
            players={player_color: player},
            status=Status.WAITING_FOR_PLAYERS,
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
