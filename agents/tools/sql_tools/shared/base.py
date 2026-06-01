"""Base compartilhada dos schemas das SQL tools."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class SqlToolBaseSchema(BaseModel):
    """Config e serializacao compartilhadas para schemas de tools SQL."""

    model_config = ConfigDict(extra="ignore")

    def to_metadata_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)
