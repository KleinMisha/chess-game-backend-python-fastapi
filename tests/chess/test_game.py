"""Unit tests for /src/chess/moves.py"""

import pytest

from src.chess.game import Board, FENState, Game, GameModel, Move, Status
from src.core.exceptions import GameStateError


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
