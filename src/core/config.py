import logging
from pathlib import Path

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    app_name: str = "Chess FastAPI"
    api_version: str = "v1"
    db_name: str = "chess_games.db"
    log_level: str = (
        "info"  # choose from: "debug", "info", "warning", "error", "critical"
    )

    @property
    def api_prefix(self) -> str:
        return f"/api/{self.api_version}"

    @property
    def db_url(self) -> str:
        """place database in project root"""
        base_dir = Path(__file__).resolve().parent.parent.parent
        return f"sqlite:///{base_dir / self.db_name}"

    @property
    def logging_level(self) -> int:
        """Convert logging level name to numerical value (integer) / Enumerated value used by logging library."""
        level_name = self.log_level.upper()
        if not hasattr(logging, level_name):
            raise ValueError(f"Unknown logging level: {self.log_level}")
        return getattr(logging, level_name)

    @property
    def is_debug(self) -> bool:
        return self.logging_level == logging.DEBUG


# expose an instance, so it can be read in other files.
config = Config()
