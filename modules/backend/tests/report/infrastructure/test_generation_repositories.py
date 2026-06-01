from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.contexts.report.infrastructure.generation_repositories import SqlAlchemyReportInstanceRepository
from src.infrastructure.persistence.database import Base
from tests.support.builders import build_flow_report


def test_report_repository_hides_other_users_report():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    repository = SqlAlchemyReportInstanceRepository(session)

    repository.create(
        report_id="rpt_owned",
        template_id="tpl_shared",
        template_instance_id="ti_owned",
        user_id="user-a",
        conversation_id="conv_owned",
        chat_id="chat_owned",
        status="available",
        schema_version="1.0.0",
        report=build_flow_report(),
    )

    assert repository.get("rpt_owned", user_id="user-a") is not None
    assert repository.get("rpt_owned", user_id="user-b") is None
