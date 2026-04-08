"""Protocol repository (can implement later for SQL Alchemy / simple Excel table etc.)"""

from typing import Optional, Protocol
from uuid import UUID

from src.core.models import GameModel


class GameRepository(Protocol):
    """Persistence layer orchestration"""

    def create_game(
        self, game: GameModel, name: Optional[str] = None
    ) -> tuple[GameModel, UUID]:
        """Store new game and return the stored data + newly created game ID."""
        ...

    def get_game(self, game_id: UUID) -> GameModel | None:
        """Get game by ID, if record exists."""
        ...

    def update_game(self, game_id: UUID, game: GameModel) -> GameModel | None:
        """Add new info to existing record."""
        ...

    def delete_game(self, game_id: UUID) -> GameModel | None:
        """Remove a game's record."""
        ...

    def name_exists(self, name: str) -> bool:
        """Check if there already is a record with the suggested alias."""
        ...

    def get_id_by_name(self, name: str) -> UUID | None:
        """Find the game ID with the given name (alias)."""
        ...

    def get_name_by_id(self, game_id: UUID) -> str | None:
        """Find the game name (if any) for the game with the given ID."""
        ...

    def get_all_name_id_pairs(self) -> list[tuple[str | None, UUID]]:
        """Returns all registered game name / game id pairs."""
        ...

    def get_all_games(self) -> list[tuple[UUID, GameModel]]:
        "Returns all the games stored in the repository."
        ...
