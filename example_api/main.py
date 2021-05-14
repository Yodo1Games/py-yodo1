from typing import Dict, List

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from example_api.base import auth, get_current_user_dict, db
from example_api.keys import PUBLIC_KEY_URL
from example_api.model import ItemModel, ItemOutSchema, ItemOutDateSchema
from yodo1.logger import logger

description = """
Api endpoint for PA2 project, auth via yodo1-sso service with `api/yodo1/login` endpoint.
"""

app = FastAPI(version='0.0.1',
              description=description)


@app.on_event("startup")
async def startup_event() -> None:
    auth.setup_with_sso_server(PUBLIC_KEY_URL)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info('Shutdown events')


@app.get("/health_check", response_model=Dict)
async def health_check() -> Dict:
    return {'health': 'normal'}


@app.get("/secret_data", response_model=Dict)
async def health_check(user: Dict = Depends(get_current_user_dict)) -> Dict:
    return {'secret': 'true', 'user': user}


@app.get('items', response_model=List[ItemOutSchema])
async def get_items(session: Session = Depends(db.get_session)):
    return session.query(ItemModel).all()


@app.get('items_with_date', response_model=List[ItemOutDateSchema])
async def get_items(session: Session = Depends(db.get_session)):
    return session.query(ItemModel).all()
