"""Protocol repository (can implement later for SQL Alchemy / simple Excel table etc.)"""

from typing import Protocol
from uuid import UUID

from src.core.models import GameModel


class GameRepository(Protocol):
    """Persistence layer orchestration"""

    def get_game(self, game_id: UUID) -> GameModel | None:
        """Get game by ID, if record exists."""
        ...

    def create_game(self, game: GameModel) -> tuple[GameModel, UUID]:
        """Store new game and return the stored data + newly created game ID."""
        ...

    def update_game(self, game_id: UUID, game: GameModel) -> GameModel | None:
        """Add new info to existing record."""
        ...

    def delete_game(self, game_id: UUID) -> GameModel | None:
        """Remove a game's record."""
        ...
