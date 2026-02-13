"""
Contract for the Service layer.

Domain level data model of information representing a Game.

"""

from dataclasses import dataclass


@dataclass
class GameModel:
    """Chess specific data + game handling info (players, etc.)"""

    current_fen: str
    history_fen: list[str]
    moves_uci: list[str]
    registered_players: dict[str, str]
    status: str
