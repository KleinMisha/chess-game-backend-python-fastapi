"""Implementation of (Game)Repository using SQLAlchemy"""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.models import GameModel
from src.db.schema import DBGame


class SQLGameRepository:
    """Data stored using SQL / methods implemented using SQLAlchemy"""

    def __init__(self, db_session: Session) -> None:
        self.db = db_session

    def get_game(self, game_id: UUID) -> GameModel | None:
        """Get game by ID, if record exists."""
        game_db = self._fetch_game(game_id)
        if game_db:
            return self._to_model(game_db)
        return None

    def create_game(self, game: GameModel) -> tuple[GameModel, UUID]:
        """Store new game and return the stored data + newly created game ID."""

        new_id = uuid4()
        game_db = DBGame(
            id=new_id,
            current_fen=game.current_fen,
            history_fen=game.history_fen,
            moves_uci=game.moves_uci,
            registered_players=game.registered_players,
            status=game.status,
        )
        self.db.add(game_db)
        self.db.commit()
        self.db.refresh(game_db)
        return self._to_model(game_db), new_id

    def update_game(self, game_id: UUID, game: GameModel) -> GameModel | None:
        """Add new info to existing record."""
        game_db = self._fetch_game(game_id)
        if not game_db:
            return None
        game_db.current_fen = game.current_fen
        game_db.history_fen = game.history_fen
        game_db.moves_uci = game.moves_uci
        game_db.registered_players = game.registered_players
        game_db.status = game.status
        self.db.commit()
        self.db.refresh(game_db)
        return self._to_model(game_db)

    def delete_game(self, game_id: UUID) -> GameModel | None:
        """Remove a game's record."""
        game_db = self._fetch_game(game_id)
        if not game_db:
            return None
        game_model = self._to_model(game_db)
        self.db.delete(game_db)
        self.db.commit()
        return game_model

    def _fetch_game(self, game_id: UUID) -> DBGame | None:
        query = select(DBGame).where(DBGame.id == game_id)
        return self.db.scalar(query)

    def _to_model(self, game_db: DBGame) -> GameModel:
        """Convert SQLAlchemy model to data transfer model."""
        return GameModel(
            current_fen=game_db.current_fen,
            history_fen=game_db.history_fen,
            moves_uci=game_db.moves_uci,
            registered_players=game_db.registered_players,
            status=game_db.status,
        )
