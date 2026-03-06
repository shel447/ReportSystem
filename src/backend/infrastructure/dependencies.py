from __future__ import annotations

from sqlalchemy.orm import Session

from ..ai_gateway import OpenAICompatGateway
from ..application.reporting.services import InstanceApplicationService, ScheduledRunApplicationService
from ..domain.reporting.services import OutlineExpansionService
from .reporting.repositories import (
    OpenAIContentGenerator,
    SqlAlchemyInstanceRepository,
    SqlAlchemyTemplateRepository,
)



def build_instance_application_service(db: Session) -> InstanceApplicationService:
    template_repo = SqlAlchemyTemplateRepository(db)
    instance_repo = SqlAlchemyInstanceRepository(db)
    generator = OpenAIContentGenerator(db, gateway=OpenAICompatGateway())
    return InstanceApplicationService(
        template_reader=template_repo,
        instance_writer=instance_repo,
        content_generator=generator,
        outline_expansion_service=OutlineExpansionService(),
    )



def build_scheduled_run_application_service(db: Session) -> ScheduledRunApplicationService:
    instance_service = build_instance_application_service(db)
    instance_repo = SqlAlchemyInstanceRepository(db)
    return ScheduledRunApplicationService(
        instance_service=instance_service,
        instance_reader=instance_repo,
    )
