"""
The Game class will be the entrypoint into the domain layer for the service layer.
It is responsible for orchestrating all the business logic required to play a turn of the board game -->
passes this information to the service layer, which can then pass it onwards to the API layer.
"""

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Self

from src.chess.board import Board
from src.chess.castling import CASTLING_RULES, CastlingDirection
from src.chess.fen import FENState
from src.chess.game_model import GameModel
from src.chess.moves import (
    AcceptedMove,
    Move,
    candidate_castling_move,
    castling_path,
    castling_rook_squares,
    en_passant_moves,
    is_pawn_push_to_promotion_square,
    pawn_pushes_w_promotion,
)
from src.chess.pieces import AVAILABLE_COLOR_NAMES, Color, Piece, PieceType
from src.chess.square import Square
from src.core.exceptions import (
    GameStateError,
    IllegalMoveError,
    NotYourTurnError,
)


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
    # --- DOMAIN LAYER API CALLED BY SERVICE---

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
        if color.upper() not in AVAILABLE_COLOR_NAMES:
            raise GameStateError(
                f"Cannot create new game. Color {color} not in {','.join([c.lower() for c in AVAILABLE_COLOR_NAMES])}."
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

    def register_player(self, player: str) -> None:
        """Registering the 2nd player to an open game"""
        if self.status != Status.WAITING_FOR_PLAYERS:
            raise GameStateError(
                f"Cannot join this game. Game is not accepting new players. status: {self.status}"
            )

        opponent_color = list(self.players.keys())[0]
        player_color = Color.WHITE if opponent_color == Color.BLACK else Color.BLACK
        new_player = {player_color: player}
        self.players.update(new_player)
        self._change_status(Status.IN_PROGRESS)

    def legal_moves(self, player: str) -> list[str]:
        """
        Service will request the set of legal moves.
        ----

        ----
        These can be used to display to the user.
        Even if not used in this way, separates the concerns of generating legal move sets/checking if it is your turn to move
        from selecting a move to make/checking legality.

        ----
        1. Check if it is your turn
        2. Yes? Generate legal moves and return a list of moves.
        """
        # make sure the game is (still) in progress
        if self.status != Status.IN_PROGRESS:
            raise GameStateError(f"Game is not in progress. status: {self.status}")

        # make sure it is your turn
        self._assert_your_turn(player)

        # determine your legal moves
        player_color = self._get_player_color(player)
        return [move.to_uci() for move in self._generate_legal_moves(player_color)]

    def make_move(self, move_uci: str, player: str) -> None:
        """
        Attempt to make a move
        -----

        5. update the board (NOTE: if castling, move the king and the rook)
        6. update the (history of) moves
        7. update the FEN history
        8. update game status (if needed)

        (Service will make separate call to update points counts)
        """
        # make sure the game is (still) in progress
        if self.status != Status.IN_PROGRESS:
            raise GameStateError(f"Game is not in progress. status: {self.status}")

        # make sure it is your turn
        self._assert_your_turn(player)

        # determine legal moves
        player_color = self._get_player_color(player)
        legal_moves = self._generate_legal_moves(player_color)
        # check if move is legal
        new_move = Move.from_uci(move_uci)
        if new_move not in legal_moves:
            raise IllegalMoveError(f"Move not allowed: {move_uci}")

        # Store move info before update
        accepted_move = self._create_accepted_move(new_move)

        # update the FEN history (with the FEN before the move)
        current_fen = self.state.to_fen()
        self._update_fen_history(current_fen)

        # update the board
        self._update_board(accepted_move)

        # update the current FEN
        self._update_fen_state(accepted_move)

        # update the list of moves in this game
        self._update_moves(accepted_move.move)

        # update the Game Status / check for end condition
        self._update_game_status()

    # -- PRIVATE HELPERS ---
    def _get_turn_player(self) -> str:
        turn_player = self.players[self.state.color_to_move]
        return turn_player

    def _get_player_color(self, player: str) -> Color:
        return next(color for color, name in self.players.items() if name == player)

    def _get_turn_player_color(self) -> Color:
        """convenience method as this is used frequently."""
        turn_player = self._get_turn_player()
        return self._get_player_color(turn_player)

    def _get_opponent_color(self) -> Color:
        player_color = self._get_turn_player_color()
        return Color.WHITE if player_color == Color.BLACK else Color.BLACK

    def _assert_your_turn(self, player: str) -> None:
        """You must wait for your turn before calculating legal moves / making a move."""
        player_to_move = self._get_turn_player()
        if player != player_to_move:
            raise NotYourTurnError(
                f"It is not your turn. Waiting for player {player_to_move} to make a move first."
            )

    def _generate_legal_moves(self, color: Color) -> list[Move]:
        """
        List of legal moves for the player with the 'color' pieces
        ----

        ----
        **Combines the following**

        1. generate candidate moves, using the basic movement rules for all pieces (the board does this calculation)
        2. add candidate castling moves
        3. add candidate en passant moves
        4. remove illegal options --> a move that would put you in check or you are in check and the move does not get you out of it.
        5. Pawn push to promotion square? --> expand the set of moves to include one for every choice of piece type to promote into.
        """

        # generate candidate moves
        candidate_moves = self.board.generate_candidate_moves(color)

        # castling moves
        if self._can_castle():
            castling_moves = self._generate_castling_moves()
            candidate_moves.extend(castling_moves)

        # En passant moves
        if self.state.en_passant_square is not None:
            en_passant_moves = self._generate_en_passant_moves(
                self.state.en_passant_square
            )
            candidate_moves.extend(en_passant_moves)

        # keep those moves that do not put (or leave) you in check
        legal_moves_wo_promotions: list[Move] = [
            move
            for move in candidate_moves
            if not self._is_putting_yourself_in_check(move)
        ]

        # promotion rule: find pawn pushes to final / first rank
        legal_moves: list[Move] = []
        for move in legal_moves_wo_promotions:
            if self._is_pawn_push_to_promotion_square(move):
                pawn_promotions = self._expand_pawn_promotion_moves(move)
                legal_moves.extend(pawn_promotions)
            else:
                legal_moves.append(move)

        return legal_moves

    def _create_accepted_move(self, move: Move) -> AcceptedMove:
        """Snapshot of the moving pieces before the updates are done."""
        return AcceptedMove.from_move_and_board(move, self.board)

    def _update_board(self, move: AcceptedMove) -> None:
        """
        Call for the proper updates of the Board's position
        """
        # castling move must displace two pieces on the board, but just add one to the move registry
        if move.move.castling_direction:
            self._update_board_w_castle_move(move.move.castling_direction)
        elif move.move.is_en_passant:
            self._update_board_w_en_passant(move.move)
        else:
            self.board.move_piece(move.move)

    def _update_moves(self, move: Move) -> None:
        self.moves.append(move)

    def _update_fen_state(self, accepted_move: AcceptedMove) -> None:
        """Create/update the FEN state to reflect state after move.
        NOTE this is performed BEFORE the board has been updated
        """

        # unpack previous stored snapshot
        # update FEN string / state
        self.state.position = self.board.to_fen()

        # NOTE: ask for current player's pieces color BEFORE updating this part of the FEN string
        player_color = self._get_turn_player_color()

        # update the current state's castling rights
        self._revoke_castling_rights_if_needed(accepted_move)

        # check if the move creates an en passant square
        ep_square = self._determine_en_passant_square(accepted_move)
        self.state.en_passant_square = (
            Square.from_algebraic(ep_square) if ep_square else None
        )

        # move counters
        if self._is_half_move(accepted_move):
            self.state.increment_half_move_counter()
        else:
            self.state.reset_half_move_counter()

        if player_color == Color.BLACK:
            self.state.increment_full_move_counter()

        # NOTE update color to move AFTER doing checks that depend on the last move made (revoking castling rights / checking en passant squares.)
        self.state.color_to_move = (
            Color.WHITE if player_color == Color.BLACK else Color.BLACK
        )

    def _update_fen_history(self, fen: str) -> None:
        """Before making a new move, commit the state before the prior to the move to the registry of FEN strings."""
        self.history.append(fen)

    def _update_game_status(self) -> None:
        """Performs checks to see if game has ended and changes status accordingly.

        NOTE the FEN state has already been updated. At this point the turn player is the opponent of the player making the original request.
        """
        next_player_color = self._get_turn_player_color()
        if self._is_check_mate(next_player_color):
            self._change_status(Status.CHECKMATE)

        if self._is_stale_mate(next_player_color):
            self._change_status(Status.STALEMATE)

        if self._is_three_fold_repetition():
            self._change_status(Status.DRAW_REPETITION)

    def _change_status(self, new_status: Status) -> None:
        self.status = new_status

    # -- LEGAL MOVES HELPERS ---
    def _is_putting_yourself_in_check(self, move: Move) -> bool:
        """Return True if the move puts you in check

        plan:
        1. Copy the board
        2. make the candidate move
        3. determine if king is in check on the new board
        """
        board = deepcopy(self.board)

        if move.castling_direction:
            self._move_castling_pieces(board, move.castling_direction)
        else:
            board.move_piece(move)
        player_color = self._get_turn_player_color()
        return board.is_check(player_color)

    # --- CHECKS FOR ENDING THE GAME ---
    def _has_legal_move(self, color: Color) -> bool:
        return len(self._generate_legal_moves(color)) > 0

    def _is_check(self, color: Color) -> bool:
        """You've put your opponent in check"""
        return self.board.is_check(color)

    def _is_check_mate(self, color: Color) -> bool:
        return self._is_check(color) and not self._has_legal_move(color)

    def _is_stale_mate(self, color: Color) -> bool:
        return not self._is_check(color) and not self._has_legal_move(color)

    def _is_three_fold_repetition(self) -> bool:
        """Check if the new FEN occurs 3 times in the history"""

        # TODO: Check if there is some nicer way of doing this.
        new_fen = self.state.to_fen()
        count = 0
        for previous_fen in self.history:
            if new_fen == previous_fen:
                count += 1
            if count == 3:
                return True
        return False

    def _is_half_move_draw(self) -> bool:
        """If you reach 50 consecutive half-moves, your reached a draw"""
        return self.state.half_move_clock >= 50

    # -- CASTLING RULE HELPERS ---
    def _generate_castling_moves(self) -> list[Move]:
        """Use CASTLING_RULES to construct corresponding set of moves"""
        legal_castling_directions = self._legal_castling_directions()
        return [
            candidate_castling_move(direction)
            for direction in legal_castling_directions
        ]

    def _can_castle(self) -> bool:
        """
        Do you have any legal castling direction?
        """
        return bool(self._legal_castling_directions())

    def _legal_castling_directions(self) -> list[CastlingDirection]:
        """
        Find the legal castling directions for the player currently attempting to move
        ---

        **you are allowed to castle if**

        * You are not currently put in check (you cannot castle out of check).
        * Castling rights are not yet revoked.
        * There is no square in between the two pieces (the king and the rook of choice) that is under attack.
        """
        player_color = self._get_turn_player_color()
        # Cannot castle out of a check.
        if self._is_check(player_color):
            return []

        # Cannot castle if rights previously revoked.
        if not self._has_any_castling_rights(player_color):
            return []

        # Now need to check specific castling rights
        legal_directions: list[CastlingDirection] = []
        opponent_color = self._get_opponent_color()
        player_castling_directions = self.state.castling_options(player_color)
        for direction in player_castling_directions:
            # Cannot castle if already got these rights revoked.
            if not self._has_castling_rights(direction):
                continue

            # For any of the squares between king and rook ...
            path = castling_path(direction)
            # Cannot castle if any of the squares is occupied
            if self.board.is_any_occupied(path):
                continue

            # Cannot castle if any of the squares is under attack
            if self.board.is_any_under_attack(path, opponent_color):
                continue

            # survived the checks? add to legal castling directions.
            legal_directions.append(direction)

        return legal_directions

    def _has_castling_rights(self, direction: CastlingDirection) -> bool:
        return self.state.castling_rights[direction]

    def _has_any_castling_rights(self, color: Color) -> bool:
        return self.state.can_castle(color)

    def _is_castling_move(self, move: AcceptedMove) -> bool:
        """Check if the king move is a castling move"""
        return move.move.castling_direction is not None

    def _is_king_move(self, move: AcceptedMove) -> bool:
        """Once moved, castling rights in both directions get revoked"""
        return move.moving_piece.type == PieceType.KING

    def _is_rook_move(self, move: AcceptedMove) -> bool:
        """Once moved, the castling rights in the direction of that rook get revoked"""
        return move.moving_piece.type == PieceType.ROOK

    def _is_opponent_rook_capture(self, move: AcceptedMove) -> bool:
        """If the rook gets captured before it moved, castling rights are also revoked."""
        opponent_color = self._get_opponent_color()
        return move.captured_piece == Piece(PieceType.ROOK, opponent_color)

    def _revoke_castling_rights_if_needed(self, move: AcceptedMove) -> None:
        """
        Checks which rights should get revoked
        ----

        1. If you are castling this move --> revoke both
        2. If you are moving your king --> revoke both
        3. If you are moving your rook (for the first time) --> revoke one of the two rights
        4. If you are taking your opponents rook --> if it is on the starting square --> revoke one of your opponent's rights
        """

        player_color = self._get_turn_player_color()
        opponent_color = self._get_opponent_color()
        player_has_rights = self._has_any_castling_rights(player_color)
        opponent_has_rights = self._has_any_castling_rights(opponent_color)

        # 1: Revoke all your rights if you now castle
        if player_has_rights and self._is_castling_move(move):
            self.state.revoke_all_castling_rights(player_color)

        # 2: Revoke all your rights if you move your king for the first time.
        if player_has_rights and self._is_king_move(move):
            self.state.revoke_all_castling_rights(player_color)

        # 3: IF you still have your right to castle AND you move your rook --> revoke rights to castle in associated direction.
        if player_has_rights and self._is_rook_move(move):
            player_castling_directions = self.state.castling_options(player_color)
            for direction in player_castling_directions:
                rook_starting_square, _ = castling_rook_squares(direction)
                if move.move.from_square == rook_starting_square:
                    self.state.revoke_castling_rights(direction)
                    break

        # 4: IF you take your opponent's rook before they have their rights revoked --> revoke rights to castle in associated direction.
        if opponent_has_rights and self._is_opponent_rook_capture(move):
            opponent_castling_directions = self.state.castling_options(opponent_color)
            for direction in opponent_castling_directions:
                rook_starting_square, _ = castling_rook_squares(direction)
                if move.move.to_square == rook_starting_square:
                    self.state.revoke_castling_rights(direction)
                    break

    def _update_board_w_castle_move(self, direction: CastlingDirection) -> None:
        """
        Board update with the castling move:
        ---

        Move both the king and the rook in accordance with the castling move associated to the given direction.
        """
        self._move_castling_pieces(self.board, direction)

    def _move_castling_pieces(self, board: Board, direction: CastlingDirection) -> None:
        """Move both the King and the Rook"""
        squares = CASTLING_RULES[direction]
        king_move = Move(from_square=squares.king_from, to_square=squares.king_to)
        rook_move = Move(from_square=squares.rook_from, to_square=squares.rook_to)
        board.move_piece(king_move)
        board.move_piece(rook_move)

    # --- EN PASSANT RULE HELPERS ----
    def _determine_en_passant_square(self, move: AcceptedMove) -> Optional[str]:
        """The possible en passant square for the next turn."""
        ranks_moved = abs(move.move.from_square.rank - move.move.to_square.rank)
        if self._is_pawn_move(move) and (ranks_moved == 2):
            player_color = self._get_turn_player_color()
            # white moves UP the board, black moves DOWN
            direction = 1 if player_color == Color.WHITE else -1
            en_passant_square = Square(
                file=move.move.from_square.file,
                rank=move.move.from_square.rank + direction,
            )
            return en_passant_square.to_algebraic()

    def _generate_en_passant_moves(self, en_passant_square: Square) -> list[Move]:
        """
        Function in moves.py checks the board to see if any of your pawns are on the correct squares to perform an en passant move.
        """
        player_color = self._get_turn_player_color()
        return en_passant_moves(
            en_passant_square=en_passant_square,
            color=player_color,
            board=self.board,
        )

    def _update_board_w_en_passant(self, move: Move) -> None:
        """
        Update the board after the en passant move.
        ---

        1. Move the pawn diagonally
        2. Remove the opponent's pawn that gets taken

        NOTE The pawn removed was standing in the same file as the en_passant square.
        NOTE ,, ,, the same rank as the moving pawn was originally standing at.
        """

        # for the typechecker: This function is only called when you know you can en_passant
        assert self.state.en_passant_square

        # make the original move (this moves the pawn diagonally onto the en passant square)
        self.board.move_piece(move)

        # take on the square where the enemy pawn is standing
        en_passant_square = self.state.en_passant_square
        take_square = Square(file=en_passant_square.file, rank=move.from_square.rank)
        self.board.remove_piece(take_square)

    def _move_en_passant_pieces(self, board: Board, move: Move) -> None:
        """"""

    # -- PROMOTION RULE HELPERS ---
    def _is_pawn_push_to_promotion_square(self, move: Move) -> bool:
        """Wraps around method in moves.py"""
        return is_pawn_push_to_promotion_square(move, self.board)

    def _expand_pawn_promotion_moves(self, pawn_push: Move) -> list[Move]:
        """Create multiple legal moves --> One for every piece type the pawn can promote into."""
        return pawn_pushes_w_promotion(pawn_push)

    def _promote_pawn(self, move: Move) -> None:
        """promote the pawn on the target square"""
        # for the type checker
        assert move.promote_to is not None
        self.board.promote_piece(move.to_square, to=move.promote_to)

    # --- HALF MOVE CLOCK HELPERS ---
    def _is_half_move(self, move: AcceptedMove) -> bool:
        return (not self._is_pawn_move(move)) and (not self._is_capture(move))

    def _is_pawn_move(self, move: AcceptedMove) -> bool:
        return move.moving_piece.type == PieceType.PAWN

    def _is_capture(self, move: AcceptedMove) -> bool:
        return bool(move.captured_piece)
