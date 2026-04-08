"""Unit tests for src/db/sql_repository.py"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from src.db.schema import Base, Status
from src.db.sql_repository import GameModel, SQLGameRepository


@pytest.fixture(autouse=True)
def clear_db(db_session: Session) -> None:
    """
    Drops all tables (and creates them from scratch) between unit tests.
    Ensures unit tests all start from a clean slate that does not share data.
    """
    # Delete all tables
    Base.metadata.drop_all(db_session.get_bind())

    # Recreate / Start from scratch
    Base.metadata.create_all(db_session.get_bind())


def test_create_game(db_session: Session) -> None:
    """Conversion from a GameModel to DBGame for a new entry to the database."""
    # Mock game data
    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session)
    record_in_db, _ = repo.create_game(model)
    assert isinstance(record_in_db, GameModel)
    assert record_in_db == model


def test_get_game_by_id(db_session: Session) -> None:
    """Create a game, then fetch it from db."""
    # Mock game data
    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session)
    expected_game, game_id = repo.create_game(model)
    game_found = repo.get_game(game_id)
    assert isinstance(game_found, GameModel)
    assert game_found == expected_game


def test_get_unknown_game(db_session: Session) -> None:
    """
    Should return None if ID does not match anything in database.

    NOTE with an empty database, any id is a valid test case.
    """
    unknown_id = uuid4()
    repo = SQLGameRepository(db_session)
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

    repo = SQLGameRepository(db_session)
    repo.create_game(model)
    wrong_id = uuid4()
    game_found = repo.get_game(wrong_id)
    assert game_found is None


def test_update_game(db_session: Session) -> None:
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

    repo = SQLGameRepository(db_session)
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


def test_consecutive_game_updates(db_session: Session) -> None:
    """Tests that we can successfully make multiple updates to the same game."""

    # Create new record
    new = GameModel(
        current_fen="FEN string",
        history_fen=[],
        moves_uci=[],
        registered_players={"white": "player_white"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session)
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


def test_attempt_updating_unknown_game(db_session: Session) -> None:
    """
    the update_game() method should break early and return None


    NOTE here simply attempt to delete a game from an empty DB. Already confirmed with the above that this is equivalent to fetching from the wrong ID.
    """

    repo = SQLGameRepository(db_session)

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


def test_delete_game(db_session: Session) -> None:
    """Record of the game should no longer exist after deletion"""
    # Mock game data
    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session)
    created_game, game_id = repo.create_game(model)
    deleted_game = repo.delete_game(game_id)

    # the correct game should be deleted
    assert deleted_game == created_game

    # The game should no longer be available in db
    assert repo.get_game(game_id) is None


def test_attempt_deleting_unknown_game(db_session: Session) -> None:
    """
    the delete_game() method should break early and return None

    NOTE here simply attempt to delete a game from an empty DB. Already confirmed with the above that this is equivalent to fetching from the wrong ID.
    """
    unknown_id = uuid4()
    repo = SQLGameRepository(db_session)
    deleted_game = repo.delete_game(unknown_id)
    assert deleted_game is None


# --- ALLOW FOR GAME NAME ALIASES ----
def test_create_game_with_name(db_session: Session) -> None:
    """Conversion from a GameModel to DBGame for a new entry to the database."""
    # Mock game data
    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session)
    record_in_db, _ = repo.create_game(model, name="my-game")
    assert isinstance(record_in_db, GameModel)
    assert record_in_db == model


def test_name_exists_true_if_present(db_session: Session) -> None:
    """Correctly identify there already is a record with this name."""
    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    game_name = "my-game"
    repo = SQLGameRepository(db_session)
    _ = repo.create_game(model, name=game_name)
    assert repo.name_exists(game_name)


def test_name_exists_false_if_absent(db_session: Session) -> None:
    """
    Correctly identify the suggested name is unique.

    NOTE: simply never create the game in the fist place ensures it does not exist in db.
    """
    game_name = "my-game"
    repo = SQLGameRepository(db_session)
    assert not repo.name_exists(game_name)


def test_game_id_by_name(db_session: Session) -> None:
    """Should return the expected UUID."""
    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    game_name = "my-game"
    repo = SQLGameRepository(db_session)
    _, expected_id = repo.create_game(model, name=game_name)
    found_id = repo.get_id_by_name(game_name)
    assert isinstance(found_id, UUID)
    assert found_id == expected_id


def test_game_id_by_name_returns_none_if_absent(db_session: Session) -> None:
    """
    If return None if no record is found (can be used in other layers to raise exception).

    NOTE: simply never create the game in the fist place ensures it does not exist in db.
    """
    game_name = "my-game"
    repo = SQLGameRepository(db_session)
    found_id = repo.get_id_by_name(game_name)
    assert found_id is None


def test_name_by_game_id(db_session: Session) -> None:
    """Should return the expected game name."""
    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    expected_name = "my-game"
    repo = SQLGameRepository(db_session)
    _, game_id = repo.create_game(model, name=expected_name)
    found_name = repo.get_name_by_id(game_id)
    assert found_name is not None
    assert found_name == expected_name


def test_name_by_game_id_returns_none_if_no_record(db_session: Session) -> None:
    """
    If return None if no record is found (can be used in other layers to raise exception).

    NOTE: simply never create the game in the fist place ensures it does not exist in db.
    """

    repo = SQLGameRepository(db_session)
    non_existing_id = uuid4()
    found_name = repo.get_name_by_id(non_existing_id)
    assert found_name is None


def test_name_by_game_id_returns_none_if_name_absent(db_session: Session) -> None:
    """
    The game name is optional. Test that for an existing game (with a null-valued name), the retrieval returns None.
    """
    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session)
    _, game_id = repo.create_game(model)
    found_name = repo.get_name_by_id(game_id)
    assert found_name is None


def test_get_all_names_with_ids(db_session: Session) -> None:
    """GET to /games/names should return all the available pairs of names and corresponding UUIDs"""
    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session)
    _, first_id = repo.create_game(model, name="first-game")
    _, second_id = repo.create_game(model, name="second-game")
    _, third_id = repo.create_game(model)

    name_id_pairs = repo.get_all_name_id_pairs()
    assert set(name_id_pairs) == {
        ("first-game", first_id),
        ("second-game", second_id),
        (None, third_id),
    }


def test_get_all_games_returns_game_models(db_session: Session) -> None:
    """Return all the identifier pairs + corresponding game state data."""

    model = GameModel(
        current_fen="FEN string",
        history_fen=["FEN", "FEN", "FEN", "yep...FEN"],
        moves_uci=["UCI", "x5y7", "mock"],
        registered_players={"white": "player_white", "black": "player_black"},
        status=Status.IN_PROGRESS,
    )

    repo = SQLGameRepository(db_session)
    _, first_id = repo.create_game(model, name="first-game")
    _, second_id = repo.create_game(model, name="second-game")
    _, third_id = repo.create_game(model)

    games_data = repo.get_all_games()
    expected_result: list[tuple[UUID, GameModel]] = [
        (first_id, model),
        (second_id, model),
        (third_id, model),
    ]
    assert all(entry in games_data for entry in expected_result)


def test_get_all_games_empty_db_returns_empty_list(db_session: Session) -> None:
    """Check that calling with no stored games results in an empty list."""
    repo = SQLGameRepository(db_session)
    games_data = repo.get_all_games()
    assert games_data == []
