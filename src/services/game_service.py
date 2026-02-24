"""Protocol for service. API endpoints depend on this type."""

from typing import Protocol
from uuid import UUID

from src.api.v1.models import (
    CreateGameRequest,
    GameResponse,
    JoinGameRequest,
    LegalMovesRequest,
    LegalMovesResponse,
    MoveRequest,
)
from src.db.repository import GameRepository


class GameService(Protocol):
    """Orchestration of layers for chess game."""

    repo: GameRepository

    # -- API routes logic ---
    def create_new_game(self, request: CreateGameRequest) -> GameResponse:
        """First player requested to create a new game."""
        ...

    def join_game(self, game_id: UUID, request: JoinGameRequest) -> GameResponse:
        """Second player requested to join a game."""
        ...

    def get_game_state(self, game_id: UUID) -> GameResponse:
        """
        Retrieve current game state.
        ----
        Used in "polling" loop by frontend to check when it is the player's turn for instance.
        """
        ...

    def legal_moves(
        self, game_id: UUID, request: LegalMovesRequest
    ) -> LegalMovesResponse:
        """retrieve set of legal moves."""
        ...

    def make_move(self, game_id: UUID, request: MoveRequest) -> GameResponse:
        """Make a move attempt."""
        ...

    def list_games(self) -> None:
        """Show all recorded games."""
        ...

    def delete_game(self, game_id: UUID) -> None:
        """Handle a request to delete a Game record."""
        ...
