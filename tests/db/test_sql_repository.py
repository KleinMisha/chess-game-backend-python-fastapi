"""Unit tests for src/db/sql_repository.py"""

from uuid import uuid4

from sqlalchemy.orm import Session

from src.db.schema import Status
from src.db.sql_repository import GameModel, SQLGameRepository


def test_create_game(db_session_repo: Session) -> None:
    """Conversion from a GameModel to DBGame for a new entry to the database."""
    # Mock game data
    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session_repo)
    record_in_db, _ = repo.create_game(model)
    assert isinstance(record_in_db, GameModel)
    assert record_in_db == model


def test_get_game_by_id(db_session_repo: Session) -> None:
    """Create a game, then fetch it from db."""
    # Mock game data
    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session_repo)
    expected_game, game_id = repo.create_game(model)
    game_found = repo.get_game(game_id)
    assert isinstance(game_found, GameModel)
    assert game_found == expected_game


def test_get_unknown_game(db_session_repo: Session) -> None:
    """
    Should return None if ID does not match anything in database.

    NOTE with an empty database, any id is a valid test case.
    """
    unknown_id = uuid4()
    repo = SQLGameRepository(db_session_repo)
    game_found = repo.get_game(unknown_id)
    assert game_found is None

    # Now do it with creating a game, but retrieving from the wrong ID
    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session_repo)
    repo.create_game(model)
    wrong_id = uuid4()
    game_found = repo.get_game(wrong_id)
    assert game_found is None


def test_update_game(db_session_repo: Session) -> None:
    """
    Update an earlier created record.
    """
    # Create new record
    new = GameModel(
        current_fen="FEN string",
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session_repo)
    _, game_id = repo.create_game(new)

    # Update data and check if recorded data matches the data after the update
    after = GameModel(
        current_fen="FEN string",
        history_fen=["FEN"],
        moves_uci=["uci_move"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )
    updated_game = repo.update_game(game_id, after)
    assert updated_game is not None
    assert updated_game == after


def test_consecutive_game_updates(db_session_repo: Session) -> None:
    """Tests that we can successfully make multiple updates to the same game."""

    # Create new record
    new = GameModel(
        current_fen="FEN string",
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session_repo)
    _, game_id = repo.create_game(new)

    # make some updates "loosely simulate real scenario"
    first_update = GameModel(
        current_fen="starting FEN",
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    second_update = GameModel(
        current_fen="FEN1",
        history_fen=["starting FEN"],
        moves_uci=["move_1"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    third_update = GameModel(
        current_fen="FEN2",
        history_fen=["starting FEN", "FEN2"],
        moves_uci=["move_1", "move_2"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    repo.update_game(game_id, first_update)
    repo.update_game(game_id, second_update)
    repo.update_game(game_id, third_update)

    # now fetch it from db and assert (a little more explicit here, just for good measure)
    after_all_updates = repo.get_game(game_id)
    assert after_all_updates is not None
    assert after_all_updates == third_update


def test_attempt_updating_unknown_game(db_session_repo: Session) -> None:
    """
    the update_game() method should break early and return None


    NOTE here simply attempt to delete a game from an empty DB. Already confirmed with the above that this is equivalent to fetching from the wrong ID.
    """

    repo = SQLGameRepository(db_session_repo)

    # Update data and check if recorded data matches the data after the update
    unknown_id = uuid4()
    after = GameModel(
        current_fen="FEN string",
        history_fen=["FEN"],
        moves_uci=["uci_move"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )
    updated_game = repo.update_game(unknown_id, after)
    assert updated_game is None


def test_delete_game(db_session_repo: Session) -> None:
    """Record of the game should no longer exist after deletion"""
    # Mock game data
    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session_repo)
    created_game, game_id = repo.create_game(model)
    deleted_game = repo.delete_game(game_id)

    # the correct game should be deleted
    assert deleted_game == created_game

    # The game should no longer be available in db
    assert repo.get_game(game_id) is None


def test_attempt_deleting_unknown_game(db_session_repo: Session) -> None:
    """
    the delete_game() method should break early and return None

    NOTE here simply attempt to delete a game from an empty DB. Already confirmed with the above that this is equivalent to fetching from the wrong ID.
    """
    unknown_id = uuid4()
    repo = SQLGameRepository(db_session_repo)
    deleted_game = repo.delete_game(unknown_id)
    assert deleted_game is None
