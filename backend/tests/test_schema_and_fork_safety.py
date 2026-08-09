"""Model/schema hygiene and Celery fork-safety (audit AUDIT-2.md H6/H7/H8).

No real Postgres needed for any of these -- they inspect the SQLAlchemy
model metadata and the fork-safety hook in isolation.
"""

from unittest.mock import MagicMock, patch

from sqlalchemy.schema import CreateTable

from app.models.job import Job
from app.models.prospect import Prospect


def test_job_has_no_dynamic_prospects_relationship():
    """audit H6: lazy="dynamic" is asyncio-incompatible and was unused --
    dropped rather than defused, so a future call site gets an immediate,
    unambiguous AttributeError instead of a confusing runtime MissingGreenlet."""
    assert not hasattr(Job, "prospects")


def test_prospect_has_no_job_relationship():
    assert not hasattr(Prospect, "job")


def test_prospect_model_declares_dedup_unique_constraint():
    """audit H7: uq_prospects_job_id_ig_pk used to exist only in Alembic
    migration 003, not in the model -- meaning Base.metadata.create_all
    (schema-authority split the audit flags) silently built a schema
    missing it. Asserted against the rendered DDL so this doesn't need a
    real database connection."""
    ddl = str(CreateTable(Prospect.__table__).compile())
    assert "uq_prospects_job_id_ig_pk" in ddl


def test_lifespan_does_not_create_all():
    """audit H7: production schema comes from Alembic only now -- the
    Base.metadata.create_all call in main.py's lifespan is gone entirely,
    not just skipped conditionally."""
    import inspect

    from app.main import lifespan

    source = inspect.getsource(lifespan)
    assert "run_sync" not in source
    assert "Base.metadata" not in source


def test_worker_process_init_disposes_sync_engine():
    """audit H8: the fork-safety hook must actually call dispose() -- not
    just exist -- so a forked worker never inherits shared connections."""
    from app.workers.celery_app import _dispose_sync_engine_after_fork

    with patch("app.workers._sync_helpers.dispose_sync_engine") as mock_dispose:
        _dispose_sync_engine_after_fork(sender=MagicMock())

    mock_dispose.assert_called_once()


def test_dispose_sync_engine_disposes_the_real_engine():
    from app.workers import _sync_helpers

    with patch.object(_sync_helpers._sync_engine, "dispose") as mock_dispose:
        _sync_helpers.dispose_sync_engine()

    mock_dispose.assert_called_once()
