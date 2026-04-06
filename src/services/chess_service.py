"""Orchestration of communication from API router to business logic and persistence layers (and the reverse direction)."""

import logging
from typing import Optional
from uuid import UUID

from src.api.v1.models import (
    CreateGameRequest,
    GameResponse,
    JoinGameRequest,
    LegalMovesRequest,
    LegalMovesResponse,
    MoveRequest,
)
from src.chess.game import Game, build_uci
from src.core.exceptions import GameCreationError, GameNotFoundError
from src.core.models import GameModel
from src.core.shared_types import Color
from src.db.repository import GameRepository


class ChessService:
    """Orchestration of layers for chess game."""

    def __init__(self, repository: GameRepository) -> None:
        self.repo = repository

    # -- API routes logic ---
    def create_new_game(self, request: CreateGameRequest) -> GameResponse:
        """First player requested to create a new game."""
        # If a name is supplied, check if this name is allowed. Otherwise, early exit
        game_name = self._prepare_name(request.game_name)
        if game_name and not self._is_unique(game_name):
            raise GameCreationError(f"Game with name '{game_name}' already exists.")

        # Use info in CreateGameRequest to create a new Game, and convert into GameModel
        new_game = Game.new_game(
            player=request.player_name,
            color=request.color,
            starting_fen=request.starting_fen,
        )

        created_game_data = new_game.to_model()
        logging.info(
            f"Game instantiated by player: {request.player_name} - {request.color} pieces."
        )

        # Store the GameModel in the repository
        stored_model, game_id = self.repo.create_game(created_game_data, name=game_name)
        logging.info(f"Created new game record with id: {game_id}")
        if game_name:
            logging.info(f"Game stored under name: {game_name} -> {game_id}")

        # Reconstruct game from stored GameModel (to compute winner, etc.)
        stored_game = Game.from_model(stored_model)

        # Return a GameResponse
        return self._create_game_response(game_id, stored_game)

    def join_game(self, identifier: str, request: JoinGameRequest) -> GameResponse:
        """Second player requested to join a game."""
        # Determine if game ID  or name is used in URL
        game_id = self._get_uuid(identifier)

        # Retrieve persisted GameModel from repository
        stored_model = self._fetch_game(game_id)
        logging.info(f"Game retrieved from repository with id: {game_id}")

        # Create a new Game instance from the retrieved GameModel
        game = Game.from_model(stored_model)

        # Register the requested player
        game.register_player(request.player_name)

        # Capture updated state in GameModel
        with_player_registered = game.to_model()
        logging.info(
            f"Registered player {request.player_name} at game with id: {game_id}"
        )

        # store in repository
        self.repo.update_game(game_id, with_player_registered)
        logging.info(f"Updated recorded game with id: {game_id}")

        # Return a GameResponse
        return self._create_game_response(game_id, game)

    def get_game_state(self, identifier: str) -> GameResponse:
        """
        Retrieve current game state.
        ----
        Used in "polling" loop by frontend to check when it is the player's turn for instance.
        """
        # Determine if game ID  or name is used in URL
        game_id = self._get_uuid(identifier)

        # Retrieve persisted GameModel from repository
        game_model = self._fetch_game(game_id)
        logging.info(f"Retrieved game from repository with id: {game_id}")

        game = Game.from_model(game_model)
        return self._create_game_response(game_id, game)

    def legal_moves(
        self, identifier: str, request: LegalMovesRequest
    ) -> LegalMovesResponse:
        """retrieve set of legal moves."""
        # Determine if game ID  or name is used in URL
        game_id = self._get_uuid(identifier)

        # Retrieve persisted GameModel from repository
        stored_model = self._fetch_game(game_id)
        logging.info(f"Retrieved game from repository with id: {game_id}")

        # Create a new Game instance from the retrieved GameModel
        game = Game.from_model(stored_model)

        # Compute legal moves
        legal_moves = game.legal_moves(request.player_name)
        logging.info(f"Computed legal moves for player: {request.player_name}")

        return LegalMovesResponse(
            game_id=game_id,
            game_name=self.repo.get_name_by_id(game_id),
            player_name=request.player_name,
            color=next(
                Color[c.name]
                for c in game.players.keys()
                if game.players[c] == request.player_name
            ),
            legal_moves=legal_moves,
        )

    def make_move(self, identifier: str, request: MoveRequest) -> GameResponse:
        """Make a move attempt."""
        # Determine if game ID  or name is used in URL
        game_id = self._get_uuid(identifier)

        # Retrieve persisted GameModel from repository
        stored_model = self._fetch_game(game_id)
        logging.info(f"Retrieved game from repository with id: {game_id}")

        # Parse data in MoveRequest to UCI notation
        move_uci = build_uci(
            from_square_alg=request.from_square,
            to_square_alg=request.to_square,
            promotion=request.promote_to,
        )

        # Create a new Game instance from the retrieved GameModel
        game = Game.from_model(stored_model)

        # Attempt the move
        game.make_move(move_uci, request.player_name)
        logging.info(f"Player {request.player_name} made move: {move_uci}")

        # Capture updated state in GameModel
        after_move = game.to_model()

        # store in repository
        self.repo.update_game(game_id, after_move)
        logging.info(f"Updated recorded game with id: {game_id}")

        # Return a GameResponse
        return self._create_game_response(game_id, game)

    def list_games(self) -> None:
        """Show all recorded games.

        ---
        # TODO If needed, should implement a corresponding method on the Repository side.
        """
        raise NotImplementedError

    def delete_game(self, identifier: str) -> None:
        """Handle a request to delete a Game record."""

        # Determine if game ID  or name is used in URL
        game_id = self._get_uuid(identifier)

        self.repo.delete_game(game_id)
        logging.info(f"Deleted record of game with id: {game_id}")

    # -- Internal helpers --
    def _create_game_response(self, game_id: UUID, game: Game) -> GameResponse:
        """Convert info in GameModel to a GameResponse (for game with given ID.)"""

        # retrieve GameModel data
        model = game.to_model()

        # Before the first turn gets played, the starting FEN equals the current FEN. Otherwise get it as first recorded FEN in history.
        starting_fen = (
            model.history_fen[0] if len(model.history_fen) > 0 else model.current_fen
        )
        return GameResponse(
            game_id=game_id,
            game_name=self.repo.get_name_by_id(game_id),
            players=model.registered_players,
            fen_state=model.current_fen,
            starting_state=starting_fen,
            move_history=model.moves_uci,
            status=model.status,
            winner=game.winner,
        )

    def _fetch_game(self, game_id: UUID) -> GameModel:
        """Attempt to find the game in the repository and raise error if it fails."""
        game_model = self.repo.get_game(game_id)
        id = str(game_id)
        if game_model is None:
            raise GameNotFoundError(f"Game with {id=} not found.")
        return game_model

    def _prepare_name(self, name: Optional[str]) -> str | None:
        """
        Preprocesses the provided name argument.
        ----
        * If no name is supplied --> passthrough
        * If empty string is provided --> return None
        * If a name is provided ---> first normalize
        """
        if not name:
            return None
        normalized_name = self._normalize_name(name)
        return normalized_name or None

    def _normalize_name(self, name: str) -> str:
        """
        Normalize requested game name(s) to simplify storage / avoid edge cases in lookup.
        ----
        * converts to lower case
        * removes trailing spaces (meaning the empty string will result in a null value in the repository)
        * replaces spaces between words by dashes
        * replaces underscores by dashes
        """
        return name.lower().strip().replace(" ", "-").replace("_", "-")

    def _is_unique(self, name: str) -> bool:
        return not self.repo.name_exists(name)

    def _get_uuid(self, identifier: str) -> UUID:
        """
        Return the ID for the given identifier.
        ----
        If the entered identifier already is a UUID, returns input value.
        If the entered identifier is a name (alias), uses the repository to find the corresponding UUID.
        """
        # Case 1: Used UUID in the URL
        if self._is_uuid(identifier):
            return UUID(identifier)

        # Case 2: Used the name in the URL
        game_id = self.repo.get_id_by_name(identifier)
        if game_id is None:
            raise GameNotFoundError(f"Game with {identifier=} not found.")

        return game_id

    def _is_uuid(self, identifier: str) -> bool:
        """Checks if the given string can be interpreted as a UUID"""
        try:
            UUID(identifier)
            return True
        except ValueError:
            return False
