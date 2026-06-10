"""Infrastructure-owned service scopes used by the web adapter.

The top-level layer calls context-owned composition builders only. Business
interfaces and adapters are owned by their requesting context.
"""

from __future__ import annotations

from contextlib import contextmanager

from ..contexts.conversation.infrastructure.composition import build_conversation_service as _build_conversation_service
from ..contexts.data_analysis.infrastructure.composition import (
    build_data_analysis_service,
    build_data_analysis_scenario_provider,
    build_data_query_gateway,
)
from ..contexts.report.infrastructure.composition import (
    build_report_scenario_provider,
    build_report_service,
)
from .persistence.unit_of_work import SqlAlchemyUnitOfWork


@contextmanager
def report_service_scope():
    with SqlAlchemyUnitOfWork() as uow:
        service = build_report_service(uow.session)
        try:
            yield service
            uow.commit()
        except Exception:
            uow.rollback()
            raise


@contextmanager
def conversation_service_scope():
    with SqlAlchemyUnitOfWork() as uow:
        dataset_query_gateway = build_data_query_gateway()
        data_analysis_service = build_data_analysis_service()
        service = _build_conversation_service(
            scenario_providers=[
                build_report_scenario_provider(uow.session, dataset_query_gateway=dataset_query_gateway),
                build_data_analysis_scenario_provider(service=data_analysis_service),
            ],
            subflow_specs=data_analysis_service.subflow_specs(),
        )
        try:
            yield service
            uow.commit()
        except Exception:
            uow.rollback()
            raise


__all__ = ["conversation_service_scope", "report_service_scope"]
