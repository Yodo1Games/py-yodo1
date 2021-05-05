import datetime

from pydantic import BaseModel


class BaseSchema(BaseModel):
    class Config:
        orm_mode = True
        json_encoders = {
            datetime.datetime: lambda dt: dt.strftime('%Y-%m-%d %H:%M:%SZ'),
            datetime.date: lambda dt: dt.strftime('%Y-%m-%d 00:00:00Z')
        }


class BaseDateSchema(BaseSchema):
    created_at: datetime.datetime
    updated_at: datetime.datetime


__all__ = [
    'BaseSchema',
    'BaseDateSchema'
]
