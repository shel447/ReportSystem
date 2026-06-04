"""Top-level service accessors used by routers.

The top-level layer calls context-owned composition builders only. Business
interfaces and adapters are owned by their requesting context.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..contexts.conversation.infrastructure.composition import build_conversation_service as _build_conversation_service
from ..contexts.data_analysis.infrastructure.composition import (
    build_data_analysis_scenario_provider,
    build_data_query_gateway,
)
from ..contexts.report.infrastructure.composition import (
    build_report_scenario_provider,
    build_report_service,
)


def build_conversation_service(db: Session):
    dataset_query_gateway = build_data_query_gateway()
    return _build_conversation_service(
        db,
        scenario_providers=[
            build_report_scenario_provider(db, dataset_query_gateway=dataset_query_gateway),
            build_data_analysis_scenario_provider(),
        ],
    )


__all__ = ["build_conversation_service", "build_report_service"]
