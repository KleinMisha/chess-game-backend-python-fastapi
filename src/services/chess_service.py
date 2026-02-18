"""Orchestration of communication from API router to business logic and persistence layers (and the reverse direction)."""

from uuid import UUID

from src.api.models import (
    CreateGameRequest,
    DeleteGameRequest,
    GameResponse,
    GetGameRequest,
    JoinGameRequest,
    LegalMovesRequest,
    LegalMovesResponse,
    MoveRequest,
)
from src.chess.game import Game, build_uci
from src.core.exceptions import RepositoryError
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

        # Use info in CreateGameRequest to create a new Game, and convert into GameModel
        new_game = Game.new_game(player=request.player_name, color=request.color)
        created_game_data = new_game.to_model()

        # Store the GameModel in the repository
        stored_game, game_id = self.repo.create_game(created_game_data)

        # Return a GameResponse
        return self._create_game_response(game_id, stored_game)

    def join_game(self, request: JoinGameRequest) -> GameResponse:
        """Second player requested to join a game."""

        # Retrieve persisted GameModel from repository
        stored_model = self._fetch_game(request.game_id)

        # Create a new Game instance from the retrieved GameModel
        game = Game.from_model(stored_model)

        # Register the requested player
        game.register_player(request.player_name)

        # Capture updated state in GameModel
        with_player_registered = game.to_model()

        # store in repository
        self.repo.update_game(request.game_id, with_player_registered)

        # Return a GameResponse
        return self._create_game_response(request.game_id, with_player_registered)

    def get_game_state(self, request: GetGameRequest) -> GameResponse:
        """
        Retrieve current game state.
        ----
        Used in "polling" loop by frontend to check when it is the player's turn for instance.
        """
        # Retrieve persisted GameModel from repository
        game_model = self._fetch_game(request.game_id)
        return self._create_game_response(request.game_id, game_model)

    def legal_moves(self, request: LegalMovesRequest) -> LegalMovesResponse:
        """retrieve set of legal moves."""

        # Retrieve persisted GameModel from repository
        stored_model = self._fetch_game(request.game_id)

        # Create a new Game instance from the retrieved GameModel
        game = Game.from_model(stored_model)

        # Compute legal moves
        legal_moves = game.legal_moves(request.player_name)
        return LegalMovesResponse(
            game_id=request.game_id,
            player_name=request.player_name,
            color=next(
                Color[c.name]
                for c in game.players.keys()
                if game.players[c] == request.player_name
            ),
            legal_moves=legal_moves,
        )

    def make_move(self, request: MoveRequest) -> GameResponse:
        """Make a move attempt."""

        # Retrieve persisted GameModel from repository
        stored_model = self._fetch_game(request.game_id)

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

        # Capture updated state in GameModel
        after_move = game.to_model()

        # store in repository
        self.repo.update_game(request.game_id, after_move)

        # Return a GameResponse
        return self._create_game_response(request.game_id, after_move)

    def list_games(self) -> None:
        """Show all recorded games.

        ---
        # TODO If needed, should implement a corresponding method on the Repository side.
        """
        raise NotImplementedError

    def delete_game(self, request: DeleteGameRequest) -> None:
        """Handle a request to delete a Game record."""
        self.repo.delete_game(request.game_id)

    # -- Internal helpers --
    def _create_game_response(self, game_id: UUID, model: GameModel) -> GameResponse:
        """Convert info in GameModel to a GameResponse (for game with given ID.)"""

        # Before the first turn gets played, the starting FEN equals the current FEN. Otherwise get it as first recorded FEN in history.
        starting_fen = (
            model.history_fen[0] if len(model.history_fen) > 0 else model.current_fen
        )
        return GameResponse(
            game_id=game_id,
            players=model.registered_players,
            fen_state=model.current_fen,
            starting_state=starting_fen,
            move_history=model.moves_uci,
        )

    def _fetch_game(self, game_id: UUID) -> GameModel:
        """Attempt to find the game in the repository and raise error if it fails."""
        game_model = self.repo.get_game(game_id)
        if game_model is None:
            raise RepositoryError(f"Game with {game_id=} not found.")
        return game_model
