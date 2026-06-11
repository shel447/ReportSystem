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
from .persistence.db_ctx import db_session
from .messaging import AfterCommitMessagePublisher
from .platform.runtime import message_center


@contextmanager
def report_service_scope():
    message_publisher = AfterCommitMessagePublisher(publisher=message_center)
    try:
        with db_session(reraise=True) as session:
            service = build_report_service(session, message_publisher=message_publisher)
            yield service
    except Exception:
        message_publisher.discard()
        raise
    message_publisher.flush()


@contextmanager
def conversation_service_scope():
    message_publisher = AfterCommitMessagePublisher(publisher=message_center)
    try:
        with db_session(reraise=True) as session:
            dataset_query_gateway = build_data_query_gateway()
            data_analysis_service = build_data_analysis_service()
            service = _build_conversation_service(
                scenario_providers=[
                    build_report_scenario_provider(
                        session,
                        dataset_query_gateway=dataset_query_gateway,
                        message_publisher=message_publisher,
                    ),
                    build_data_analysis_scenario_provider(service=data_analysis_service),
                ],
                subflow_specs=data_analysis_service.subflow_specs(),
            )
            yield service
    except Exception:
        message_publisher.discard()
        raise
    message_publisher.flush()


__all__ = ["conversation_service_scope", "report_service_scope"]
