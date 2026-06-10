from src.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


class Session:
    def __init__(self):
        self.commits = self.rollbacks = self.closes = 0

    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1
    def close(self): self.closes += 1


def test_unit_of_work_commits_and_closes_explicitly():
    session = Session()
    with SqlAlchemyUnitOfWork(lambda: session) as uow:
        uow.commit()
    assert (session.commits, session.rollbacks, session.closes) == (1, 0, 1)


def test_unit_of_work_rolls_back_and_closes_on_error():
    session = Session()
    try:
        with SqlAlchemyUnitOfWork(lambda: session):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert (session.commits, session.rollbacks, session.closes) == (0, 1, 1)
