"""Router for Game service."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.v1.models import (
    CreateGameRequest,
    GameIdentifiers,
    GameResponse,
    JoinGameRequest,
    LegalMovesRequest,
    LegalMovesResponse,
    MoveRequest,
)
from src.db.database import get_db
from src.db.sql_repository import SQLGameRepository
from src.services.chess_service import ChessService

router = APIRouter()


def get_chess_service(db: Session = Depends(get_db)) -> ChessService:
    """Setup dependency injection using FastAPI."""
    repository = SQLGameRepository(db)
    return ChessService(repository)


@router.get("/games", response_model=list[GameResponse])
def get_all_games(
    service: ChessService = Depends(get_chess_service),
) -> list[GameResponse]:
    return service.get_all_games()


@router.post("/games", response_model=GameResponse)
def create_new_game(
    request: CreateGameRequest, service: ChessService = Depends(get_chess_service)
) -> GameResponse:
    return service.create_new_game(request)


@router.get("/games/identifiers")
def get_game_name_id_pairs(
    service: ChessService = Depends(get_chess_service),
) -> list[GameIdentifiers]:
    return service.get_all_name_id_pairs()


@router.post("/games/{identifier}/players", response_model=GameResponse)
def join_game(
    identifier: str,
    request: JoinGameRequest,
    service: ChessService = Depends(get_chess_service),
) -> GameResponse:
    return service.join_game(identifier, request)


@router.get("/games/{identifier}", response_model=GameResponse)
def get_game_state(
    identifier: str, service: ChessService = Depends(get_chess_service)
) -> GameResponse:
    return service.get_game_state(identifier)


@router.get("/games/{identifier}/legal-moves", response_model=LegalMovesResponse)
def legal_moves(
    identifier: str,
    player_name: str,
    service: ChessService = Depends(get_chess_service),
) -> LegalMovesResponse:
    request = LegalMovesRequest(player_name=player_name)
    return service.legal_moves(identifier, request)


@router.post("/games/{identifier}/moves", response_model=GameResponse)
def make_move(
    identifier: str,
    request: MoveRequest,
    service: ChessService = Depends(get_chess_service),
) -> GameResponse:
    return service.make_move(identifier, request)


@router.delete("/games/{identifier}")
def delete_game(
    identifier: str, service: ChessService = Depends(get_chess_service)
) -> None:
    return service.delete_game(identifier)
