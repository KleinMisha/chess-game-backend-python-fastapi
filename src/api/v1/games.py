"""Router for Game service."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.v1.models import (
    CreateGameRequest,
    GameResponse,
    JoinGameRequest,
    LegalMovesRequest,
    LegalMovesResponse,
    MoveRequest,
)
from src.db.database import get_db
from src.db.sql_repository import SQLGameRepository
from src.services.chess_service import ChessService
from src.services.game_service import GameService

router = APIRouter()


def get_chess_service(db: Session = Depends(get_db)) -> GameService:
    """Setup dependency injection using FastAPI."""
    repository = SQLGameRepository(db)
    return ChessService(repository)


@router.post("/games", response_model=GameResponse)
def create_new_game(
    request: CreateGameRequest, service: ChessService = Depends(get_chess_service)
) -> GameResponse:
    return service.create_new_game(request)


@router.post("/games/{game_id}/players", response_model=GameResponse)
def join_game(
    game_id: UUID,
    request: JoinGameRequest,
    service: ChessService = Depends(get_chess_service),
) -> GameResponse:
    return service.join_game(game_id, request)


@router.get("/games/{game_id}", response_model=GameResponse)
def get_game_state(
    game_id: UUID, service: ChessService = Depends(get_chess_service)
) -> GameResponse:
    return service.get_game_state(game_id)


@router.get("/games/{game_id}/legal-moves", response_model=LegalMovesResponse)
def legal_moves(
    game_id: UUID,
    request: LegalMovesRequest,
    service: ChessService = Depends(get_chess_service),
) -> LegalMovesResponse:
    return service.legal_moves(game_id, request)


@router.post("/games/{game_id}/moves", response_model=GameResponse)
def make_move(
    game_id: UUID,
    request: MoveRequest,
    service: ChessService = Depends(get_chess_service),
) -> GameResponse:
    return service.make_move(game_id, request)


@router.delete("/games/{game_id}")
def delete_game(
    game_id: UUID, service: ChessService = Depends(get_chess_service)
) -> None:
    return service.delete_game(game_id)
