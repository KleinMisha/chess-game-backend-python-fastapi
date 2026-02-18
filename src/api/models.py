"""Requests and Response models"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from src.core.exceptions import InvalidRequestError
from src.core.shared_types import Color, PieceType

PieceColor = str
PlayerName = str


# --- REQUEST MODELS ---
class CreateGameRequest(BaseModel):
    player_name: str
    color: Color
    starting_fen: Optional[str]

    @field_validator("starting_fen")
    @classmethod
    def validate_starting_fen(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        parts = value.strip().split(" ")
        if len(parts) != 6:
            raise InvalidRequestError(
                "FEN string must contain 6 space-separated parts."
            )


class JoinGameRequest(BaseModel):
    game_id: UUID
    player_name: str


class LegalMovesRequest(BaseModel):
    game_id: UUID
    player_name: str


class MoveRequest(BaseModel):
    game_id: UUID
    player_name: str
    from_square: str
    to_square: str
    promote_to: Optional[PieceType]

    @field_validator(*["from_square", "to_square"])
    @classmethod
    def validate_square(cls, value: str) -> str:
        def _is_algebraic_notation(value: str) -> bool:
            if len(value) != 2:
                return False

            first_character = value[0]
            second_character = value[1]
            if not (first_character.isalpha() and second_character.isnumeric()):
                return False
            return True

        if not _is_algebraic_notation(value):
            raise InvalidRequestError(
                f"Cannot interpret from_square: {value!r} as a valid square name."
            )
        return value


class GetGameRequest(BaseModel):
    game_id: UUID


class DeleteGameRequest(BaseModel):
    game_id: UUID


# --- RESPONSE MODELS ---
class GameResponse(BaseModel):
    game_id: UUID
    players: dict[PieceColor, PlayerName]
    fen_state: str
    starting_state: str
    move_history: list[str]


class LegalMovesResponse(BaseModel):
    game_id: UUID
    player_name: str
    color: Color
    legal_moves: list[str]
