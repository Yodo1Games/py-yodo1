from sqlalchemy import (
    INTEGER,
    Column,
    TEXT
)

from yodo1.pydantic import BaseSchema, BaseDateSchema
from yodo1.sqlalchemy import BaseDBModel


class ItemModel(BaseDBModel):
    __tablename__ = "item_list"
    __table_args__ = {"extend_existing": True}

    id = Column(INTEGER, primary_key=True, autoincrement=True, nullable=False)
    title = Column(TEXT, nullable=False, comment="notification title")


class ItemOutSchema(BaseSchema):
    id: int
    title: str


class ItemOutDateSchema(BaseDateSchema):
    id: int
    title: str
