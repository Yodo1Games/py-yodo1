import datetime
from typing import Dict, Any, List, TypeVar, Type, Generator

from sqlalchemy import Column, DateTime
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.schema import CreateTable
from sqlalchemy.sql import func

T = TypeVar("T")
Base = declarative_base()  # type: ignore


@compiles(CreateTable)
def _compile_create_table(element: Any, compiler: Any, **kwargs: Dict) -> str:
    """
    Change the table order, put created_at and updated_at at last.
    Put 3 columns from base model class (is_deleted, created_at, updated_at) at the end of the table.
    """
    element.columns = element.columns[2:] + element.columns[:2]
    return compiler.visit_create_table(element)


class BaseDBModel(Base):  # type: ignore
    __abstract__ = True

    created_at = Column(DateTime,
                        default=datetime.datetime.utcnow,
                        nullable=False)
    updated_at = Column(DateTime,
                        default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow,
                        server_onupdate=func.now(),
                        nullable=False)

    def update(self, data: Dict) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    def is_saved(self) -> bool:
        return self.created_at is not None

    def to_dict(self, target_cols: List[str] = None) -> Dict[str, Any]:
        if target_cols is None:
            target_cols = [c.name for c in self.__table__.columns]
        return {
            col: getattr(self, col, None)
            for col in target_cols
        }

    @classmethod
    def instance(cls: Type[T], session: Session, **kwargs) -> T:  # type: ignore  # noqa: F821
        """
        Get instance from db or create a new one
        """
        model = session.query(cls).filter_by(**kwargs).first()
        if not model:
            model = cls(**kwargs)  # type: ignore
        return model

    @classmethod
    def time_now(cls) -> datetime.datetime:
        return datetime.datetime.utcnow()

    @classmethod
    def time_delay(cls, seconds: int) -> datetime.datetime:
        return datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)


class DBManager:
    def __init__(self, engine: Any):
        self.engine = engine
        self._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_session(self) -> Generator[None, Session, None]:
        db = None
        try:
            db = self.SessionLocal()
            yield db
        finally:
            if db:
                db.close()

    def SessionLocal(self) -> Session:
        return self._SessionLocal()

    def session(self) -> Session:
        return self.SessionLocal()


__all__ = [
    'Base',
    'BaseDBModel',
    'DBManager'
]
