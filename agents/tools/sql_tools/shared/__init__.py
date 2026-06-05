"""Helpers compartilhados entre schemas das SQL tools."""

from .aggregate import (
    AggregateExecutionResult,
    build_aggregate_response,
    calculate_collection_metric,
    execute_collection_aggregate,
    execute_statement_grouped,
    execute_statement_total,
)
from .base import SqlToolBaseSchema
from .lookup import (
    LookupExecutionResult,
    build_lookup_response,
    compose_message,
    execute_collection_lookup,
    execute_statement_lookup,
)
from .normalization import normalize_model_input, normalize_selected_fields
from .validation import validate_tool_params

__all__ = [
    "AggregateExecutionResult",
    "LookupExecutionResult",
    "SqlToolBaseSchema",
    "build_aggregate_response",
    "build_lookup_response",
    "calculate_collection_metric",
    "compose_message",
    "execute_collection_aggregate",
    "execute_collection_lookup",
    "execute_statement_grouped",
    "execute_statement_lookup",
    "execute_statement_total",
    "normalize_model_input",
    "normalize_selected_fields",
    "validate_tool_params",
]
