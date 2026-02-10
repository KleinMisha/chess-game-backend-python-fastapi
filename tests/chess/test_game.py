"""Unit tests for /src/chess/game.py"""

from copy import deepcopy
from itertools import product
from unittest.mock import Mock, patch

import pytest

from src.chess.game import (
    CASTLING_RULES,
    Board,
    CastlingDirection,
    Color,
    FENState,
    Game,
    GameModel,
    Move,
    Piece,
    PieceType,
    Square,
    Status,
)
from src.chess.pieces import PIECE_TO_FEN
from src.core.exceptions import (
    GameStateError,
    IllegalMoveError,
    NotYourTurnError,
)

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
STARTING_POSITION = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
EMPTY_FEN = "/".join(["8"] * 8)


@pytest.fixture
def castling_board() -> Board:
    """Create a board with only the Kings and the Rooks. Ready to perform any castling move (if allowed)."""
    board = Board.from_fen(EMPTY_FEN)
    a1 = Square.from_algebraic("a1")
    e1 = Square.from_algebraic("e1")
    h1 = Square.from_algebraic("h1")
    a8 = Square.from_algebraic("a8")
    e8 = Square.from_algebraic("e8")
    h8 = Square.from_algebraic("h8")
    board.place_piece(Piece.from_fen("K"), e1)
    board.place_piece(Piece.from_fen("R"), a1)
    board.place_piece(Piece.from_fen("R"), h1)
    board.place_piece(Piece.from_fen("k"), e8)
    board.place_piece(Piece.from_fen("r"), a8)
    board.place_piece(Piece.from_fen("r"), h8)
    return board


@pytest.fixture
def kings_only_board() -> Board:
    """
    Create a board with only kings on their canonical starting squares.
    Because making a move involves inferring if a king is under attack, moves cannot played on a board without one of the kings.
    """
    board = Board.from_fen(EMPTY_FEN)
    e1 = Square.from_algebraic("e1")
    e8 = Square.from_algebraic("e8")
    white_king = Piece.from_fen("K")
    black_king = Piece.from_fen("k")
    board.place_piece(white_king, e1)
    board.place_piece(black_king, e8)
    return board


# -- CREATION LOGIC --
def test_game_creation_from_model_roundtrip() -> None:
    """Create a Game from a GameModel and convert back into GameModel"""

    # some random fen
    fen = "r3k2r/pppq1ppp/2npbn2/4p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 b kq - 3 9"

    expected_model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_1", "black": "player_2"},
        status="in_progress",
    )

    game = Game.from_model(expected_model)
    assert game.to_model() == expected_model


def test_game_from_model_builds_domain_objects() -> None:
    """
    Once created, the Game should work with objects like Board and Move
    NOTE: The moves no need to make much sense. No chess logic is being tested here. Just parsing logic
    """
    model = GameModel(
        current_fen="r3k2r/pppq1ppp/2npbn2/4p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 b kq - 3 9",
        history_fen=[],
        moves_uci=["e2e4", "e7e5"],
        registered_players={"white": "player_1", "black": "player_2"},
        status="in progress",
    )
    game = Game.from_model(model)
    assert isinstance(game.board, Board)
    assert all(isinstance(move, Move) for move in game.moves)
    assert isinstance(game.state, FENState)
    assert isinstance(game.status, Status)
    assert game.status == Status.IN_PROGRESS


def test_create_game_with_no_move_list() -> None:
    model = GameModel(
        current_fen=f"{'/'.join(['8'] * 8)} b kq - 3 9",
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_1", "black": "player_2"},
        status="in progress",
    )
    game = Game.from_model(model)
    assert game.moves == []


def test_invalid_status_name() -> None:
    """Try creating a game with a non-existing status name (just to make sure a frontend later does not make some kind of odd choice)"""
    model = GameModel(
        current_fen=f"{'/'.join(['8'] * 8)} w KQkq - 0 1",
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_1", "black": "player_2"},
        status="not_existing",
    )
    with pytest.raises(GameStateError):
        _ = Game.from_model(model)


@pytest.mark.parametrize("player_color", [Color.WHITE, Color.BLACK])
def test_creating_new_game(player_color: Color) -> None:
    """Creating a new game with canonical starting position"""

    # expected game attributes
    fen = FENState.from_fen(STARTING_FEN)
    board = Board.from_fen(fen.position)
    waiting_for_players = Status.WAITING_FOR_PLAYERS

    new_game = Game.new_game(player="player name", color=player_color.name.lower())

    assert new_game.board == board
    assert new_game.moves == []
    assert new_game.history == []
    assert new_game.state == fen
    assert new_game.players == {player_color: "player name"}
    assert new_game.status == waiting_for_players


@pytest.mark.parametrize("player_color", [Color.WHITE, Color.BLACK])
def test_creating_new_game_custom_starting_position(player_color: Color) -> None:
    """Creating a new game with a custom starting position"""

    # some arbitrary, FEN string (NOTE: Did not check if this is a valid FEN state.)
    custom_fen = "2kb1b1r/p1p1ppNp/2p2n2/3q2B1/6Q1/2NP4/PPP2PPP/R4RK1 b - e3 3 15"
    # expected game attributes
    fen = FENState.from_fen(custom_fen)
    board = Board.from_fen(fen.position)
    waiting_for_players = Status.WAITING_FOR_PLAYERS

    new_game = Game.new_game(
        player="player name", color=player_color.name.lower(), starting_fen=custom_fen
    )

    assert new_game.board == board
    assert new_game.moves == []
    assert new_game.history == []
    assert new_game.state == fen
    assert new_game.players == {player_color: "player name"}
    assert new_game.status == waiting_for_players


def test_creating_new_game_invalid_color() -> None:
    """Check no new game should get created when the color name is not part of the Color enum, aka. the available piece colors."""

    with pytest.raises(GameStateError):
        Game.new_game("player 1", "rainbow")


@pytest.mark.parametrize("first_player_color", [Color.WHITE, Color.BLACK])
def test_registering_new_player(first_player_color: Color) -> None:
    """The second player should get whatever color is left"""

    second_player_color = (
        Color.BLACK if first_player_color == Color.WHITE else Color.WHITE
    )
    game = Game.new_game("first_player", first_player_color.name.lower())
    game.register_player("second_player")
    assert game.players == {
        first_player_color: "first_player",
        second_player_color: "second_player",
    }
    assert game.status == Status.IN_PROGRESS


def test_cannot_register_3rd_player() -> None:
    """One shouldn't be able to register a third player to a game of Chess."""
    first_player_color = Color.WHITE
    game = Game.new_game("first_player", first_player_color.name.lower())
    game.register_player("second_player")
    with pytest.raises(GameStateError):
        game.register_player("third_player")


# --- WINNER ---
@pytest.mark.parametrize("winner_color", [Color.WHITE, Color.BLACK])
def test_determining_winner(winner_color: Color) -> None:
    """Test determining if the correct winner gets assigned.

    NOTE: The actual logic of looking for check mate is not tested here. Simply pretend the starting FEN immediately led to check mate.
    """

    # For you to win, it must now be the opponent's turn
    # (who asks for all valid moves and gets none returned, at which point the game knows it is checkmate)

    fen = FENState.starting_position()
    fen.color_to_move = Color.BLACK if winner_color == Color.WHITE else Color.WHITE

    model = GameModel(
        current_fen=fen.to_fen(),
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="checkmate",
    )

    game = Game.from_model(model)
    winning_player = f"player_{winner_color.name.lower()}"
    assert game.winner == winning_player


def test_no_winner() -> None:
    """
    When not checkmate, there should be no winner
    NOTE: simplest case is to generate a new game, still register two players.
    """
    game = Game.new_game("player_white", "white")
    game.register_player("player_black")
    assert game.winner is None


# --- LEGAL MOVE GENERATION ---
def test_asking_for_legal_moves_when_game_not_in_progress() -> None:
    """Make sure to not do any of the calculations if status is not IN_PROGRESS"""
    game = Game.new_game("player_white", "white")
    with pytest.raises(GameStateError):
        game.legal_moves("player_white")


def test_asking_for_legal_moves_before_your_turn() -> None:
    """Make sure to not do any of the calculations if it is not your turn yet."""
    game = Game.new_game("player_1", "white")
    game.register_player("player_2")
    with pytest.raises(NotYourTurnError):
        game.legal_moves("player_2")


def test_legal_moves_returns_uci_encodings() -> None:
    """Output should be UCI encoded moves (string-valued)."""
    game = Game.new_game("player_1", "white")
    game.register_player("player_2")

    mock_move = Move.from_uci("e2e4")
    with patch.object(
        game, attribute="_generate_legal_moves", return_value=[mock_move]
    ):
        legal_moves = game.legal_moves("player_1")

        assert legal_moves == [mock_move.to_uci()]


def test_legal_moves_equal_candidate_moves() -> None:
    """
    Simple case: No castling, no en passant, no moves that would put you in check.

    NOTE: For white's first move --> there are 20 total moves possible:
    * 8 pawns that can move either by one or two squares = 16 moves
    * 2 knights that have two options = 4 moves

    NOTE: Deliberately made the check for pawn pushes by two squares return FALSE for this test
    """
    game = Game.new_game("player_1", "white")
    game.register_player("player_2")
    with (
        patch.object(
            game, attribute="_generate_castling_moves"
        ) as mock_gen_castle_moves,
        patch.object(
            game, attribute="_generate_en_passant_moves"
        ) as mock_en_passant_moves,
        patch.object(
            game, attribute="_is_pawn_push_to_promotion_square", return_value=False
        ) as _,
        patch.object(
            game, attribute="_expand_pawn_promotion_moves"
        ) as mock_expand_promotions,
    ):
        legal_moves = game.legal_moves("player_1")

        mock_en_passant_moves.assert_not_called()
        mock_gen_castle_moves.assert_not_called()
        mock_expand_promotions.assert_not_called()
        assert len(legal_moves) == 20


def test_legal_moves_not_all_candidate_moves() -> None:
    """Test candidate moves get filtered: only moves that do not put you in check remain."""
    fen = f"{EMPTY_FEN} w - - 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)
    black_rook = Piece(PieceType.ROOK, Color.BLACK)
    white_king = Piece(PieceType.KING, Color.WHITE)
    black_king = Piece(PieceType.KING, Color.BLACK)
    h8 = Square.from_algebraic("h8")
    g1 = Square.from_algebraic("g1")
    d4 = Square.from_algebraic("d4")
    game.board.place_piece(black_rook, h8)
    game.board.place_piece(white_king, g1)
    game.board.place_piece(black_king, d4)

    # Normally, the king can move to 5 squares. The rook should block 2 of those options
    legal_moves = game.legal_moves("player_white")
    assert len(legal_moves) == 3
    assert set(legal_moves) == set(["g1f1", "g1f2", "g1g2"])


def test_legal_moves_w_promotion() -> None:
    """
    Make sure moves are included for every kind of promotion

    NOTE: A pawn can promote into a KNIGHT, ROOK, BISHOP, OR QUEEN = 4 options
    """
    fen = f"{EMPTY_FEN} w - - 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    white_king = Piece(PieceType.KING, Color.WHITE)
    black_king = Piece(PieceType.KING, Color.BLACK)
    e1 = Square.from_algebraic("e1")
    e8 = Square.from_algebraic("e8")
    game.board.place_piece(white_king, e1)
    game.board.place_piece(black_king, e8)
    d7 = Square.from_algebraic("d7")
    white_pawn = Piece(PieceType.PAWN, Color.WHITE)
    game.board.place_piece(white_pawn, d7)
    # check wiring, no chess logic yet
    with (
        patch.object(
            game, attribute="_generate_castling_moves"
        ) as mock_gen_castle_moves,
        patch.object(
            game, attribute="_generate_en_passant_moves"
        ) as mock_en_passant_moves,
        patch.object(
            game, attribute="_expand_pawn_promotion_moves"
        ) as mock_expand_promotions,
    ):
        game.legal_moves("player_white")
        mock_gen_castle_moves.assert_not_called()
        mock_en_passant_moves.assert_not_called()
        mock_expand_promotions.assert_called_once()

    # check behavior
    legal_moves = game.legal_moves("player_white")
    pawn_moves = set([move for move in legal_moves if move[:2] == "d7"])
    assert len(legal_moves) == 9
    assert len(pawn_moves) == 4
    assert pawn_moves == set([f"d7d8{x}" for x in ["n", "b", "r", "q"]])


def test_legal_moves_w_en_passant() -> None:
    """Include the en passant move."""
    fen = f"{EMPTY_FEN} w - d6 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    white_king = Piece(PieceType.KING, Color.WHITE)
    black_king = Piece(PieceType.KING, Color.BLACK)
    e1 = Square.from_algebraic("e1")
    e8 = Square.from_algebraic("e8")
    game.board.place_piece(white_king, e1)
    game.board.place_piece(black_king, e8)

    white_pawn = Piece(PieceType.PAWN, Color.WHITE)
    black_pawn = Piece(PieceType.PAWN, Color.BLACK)
    d5 = Square.from_algebraic("d5")
    c5 = Square.from_algebraic("c5")
    game.board.place_piece(white_pawn, c5)
    game.board.place_piece(black_pawn, d5)

    # check wiring, no chess logic yet
    with (
        patch.object(
            game, attribute="_generate_castling_moves"
        ) as mock_gen_castle_moves,
        patch.object(
            game, attribute="_generate_en_passant_moves"
        ) as mock_en_passant_moves,
        patch.object(
            game, attribute="_expand_pawn_promotion_moves"
        ) as mock_expand_promotions,
    ):
        game.legal_moves("player_white")
        mock_gen_castle_moves.assert_not_called()
        mock_en_passant_moves.assert_called_once()
        mock_expand_promotions.assert_not_called()

    # check behavior
    legal_moves = game.legal_moves("player_white")
    pawn_moves = set([move for move in legal_moves if move[:2] == "c5"])
    assert len(legal_moves) == 7
    assert len(pawn_moves) == 2
    assert pawn_moves == set(["c5c6", "c5d6"])


def test_legal_moves_w_castling() -> None:
    """Include a legal castling move."""
    fen = f"{EMPTY_FEN} w Q - 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    white_king = Piece(PieceType.KING, Color.WHITE)
    black_king = Piece(PieceType.KING, Color.BLACK)
    e1 = Square.from_algebraic("e1")
    e8 = Square.from_algebraic("e8")
    game.board.place_piece(white_king, e1)
    game.board.place_piece(black_king, e8)

    white_rook = Piece(PieceType.ROOK, Color.WHITE)
    a1 = Square.from_algebraic("a1")
    game.board.place_piece(white_rook, a1)

    # check wiring, no chess logic yet
    with (
        patch.object(
            game, attribute="_generate_castling_moves"
        ) as mock_gen_castle_moves,
        patch.object(
            game, attribute="_generate_en_passant_moves"
        ) as mock_en_passant_moves,
        patch.object(
            game, attribute="_expand_pawn_promotion_moves"
        ) as mock_expand_promotions,
    ):
        game.legal_moves("player_white")
        mock_gen_castle_moves.assert_called_once()
        mock_en_passant_moves.assert_not_called()
        mock_expand_promotions.assert_not_called()

    # check behavior
    legal_moves = game.legal_moves("player_white")
    assert len(legal_moves) == 16
    assert "e1c1" in legal_moves


def test_legal_moves_w_castling_blocked() -> None:
    """Prevent the castling move by letting an opponent bishop stare down one of the squares between king and rook."""
    fen = f"{EMPTY_FEN} w Q - 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    white_king = Piece(PieceType.KING, Color.WHITE)
    black_king = Piece(PieceType.KING, Color.BLACK)
    e1 = Square.from_algebraic("e1")
    e8 = Square.from_algebraic("e8")
    game.board.place_piece(white_king, e1)
    game.board.place_piece(black_king, e8)

    white_rook = Piece(PieceType.ROOK, Color.WHITE)
    a1 = Square.from_algebraic("a1")
    game.board.place_piece(white_rook, a1)

    black_bishop = Piece(PieceType.BISHOP, Color.BLACK)
    e4 = Square.from_algebraic("e4")
    game.board.place_piece(black_bishop, e4)

    # check wiring, no chess logic yet
    with (
        patch.object(
            game, attribute="_generate_castling_moves"
        ) as mock_gen_castle_moves,
        patch.object(
            game, attribute="_generate_en_passant_moves"
        ) as mock_en_passant_moves,
        patch.object(
            game, attribute="_expand_pawn_promotion_moves"
        ) as mock_expand_promotions,
    ):
        game.legal_moves("player_white")
        mock_gen_castle_moves.assert_not_called()
        mock_en_passant_moves.assert_not_called()
        mock_expand_promotions.assert_not_called()

    # check behavior
    legal_moves = game.legal_moves("player_white")
    assert len(legal_moves) == 15
    assert "e1c1" not in legal_moves


def test_legal_moves_cannot_castle_out_of_check() -> None:
    """Put the king in check: Should not be able to castle any longer.
    NOTE: Also checks that other pieces cannot move (as the rook cannot block the check in this position)
    """

    fen = f"{EMPTY_FEN} w Q - 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    white_king = Piece(PieceType.KING, Color.WHITE)
    black_king = Piece(PieceType.KING, Color.BLACK)
    e1 = Square.from_algebraic("e1")
    e8 = Square.from_algebraic("e8")
    game.board.place_piece(white_king, e1)
    game.board.place_piece(black_king, e8)

    white_rook = Piece(PieceType.ROOK, Color.WHITE)
    a1 = Square.from_algebraic("a1")
    game.board.place_piece(white_rook, a1)

    black_bishop = Piece(PieceType.BISHOP, Color.BLACK)
    g3 = Square.from_algebraic("g3")
    game.board.place_piece(black_bishop, g3)

    # check wiring, no chess logic yet
    with (
        patch.object(
            game, attribute="_generate_castling_moves"
        ) as mock_gen_castle_moves,
        patch.object(
            game, attribute="_generate_en_passant_moves"
        ) as mock_en_passant_moves,
        patch.object(
            game, attribute="_expand_pawn_promotion_moves"
        ) as mock_expand_promotions,
    ):
        game.legal_moves("player_white")
        mock_gen_castle_moves.assert_not_called()
        mock_en_passant_moves.assert_not_called()
        mock_expand_promotions.assert_not_called()

    # check behavior
    legal_moves = game.legal_moves("player_white")
    assert len(legal_moves) == 4
    assert "e1c1" not in legal_moves


# --- MAKING A MOVE ---
def test_make_move_when_game_not_in_progress() -> None:
    """Make sure to not do any of the calculations if status is not IN_PROGRESS"""
    game = Game.new_game("player_white", "white")
    with pytest.raises(GameStateError):
        game.make_move("e2e4", "player_white")


def test_make_move_before_your_turn() -> None:
    """Make sure to not do any of the calculations if it is not your turn yet."""
    game = Game.new_game("player_1", "white")
    game.register_player("player_2")
    with pytest.raises(NotYourTurnError):
        game.make_move("e7e5", "player_2")


def test_make_illegal_move() -> None:
    """Cannot make an illegal move."""
    game = Game.new_game("player_1", "white")
    game.register_player("player_2")

    with patch.object(
        game, attribute="_generate_legal_moves", return_value=[Move.from_uci("a1a2")]
    ) as _:
        with pytest.raises(IllegalMoveError):
            game.make_move("a1b5", "player_1")


def test_make_legal_move() -> None:
    """Make sure correct updates happen when making a legal move."""
    game = Game.new_game("player_1", "white")
    game.register_player("player_2")

    # check wiring, no chess logic
    order = Mock()
    with (
        patch.object(game, attribute="_update_fen_history") as mock_history_update,
        patch.object(game, attribute="_update_fen_state") as mock_fen_update,
        patch.object(game, attribute="_update_moves") as mock_move_update,
        patch.object(game, attribute="_update_board") as mock_board_update,
        patch.object(game, attribute="_update_game_status") as mock_status_update,
    ):
        order.attach_mock(mock_history_update, "fen_history_update")
        order.attach_mock(mock_fen_update, "current_fen_update")
        order.attach_mock(mock_move_update, "move_history_update")
        order.attach_mock(mock_board_update, "board_update")
        order.attach_mock(mock_status_update, "game_status_update")

        game.make_move("e2e4", "player_1")

        mock_history_update.assert_called_once()
        mock_fen_update.assert_called_once()
        mock_move_update.assert_called_once()
        mock_board_update.assert_called_once()
        mock_status_update.assert_called_once()

        calls = order.mock_calls
        # Should update fen history before anything else gets updated (which will mutate the FEN)
        assert calls[0][0] == "fen_history_update"

        # Board should update before you update the current FEN state.
        fen_update_idx = next(
            idx for idx, call in enumerate(calls) if call[0] == "current_fen_update"
        )
        board_update_idx = next(
            idx for idx, call in enumerate(calls) if call[0] == "board_update"
        )
        assert board_update_idx < fen_update_idx

        # Checks for new game status (end of game conditions) should happen last.
        assert calls[-1][0] == "game_status_update"


def test_increment_turn_count_after_black_moves() -> None:
    """When black makes a move, increment the full turn counter."""

    # play full turn of Game
    game = Game.new_game("player_1", "white")
    game.register_player("player_2")
    # sanity check before any moves:
    assert game.state.num_turns == 1

    # do not update after white moves
    game.make_move("e2e3", "player_1")
    assert game.state.num_turns == 1

    # check correct updates happened
    game.make_move("e7e6", "player_2")
    assert game.state.num_turns == 2


def test_count_half_move_no_pawn_move() -> None:
    """Move a piece (not a pawn) that does not capture anything"""
    game = Game.new_game("player_1", "white")
    game.register_player("player_2")
    # sanity check before any moves:
    assert game.state.half_move_clock == 0

    # move the knight
    game.make_move("g1f3", "player_1")
    assert game.state.half_move_clock == 1


def test_no_half_move_if_capture() -> None:
    """Move a piece (not a pawn) to capture another piece, half-move clock should reset"""
    board = Board.from_fen(EMPTY_FEN)
    d3 = Square.from_algebraic("d3")
    c2 = Square.from_algebraic("c2")
    e1 = Square.from_algebraic("e1")
    e8 = Square.from_algebraic("e8")
    white_bishop = Piece.from_fen("B")
    black_knight = Piece.from_fen("n")
    white_king = Piece.from_fen("K")
    black_king = Piece.from_fen("k")
    board.place_piece(white_bishop, d3)
    board.place_piece(black_knight, c2)
    board.place_piece(white_king, e1)
    board.place_piece(black_king, e8)
    model = GameModel(
        current_fen=f"{board.to_fen()} w - - 0 42",
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    # capture the knight with the bishop
    game.make_move("d3c2", "player_white")
    assert game.state.half_move_clock == 0


def test_make_move_regular() -> None:
    """Test chess logic: Make a regular move (no captures, castling, en passant, or promotion)"""
    # play turn of Game
    game = Game.new_game("player_1", "white")
    game.register_player("player_2")
    game.make_move("e2e3", "player_1")

    # independently construct expected outcomes
    fen = FENState.starting_position()
    board = Board.from_fen(fen.position)
    e2 = Square.from_algebraic("e2")
    e3 = Square.from_algebraic("e3")
    e2e3 = Move(e2, e3)
    board.move_piece(e2e3)
    fen_before = fen.to_fen()
    fen_after = FENState.from_fen(f"{board.to_fen()} b KQkq - 0 1")

    # check correct updates happened
    assert game.state == fen_after
    assert game.history == [fen_before]
    assert game.moves == [e2e3]
    assert game.board == board
    assert game.status == Status.IN_PROGRESS


def test_make_move_with_capture() -> None:
    """Test chess logic: Capture a piece. Check board gets updated properly"""
    board = Board.from_fen(EMPTY_FEN)
    d3 = Square.from_algebraic("d3")
    c2 = Square.from_algebraic("c2")
    e1 = Square.from_algebraic("e1")
    e8 = Square.from_algebraic("e8")
    white_bishop = Piece.from_fen("B")
    black_knight = Piece.from_fen("n")
    white_king = Piece.from_fen("K")
    black_king = Piece.from_fen("k")
    board.place_piece(white_bishop, d3)
    board.place_piece(black_knight, c2)
    board.place_piece(white_king, e1)
    board.place_piece(black_king, e8)
    model = GameModel(
        current_fen=f"{board.to_fen()} w - - 0 42",
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    # expected board position:
    board_after_move = Board.from_fen(EMPTY_FEN)
    board_after_move.place_piece(white_bishop, c2)
    board_after_move.place_piece(white_king, e1)
    board_after_move.place_piece(black_king, e8)

    # capture the knight with the bishop
    game.make_move("d3c2", "player_white")
    assert game.board == board_after_move


#  --- CASTLING ---
@pytest.mark.parametrize("direction", [d for d in CastlingDirection])
def test_castling_moves(direction: CastlingDirection, castling_board: Board) -> None:
    """Test wiring and chess logic: Make castling move

    NOTE: !Using a 'spy' not a 'mock' for game._generate_castling_moves() because using a mock destroys internal chess logic/ruins tests.
    """
    # start with board with only kings and rooks
    color_to_move = "white" if "WHITE" in direction.name else "black"
    fen = f"{castling_board.to_fen()} {color_to_move[0]} KQkq - 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    # castle
    rule = CASTLING_RULES[direction]
    castle_move = Move(rule.king_from, rule.king_to, castling_direction=direction)
    # test wiring. Check that castling moves have been generated
    with patch.object(
        game,
        attribute="_generate_castling_moves",
        wraps=game._generate_castling_moves,  # type: ignore
    ) as spy_gen_castle_moves:
        game.make_move(castle_move.to_uci(), f"player_{color_to_move}")
        spy_gen_castle_moves.assert_called()

    # test chess logic : reset the game
    game = Game.from_model(model)

    # expected board
    board_after_move = deepcopy(castling_board)
    board_after_move.move_pieces(
        [Move(rule.king_from, rule.king_to), Move(rule.rook_from, rule.rook_to)]
    )

    # castle
    game.make_move(castle_move.to_uci(), f"player_{color_to_move}")

    assert game.board == board_after_move
    assert game.state.castling_rights == {
        d: False if color_to_move in d.name.lower() else True for d in CastlingDirection
    }


@pytest.mark.parametrize("color", [Color.WHITE, Color.BLACK])
def test_revoke_rights_if_king_is_moved(color: Color, castling_board: Board) -> None:
    """
    Move the king? Cannot castle in either direction
    """
    # start with board with only kings and rooks
    fen = f"{castling_board.to_fen()} {color.name.lower()[0]} KQkq - 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    # king moves (depend on the color)
    king_move_uci = "e1e2" if color == Color.WHITE else "e8e7"
    game.make_move(king_move_uci, f"player_{color.name.lower()}")
    assert game.state.castling_rights == {
        d: False if color.name in d.name else True for d in CastlingDirection
    }


@pytest.mark.parametrize("direction", [d for d in CastlingDirection])
def test_revoke_rights_if_rook_is_moved(
    direction: CastlingDirection, castling_board: Board
) -> None:
    """Move the rook? Revoke that specific castling rights

    NOTE To make the test simpler, just assume you move the rook to the same location it would've if castling (could have been any move)
    """
    # start with board with only kings and rooks
    color_to_move = "white" if "WHITE" in direction.name else "black"
    fen = f"{castling_board.to_fen()} {color_to_move[0]} KQkq - 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    # move the rook
    rule = CASTLING_RULES[direction]
    rook_move = Move(rule.rook_from, rule.rook_to)
    game.make_move(rook_move.to_uci(), f"player_{color_to_move}")
    assert game.state.castling_rights == {
        d: False if d == direction else True for d in CastlingDirection
    }


def test_revoke_rights_if_black_rook_gets_captured(castling_board: Board) -> None:
    """Capture your opponent's rook? Revoke your opponent's rights to castle in that direction."""
    # start with board with only kings and rooks
    fen = f"{castling_board.to_fen()} w KQkq - 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    # White uses a bishop to capture a black rook
    game.board.place_piece(Piece.from_fen("B"), Square.from_algebraic("g7"))
    game.make_move("g7h8", "player_white")
    assert game.state.castling_rights == {
        d: False if d == CastlingDirection.BLACK_KING_SIDE else True
        for d in CastlingDirection
    }

    # Do the same check for the opposite rook
    game = Game.from_model(model)
    game.board.place_piece(Piece.from_fen("B"), Square.from_algebraic("b7"))
    game.make_move("b7a8", "player_white")
    assert game.state.castling_rights == {
        d: False if d == CastlingDirection.BLACK_QUEEN_SIDE else True
        for d in CastlingDirection
    }


def test_revoke_rights_if_white_rook_gets_captured(castling_board: Board) -> None:
    """Capture your opponent's rook? Revoke your opponent's rights to castle in that direction."""
    # start with board with only kings and rooks
    fen = f"{castling_board.to_fen()} b KQkq - 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    # White uses a bishop to capture a black rook
    game.board.place_piece(Piece.from_fen("b"), Square.from_algebraic("g2"))
    game.make_move("g2h1", "player_black")
    assert game.state.castling_rights == {
        d: True if d != CastlingDirection.WHITE_KING_SIDE else False
        for d in CastlingDirection
    }

    # Do the same check for the opposite rook
    game = Game.from_model(model)
    game.board.place_piece(Piece.from_fen("b"), Square.from_algebraic("b2"))
    game.make_move("b2a1", "player_black")
    assert game.state.castling_rights == {
        d: True if d != CastlingDirection.WHITE_QUEEN_SIDE else False
        for d in CastlingDirection
    }


# --- EN PASSANT ---
@pytest.mark.parametrize(
    "en_passant_sq, player_color",
    [
        (
            Square.from_algebraic("e6"),
            Color.WHITE,
        ),  # White can take black pawn on 6th rank
        (
            Square.from_algebraic("e3"),
            Color.BLACK,
        ),  # Black can take white pawn on 3rd rank
    ],
)
def test_en_passant_moves(
    en_passant_sq: Square, player_color: Color, kings_only_board: Board
) -> None:
    """Test wiring and chess logic: Make en passant move"""
    # prepare board position with pawns in correct locations
    rank_delta = -1 if player_color == Color.WHITE else 1
    player_pawn_sq = Square(
        file=en_passant_sq.file + 1, rank=en_passant_sq.rank + rank_delta
    )
    opponent_pawn_sq = Square(
        file=en_passant_sq.file, rank=en_passant_sq.rank + rank_delta
    )
    board = kings_only_board
    player_pawn = (
        Piece.from_fen("P") if player_color == Color.WHITE else Piece.from_fen("p")
    )
    opponent_pawn = (
        Piece.from_fen("p") if player_color == Color.WHITE else Piece.from_fen("P")
    )
    board.place_piece(player_pawn, player_pawn_sq)
    board.place_piece(opponent_pawn, opponent_pawn_sq)

    # The en-passant move: move player's pawn to en-passant square
    en_passant_move = Move(
        from_square=player_pawn_sq, to_square=en_passant_sq, is_en_passant=True
    )

    # expected board: Opponent pawn is removed, player pawn moved to the en-passant square
    board_after_move = deepcopy(board)
    board_after_move.move_piece(en_passant_move)
    board_after_move.remove_piece(opponent_pawn_sq)

    # Play the move: chess logic
    fen = f"{board.to_fen()} {player_color.name.lower()[0]} - {en_passant_sq.to_algebraic()} 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)
    game.make_move(en_passant_move.to_uci(), f"player_{player_color.name.lower()}")

    # check board position
    assert game.board == board_after_move

    # check that FEN no longer has an en passant square
    assert game.history == [fen]
    assert game.state.en_passant_square is None


@pytest.mark.parametrize(
    "en_passant_sq, player_color",
    [
        (
            Square.from_algebraic("e6"),
            Color.WHITE,
        ),  # NOTE White will attempt this en passant, but timing is off
        (
            Square.from_algebraic("e3"),
            Color.BLACK,
        ),  # NOTE Black will attempt this en passant, but timing is off
    ],
)
def test_illegal_en_passant(
    en_passant_sq: Square, player_color: Color, kings_only_board: Board
) -> None:
    """
    Attempt to play the en passant move, but simulate timing being off.
    Your opponent did NOT move their pawn by two squares in the previous move.
    i.e. no en passant square in the FEN string.
    """
    # prepare board position with pawns in correct locations
    rank_delta = -1 if player_color == Color.WHITE else 1
    player_pawn_sq = Square(
        file=en_passant_sq.file + 1, rank=en_passant_sq.rank + rank_delta
    )
    opponent_pawn_sq = Square(
        file=en_passant_sq.file, rank=en_passant_sq.rank + rank_delta
    )
    board = kings_only_board
    player_pawn = (
        Piece.from_fen("P") if player_color == Color.WHITE else Piece.from_fen("p")
    )
    opponent_pawn = (
        Piece.from_fen("p") if player_color == Color.WHITE else Piece.from_fen("P")
    )
    board.place_piece(player_pawn, player_pawn_sq)
    board.place_piece(opponent_pawn, opponent_pawn_sq)

    # Attempt to play the move, but simulate timing being off. Your opponent did NOT move their pawn by two squares in the previous move.
    # i.e. no en passant square in the FEN string
    fen = f"{board.to_fen()} {player_color.name.lower()[0]} - - 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    en_passant_move = Move(
        from_square=player_pawn_sq, to_square=en_passant_sq, is_en_passant=True
    )
    with pytest.raises(IllegalMoveError):
        game.make_move(en_passant_move.to_uci(), f"player_{player_color.name.lower()}")


@pytest.mark.parametrize(
    "pawn_push_file, color", list(product(list("abcdefgh"), [Color.WHITE, Color.BLACK]))
)
def test_determine_en_passant_square_after_pawn_push(
    pawn_push_file: str, color: Color
) -> None:
    """If you push your pawn (from the starting position) by two squares, the post-move FEN should include the appropriate en passant square."""

    en_passant_rank = 3 if color == Color.WHITE else 6
    en_passant_sq = Square.from_algebraic(f"{pawn_push_file}{en_passant_rank}")
    starting_rank = 2 if color == Color.WHITE else 7
    pawn_push_delta = 2 if color == Color.WHITE else -2

    # start from canonical starting position, easiest relevant scenario
    # (of course, it won't ever actually be BLACK to move in this position, but does not affect correctness of test. )
    fen = f"{STARTING_POSITION} {color.name.lower()[0]} KQkq - 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    pawn_push_uci = f"{pawn_push_file}{starting_rank}{pawn_push_file}{starting_rank + pawn_push_delta}"
    game.make_move(pawn_push_uci, f"player_{color.name.lower()}")
    assert game.state.en_passant_square == en_passant_sq


# --- PROMOTION ---
@pytest.mark.parametrize(
    "color, new_type",
    list(
        product(
            [Color.WHITE, Color.BLACK],
            [PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT, PieceType.QUEEN],
        )
    ),
)
def test_pawn_promotion(
    color: Color, new_type: PieceType, kings_only_board: Board
) -> None:
    """Push pawn to promotion square and promote to new piece type.

    NOTE given the tests of the methods in moves.py --> just check logic for the a-file. No need to retest all possible files.
    """
    # set up the game
    promotion_rank = 8 if color == Color.WHITE else 1
    push_by = 1 if color == Color.WHITE else -1
    pawn_sq = Square.from_algebraic(f"a{promotion_rank - push_by}")
    promotion_square = Square.from_algebraic(f"a{promotion_rank}")

    board = kings_only_board
    board.place_piece(Piece(PieceType.PAWN, color), pawn_sq)

    fen = f"{board.to_fen()} {color.name.lower()[0]} KQkq - 0 42"
    model = GameModel(
        current_fen=fen,
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status="in progress",
    )
    game = Game.from_model(model)

    # push pawn and promote
    pawn_push = f"{pawn_sq.to_algebraic()}{promotion_square.to_algebraic()}{PIECE_TO_FEN[new_type]}"
    game.make_move(pawn_push, f"player_{color.name.lower()}")

    # expected scenario
    board_after_move = deepcopy(kings_only_board)
    board_after_move.place_piece(Piece(new_type, color), promotion_square)
    assert game.board.piece(promotion_square) == Piece(new_type, color)


# --- CHECK MATE ---

# --- STALE MATE ---

# --- THREE FOLD REPETITION ---

# --- HALF CLOCK DRAW ---
