# Yodo1 Python Toolkit

- [Yodo1 Python Toolkit](#yodo1-python-toolkit)
  - [Install](#install)
  - [SSO](#sso)
    - [Setup](#setup)
    - [User with FastAPI](#user-with-fastapi)
  - [sqlalchemy](#sqlalchemy)
    - [Use with FastAPI](#use-with-fastapi)
    - [Use without FastAPI](#use-without-fastapi)
    - [Define Model](#define-model)
    - [Define Schema](#define-schema)
  - [Rabbit MQ](#rabbit-mq)
    - [How to use Consumer](#how-to-use-consumer)
      - [Consume MQ with apm enabled](#consume-mq-with-apm-enabled)
    - [How to use Sender](#how-to-use-sender)
      - [Send MQ with apm enabled](#send-mq-with-apm-enabled)
      - [Send MQ with FastAPI apm enabled](#send-mq-with-fastapi-apm-enabled)
  - [Progress Bar](#progress-bar)

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
    "sub": payload.sub,
    "email": payload.email,
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
  auth.setup_with_sso_server("<public_key_url>")

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
  return f"Hello, {payload.sub}"


# use custom user model
@router.get("/user")
async def get_payload(
  payload: Dict=Depends(get_current_user_dict)):
  return f"Hello, {payload["sub"]}"
```

## sqlalchemy

Create base instances on `app/base.py` file.

```python
from sqlalchemy import create_engine
from yodo1.sqlalchemy import DBManager

engine = create_engine("<db_rui>",
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

```python
import logging
import random
import time
import pika
from yodo1.rabbitmq.multi_thread import MultiThreadConsumer, MQAction, CallbackResult

# We can change pika log level to reduce logs.
logging.getLogger("pika").setLevel(logging.INFO)
logging.basicConfig(level="DEBUG")


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
consumer.setup_queue_consumer(queue_name="test.consumer.a.debug",
                              exchange_name="target-exchange",
                              handler_function=demo_callback)

try:
    consumer.start_consuming()
except KeyboardInterrupt:
    consumer.stop_consuming()

consumer.close()
```

#### Consume MQ with apm enabled

```python
import elasticapm
apm_client = elasticapm.Client(
      service_name="awesome-api",
      server_url="https://apm-host",
      secret_token="token",
      environment="test",
      service_version="2.0.0")

consumer = MultiThreadConsumer(uri="amqps://xxxx",
                               apm_client=apm_client,
                               verbose=True)
```

`AsyncRabbit` is Deprecated due to stability, will remove from version 0.3.0. Please use `yodo1.rabbitmq.MultiThreadConsumer`

### How to use Sender

`RabbitHttpSender` is a thread safe sender with send MQ directly using the HTTP client.

```python
import json
import aio_pika
from yodo1.rabbitmq import RabbitHttpSender

# Recommend to share one sender client for each app worker

# Init with URI
uri = "https://username:password@rabbit-host/virtualhost"
rabbit_sender = RabbitHttpSender(uri=uri)

# Make sure we have defined target queue and exchange relation on the startup
@app.on_event("startup")
async def startup_event() -> None:
    # Register the exchange.
    # We need to define the relation in the code
    rabbit_sender.declare_exchange(exchange_name="only-queue")


def do_some_magic_and_publish_to_exchange():
    do_magic()
    rabbit_sender.publish(
      exchange_name="exchange-1",
      message_body={"magic": "done"}
    )

def do_some_magic_and_publish_to_queue_withou_exchange():
    do_magic()
    # We can publish message directly to a queue using special exchange ""
    rabbit_sender.publish(
      exchange_name="",
      routing_key="target-queue-name",
      message_body={"magic": "done"}
    )
```

#### Send MQ with apm enabled

```python
import elasticapm
apm_client = elasticapm.Client(
      service_name="awesome-api-consumer",
      server_url="https://apm-host",
      secret_token="token",
      environment="test",
      service_version="2.0.0")

# init sender with apm client
uri = "https://username:password@rabbit-host/virtualhost"
rabbit_sender = RabbitHttpSender(uri=uri)

rabbit_sender.publish(
      event_name="alian-found", # Must have a event name when using apm client
      exchange_name="",
      routing_key="target-queue-name",
      message_body={"magic": "done"}
    )

rabbit_sender.publish(
      event_name="alian-found", # Must have a event name when using apm client
      exchange_name="exchange-1",
      message_body={"magic": "done"}
    )
```

#### Send MQ with FastAPI apm enabled

```python
from elasticapm.contrib.starlette import ElasticAPM, make_apm_client
from fastapi import FastAPI

apm_client = make_apm_client(
    {
        "SERVICE_NAME": "demo-api",
        "SECRET_TOKEN": "xxxx",
        "SERVER_URL": "https://apm-host",
        "ENVIRONMENT": "test",
        "SERVICE_VERSION": "1.0.0",
    }
)

app = FastAPI()
app.add_middleware(ElasticAPM, client=apm_client)

# init sender with apm client
uri = "https://username:password@rabbit-host/virtualhost"
rabbit_sender = RabbitHttpSender(uri=uri, apm_client=apm_client)

rabbit_sender.publish(
      event_name="alian-found", # Must have a event name when using apm client
      exchange_name="exchange-1",
      message_body={"magic": "done"}
    )
```

## Progress Bar

A simple progress bar can display properly on k8s and Grafana.

```python
import logging
from yodo1.progress import ProgressBar

logging.basicConfig(level="DEBUG")

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
