from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_Session = None


def get_engine():
    global _engine, _Session
    if _engine is None:
        url = get_settings().database_url.get_secret_value()
        kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        _engine = create_engine(url, future=True, **kwargs)
        _Session = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def session():
    get_engine()
    return _Session()


def init_db() -> None:
    from ..models import tables  # noqa: F401  (register models)
    engine = get_engine()
    upgrade_owner_columns(engine)
    Base.metadata.create_all(engine)
    upgrade_knowledge_content_type(engine)
    upgrade_knowledge_evidence_columns(engine)


def upgrade_owner_columns(engine=None) -> None:
    """Add owner columns to existing databases without exposing legacy rows to new sessions."""
    engine = engine or get_engine()
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    ownership_tables = ("profiles", "assessments", "conversations")
    with engine.begin() as connection:
        for table in ownership_tables:
            if table not in existing_tables:
                continue
            columns = {column["name"] for column in inspect(connection).get_columns(table)}
            if "owner_id" not in columns:
                connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN owner_id VARCHAR(64)'))


def upgrade_knowledge_content_type(engine=None) -> None:
    """Add the knowledge classification to existing databases without changing stored documents."""
    engine = engine or get_engine()
    inspector = inspect(engine)
    if "knowledge_documents" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("knowledge_documents")}
    if "content_type" not in columns:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE knowledge_documents ADD COLUMN content_type VARCHAR(30) NOT NULL DEFAULT 'educational'"))


def upgrade_knowledge_evidence_columns(engine=None) -> None:
    """Add evidence provenance and applicability metadata to existing knowledge rows."""
    engine = engine or get_engine()
    if "knowledge_documents" not in set(inspect(engine).get_table_names()):
        return
    columns = {column["name"] for column in inspect(engine).get_columns("knowledge_documents")}
    additions = {
        "evidence_status": "VARCHAR(32) NOT NULL DEFAULT 'expert_review_required'",
        "source_access_status": "VARCHAR(32) NOT NULL DEFAULT 'not_checked'",
        "evidence_class": "VARCHAR(32) NOT NULL DEFAULT 'source_fact'",
        "state": "VARCHAR(40)",
        "districts": "JSON",
        "seasons": "JSON",
        "concern": "VARCHAR(80)",
        "source_section": "TEXT",
        "source_time_window": "TEXT",
        "weather_input_time_window": "TEXT",
        "measurement_window_status": "VARCHAR(32) NOT NULL DEFAULT 'not_assessed'",
        "threshold_details": "JSON",
        "recommendation": "TEXT",
        "limitations": "TEXT",
    }
    new_evidence_status = "evidence_status" not in columns
    with engine.begin() as connection:
        for name, sql_type in additions.items():
            if name not in columns:
                connection.execute(text(f'ALTER TABLE knowledge_documents ADD COLUMN "{name}" {sql_type}'))
        if new_evidence_status:
            connection.execute(text(
                "UPDATE knowledge_documents SET evidence_status = CASE verification_status "
                "WHEN 'verified' THEN 'source_verified' "
                "WHEN 'outdated' THEN 'source_unverified' "
                "ELSE 'expert_review_required' END"))


def reset_engine() -> None:
    global _engine, _Session
    if _engine is not None:
        _engine.dispose()
    _engine = _Session = None


def db_ok() -> bool:
    try:
        from sqlalchemy import text
        with get_engine().connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
