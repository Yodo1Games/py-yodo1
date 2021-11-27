# Yodo1 Python Toolkit

Includes

- sso auth
- sqlalchemy
- Rabbit MQ Consumer
- Progress Bar
- Logger
- pydantic

## Install

```shell
pip install yodo1-toolkit
```



## SSO

### Setup

Create base instance on `app/base.py` file.

```python
from typing import Dict
from fastapi import Depends
from yodo1.sso import JWTHelper, JWTPayload

auth = JWTHelper()

# Define helper class
# This is to add custom operation after get user info, like setup APM context
# https://www.elastic.co/guide/en/apm/agent/python/master/api.html#api-set-user-context
def get_current_user_dict(payload: JWTPayload = Depends(auth.current_payload)) -> Dict:
  elasticapm.set_user_context(username=payload.name,
                              email=payload.email,
                              user_id=payload.sub)
  return {
    'sub': payload.sub,
    'email': payload.email,
  }

```

Setup public key when api startup

```python
from fastapi import FastAPI
from app.base import auth

app = FastAPI()


@app.on_event("startup")
async def startup_event() -> None:
  # Setup public key via sso verser url, this is path to public_key file.
  auth.setup_with_sso_server('<public_key_url>')

  # Or just setup with piblic_key str
  # >>> public_key = "-----BEGIN PUBLIC KEY-----\nMIICIjANBgkqhkiG9w0BA ..."
  # >>> auth.setup_keys(public_key=public_key)
```

### User with FastAPI

```python
from app.base import auth, get_current_user_dict
from yodo1.sso import JWTPayload
...

# use payload without custom model
@router.get("/get_payload")
async def get_payload(
  payload: JWTPayload=Depends(auth.current_payload)):
  return f'Hello, {payload.sub}'


# use custom user model
@router.get("/user")
async def get_payload(
  payload: Dict=Depends(get_current_user_dict)):
  return f"Hello, {payload['sub']}"
```

## sqlalchemy

Create base instances on `app/base.py` file.

```python
from sqlalchemy import create_engine
from yodo1.sqlalchemy import DBManager

engine = create_engine('<db_rui>',
                       pool_size=0,
                       pool_recycle=600,
                       max_overflow=-1)

db = DBManager(engine=engine)
```

### Use with FastAPI

```python
from app.base import db

...

@router.post("/update")
async def hello_world(
  payload=Depends(auth.current_payload),
  session=Depends(db.get_session)) -> ItemModel:
  item: ItemModel = session.query(ItemModel).first()
  return item

...
```

### Use without FastAPI

```python
from app.base import db

session = db.SessionLocal()
session.query(Model).all()
session.commit()
session.close()
```

### Define Model

```python
from sqlalchemy import (
  INTEGER,
  Column,
  TEXT
)
from yodo1.sqlalchemy import BaseDBModel


class ItemModel(BaseDBModel):
  __tablename__ = "item_list"
  __table_args__ = {"extend_existing": True}

  id = Column(INTEGER, primary_key=True, autoincrement=True, nullable=False)
  title = Column(TEXT, nullable=False, comment="notification title")
```

### Define Schema

```python
from yodo1.pydantic import BaseSchema, BaseDateSchema


class OutputModelSchema(BaseSchema):
  id: int
  title: str


class OutputModelWithDateSchema(BaseDateSchema):
  id: int
  title: str
```


## Rabbit MQ

### How to use Consumer

```python3
import logging
import random
import time
import pika
from yodo1.rabbitmq.multi_thread import MultiThreadConsumer, MQAction, CallbackResult

# We can change pika log level to reduce logs.
logging.getLogger("pika").setLevel(logging.INFO)
logging.basicConfig(level='DEBUG')


def demo_callback(method_frame: pika.spec.Basic.Deliver,
                  header_frame: pika.spec.BasicProperties,
                  message_body: bytes) -> CallbackResult:
    """
    Demo callback function
    :param method_frame: method_frame from MQ Message
    :param header_frame: header_frame from MQ Message
    :param message_body: MQ Message body
    :return: whether should ack
    """
    logging.info(f"Received message in Queue: {method_frame.routing_key}, delivery_tag: {method_frame.delivery_tag}")
    time.sleep(30)
    if random.random() > 0.5:
        # Failed to process, should nack with `requeue=False`
        return CallbackResult(MQAction.ack)
    else:
        # Process success, should ack
        return CallbackResult(MQAction.nack)

consumer = MultiThreadConsumer(uri="amqps://xxxx",
                               verbose=True)
consumer.setup_queue_consumer("test.consumer.a.debug",
                              handler_function=demo_callback)

try:
    consumer.start_consuming()
except KeyboardInterrupt:
    consumer.stop_consuming()

consumer.close()
```


`AsyncRabbit` is Deprecated due to stability. Please use `yodo1.rabbitmq.MultiThreadConsumerl`

```python
import json
import aio_pika
from yodo1.aio_pika import AsyncRabbit

# create a `AsyncRabbit` instance with configs.
aio_rabbit = AsyncRabbit(host=conf.MQ_HOST,
                         port=conf.MQ_PORT,
                         login=conf.MQ_USER,
                         password=conf.MQ_PASSWORD,
                         virtualhost='/' + conf.env)


# Define a callback function
async def my_callback_func(message: aio_pika.IncomingMessage) -> None:
  try:
    body = json.loads(message.body)
    event = body.get('event', None)
    if event == 'target_event':
      # Handle it and ack
      message.ack()
    else:
      # if failed to handle it nack()
      message.nack()
  except Exception as e:
    # if exception to handle it nack()
    message.nack()
  finally:
    # sleep 0.1 after nack/ack last message, ugly patch before having the x-death logic.
    time.sleep(0.1)

@app.on_event("startup")
async def startup_event() -> None:
  # Register the callback
  await aio_rabbit.register_callback(exchange_name="<cool-exchange>",
                                     queue_name="<cool-queue-name>",
                                     callback=my_callback_func)
```


## Progress Bar

A simple progress bar can display properly on k8s and Grafana.

```python
import logging
from yodo1.progress import ProgressBar

logging.basicConfig(level='DEBUG')

p = ProgressBar(total=100, desc="Hacking ...", step=5)

for i in range(100):
    p.update()
```

This is the output

```log
INFO:yodo1.progress: 12.0%  |>>>>>>                                            | 12/100 Hacking ...
INFO:yodo1.progress: 24.0%  |>>>>>>>>>>>>                                      | 24/100 Hacking ...
INFO:yodo1.progress: 36.0%  |>>>>>>>>>>>>>>>>>>                                | 36/100 Hacking ...
INFO:yodo1.progress: 48.0%  |>>>>>>>>>>>>>>>>>>>>>>>>                          | 48/100 Hacking ...
INFO:yodo1.progress: 60.0%  |>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>                    | 60/100 Hacking ...
INFO:yodo1.progress: 72.0%  |>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>              | 72/100 Hacking ...
INFO:yodo1.progress: 84.0%  |>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>        | 84/100 Hacking ...
INFO:yodo1.progress: 96.0%  |>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>  | 96/100 Hacking ...
INFO:yodo1.progress: 100.0% |>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>| 100/100 Hacking ...
```

Use it with ThreadPoolExecutor.

```python
progress = ProgressBar(total=1000, desc="Processing... ")

with ThreadPoolExecutor(max_workers=20) as executor:
    for index, row in df.iterrows():
        future = executor.submit(do_something
                                 id=row.id)
        # Update progress bar when the job done
        future.add_done_callback(lambda x: progress.update())
```
