"""
Boundary layer data model(s).

These objects can be used to communicate with the Service.
Hence, both the API layer (higher) and domain/db layers (lower) will use model(s) defined here to send to/receive from the Service
(Decouples the data model specific to the DB layer, API layer, or domain layer from the information needed to send across boundaries)
"""

from dataclasses import dataclass

# Type aliases to make GameModel easier to read
PieceColor = str
PlayerName = str


@dataclass
class GameModel:
    """Transport-safe representation of a chess game used between API, Service, DB, and Game layers."""

    current_fen: str
    history_fen: list[str]
    moves_uci: list[str]
    registered_players: dict[PieceColor, PlayerName]
    status: str
