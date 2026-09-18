import os
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from proxy.db.models import Base, CallLog


def test_call_log_survives_reopened_connection():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite:///{path}"
    try:
        engine1 = create_engine(db_url)
        Base.metadata.create_all(engine1)
        Session1 = sessionmaker(bind=engine1)
        s1 = Session1()
        s1.add(
            CallLog(
                session_id="persist-test",
                operation="playground",
                provider="fake",
                model="fake-model",
                guardrails={"injection": {"flagged": False}},
            )
        )
        s1.commit()
        s1.close()
        engine1.dispose()

        engine2 = create_engine(db_url)
        Session2 = sessionmaker(bind=engine2)
        s2 = Session2()
        rows = s2.query(CallLog).filter_by(session_id="persist-test").all()
        s2.close()
        engine2.dispose()

        assert len(rows) == 1
        assert rows[0].provider == "fake"
    finally:
        os.remove(path)
