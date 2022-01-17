import logging
import os
import random
import socket
from typing import Callable, Optional
from urllib.parse import quote

import aio_pika
import aiormq
from aio_pika import Channel, Connection


class AsyncRabbit:

    @staticmethod
    def get_uri(host: str,
                port: int,
                login: str,
                password: str,
                virtualhost: str) -> str:
        return f"amqps://{login}:{password}@{host}:{port}/{quote(virtualhost, safe='')}"

    def __init__(self,
                 url: Optional[str] = None,
                 *,
                 host: Optional[str] = None,
                 port: Optional[int] = None,
                 login: Optional[str] = None,
                 password: Optional[str] = None,
                 consumer_tag: str = None,
                 virtualhost: str = '/',
                 ssl: bool = True) -> None:
        self.url = url
        self.host = host
        self.port = port
        self.login = login
        self.password = password
        self.virtualhost = virtualhost
        self.ssl = ssl

        if self.url is None:
            self.url = AsyncRabbit.get_uri(
                host=self.host,
                port=self.port,
                login=self.login,
                password=self.password,
                virtualhost=self.virtualhost
            )

        if consumer_tag is None:
            consumer_tag = f'{socket.gethostname()}[{os.getpid()}]'

        self._consumer_tag = consumer_tag

        self._qos = 1
        self._connection: Connection = None
        self._channel: Channel = None

    async def connect(self) -> None:
        self._connection: Connection = await aio_pika.connect_robust(url=self.url)  # type: ignore
        self._channel = await self._connection.channel()  # type: ignore
        await self._channel.set_qos(self._qos)
        logging.info('Connected to Rabbit MQ')

    async def live_channel(self) -> Channel:
        if self._channel and not self._channel.is_closed:
            return self._channel
        await self.connect()
        return self._channel

    async def register_callback(self, *,
                                exchange_name: str,
                                queue_name: str,
                                callback: Callable,
                                consumer_tag: str = None) -> None:
        """
        Add new callback for queue, needs to declare queue & add it to target exchange
        """
        channel = await self.live_channel()
        exchange = await channel.get_exchange(exchange_name)
        queue = await channel.declare_queue(queue_name, durable=True)

        await queue.bind(exchange)

        if consumer_tag is None:
            consumer_tag = self._consumer_tag
        try:
            await queue.consume(callback, consumer_tag=consumer_tag)
        except aio_pika.exceptions.DuplicateConsumerTag:
            consumer_tag = f"{self._consumer_tag}-{random.randint(0, 10000):05d}"
            logging.debug(f"Consumer_tag tag duplicated, add suffix now, new: {consumer_tag}")
            await self.register_callback(exchange_name=exchange_name,
                                         queue_name=queue_name,
                                         callback=callback,
                                         consumer_tag=consumer_tag)

    async def publish(self,
                      exchange_name: str,
                      message: aio_pika.Message,
                      routing_key: str = '') -> Optional[aiormq.types.ConfirmationFrameType]:
        channel = await self.live_channel()
        exchange = await channel.declare_exchange(exchange_name,
                                                  durable=True,
                                                  type=aio_pika.ExchangeType.FANOUT)
        return await exchange.publish(
            message=message,
            routing_key=routing_key,
        )

    async def close(self) -> None:
        """
        Close Rabbit MQ connections
        """
        await self._channel.close()
        await self._connection.close()

    async def cancel(self) -> None:
        """
        Cancel consumer receive new message
        """
        await self._channel.channel.basic_cancel(self._consumer_tag)


__all__ = [
    'AsyncRabbit'
]
