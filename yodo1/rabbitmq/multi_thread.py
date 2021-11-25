import enum
import functools
import logging
import os
import random
import socket
import string
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable

import pika
from pika.channel import Channel

logger = logging.getLogger('yodo1.rabbitmq')


class MQAction(enum.Enum):
    ack = 'ack'
    nack = 'nack'


class CallbackResult:
    def __init__(self,
                 action: MQAction,
                 *,
                 requeue: bool = False):
        self.action = action
        self.requeue = requeue


def demo_callback(method_frame: pika.spec.Basic.Deliver,
                  header_frame: pika.spec.BasicProperties,
                  message_body: bytes) -> CallbackResult:
    """
    Sample callback function
    :param method_frame: method_frame from MQ Message
    :param header_frame: header_frame from MQ Message
    :param message_body: MQ Message body
    :return: whether should ack
    """
    if random.random() > 0.8:
        return CallbackResult(MQAction.ack)
    else:
        return CallbackResult(MQAction.nack)


class MultiThreadConsumer:
    def __init__(self,
                 uri: str,
                 *,
                 qos: int = 10,
                 max_worker: int = 10) -> None:
        """
        :param uri: MQ URI
        :param qos: qos
        :param max_worker: thread max worker, if you want to process MQ in single thread, set it to 1.
        """
        params = pika.URLParameters(uri)
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=qos)
        self.thread_pool = ThreadPoolExecutor(max_workers=max_worker)

    def setup_queue_consumer(self,
                             queue_name: str,
                             *,
                             handler_function: Callable,
                             exchange_name: str = None,
                             consumer_tag: str = None) -> None:
        """
        Setup queue's callback function
        :param queue_name: target queue name
        :param handler_function: target callback function
        :param exchange_name: optional, exchange that needs to blind to the queue
        :param consumer_tag: optional, human-readable tag. default value is `{host_name}-{pid}-{random-string}`
        :return: None
        """
        self.channel.queue_declare(queue_name, durable=True)
        if exchange_name is not None:
            self.channel.queue_bind(queue_name, exchange=exchange_name, routing_key='')

        if consumer_tag is None:
            random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            consumer_tag = f'{socket.gethostname()}[{os.getpid()}]-{random_id}'

        queue_thread_handler = functools.partial(self._handle_message,
                                                 handler_function=handler_function)
        self.channel.basic_consume(queue_name, queue_thread_handler, consumer_tag=consumer_tag)

    def start_consuming(self):
        """
        Start consuming, will block the main thread
        """
        logger.info("Start consuming.")
        self.channel.start_consuming()

    def stop_consuming(self):
        """
        Stop consuming
        """
        self.channel.stop_consuming()
        logger.info("Stop consuming.")

    def close(self):
        """
        Close the consumer and handle remaining received messages.
        """
        logger.info("Consumer Closing... Please wait until all messages consumed.")
        self.thread_pool.shutdown(wait=True)
        self.connection.close()
        logger.info("Consumer Closed.")

    def _handle_ack(self,
                    future: Future,
                    channel: Channel,
                    method_frame: pika.spec.Basic.Deliver) -> None:
        result = future.result()
        if not isinstance(result, CallbackResult):
            raise ValueError("Consumer's callback function must return a CallbackResult object.")
        if result.action == MQAction.ack:
            channel.basic_ack(delivery_tag=method_frame.delivery_tag)
            logger.debug(f"ACK: queue: {method_frame.routing_key}, "
                         f"delivery_tag: {method_frame.delivery_tag}")
        else:
            channel.basic_nack(delivery_tag=method_frame.delivery_tag, requeue=False)

            logger.debug(f"NACK:, queue: {method_frame.routing_key}, "
                         f"delivery_tag: {method_frame.delivery_tag}")

    def _handle_message(
        self,
        channel: Channel,
        method_frame: pika.spec.Basic.Deliver,
        header_frame: pika.spec.BasicProperties,
        message_body: bytes,
        handler_function: Callable
    ) -> None:
        future = self.thread_pool.submit(handler_function,
                                         method_frame=method_frame,
                                         header_frame=header_frame,
                                         message_body=message_body)

        # Important, add_callback_threadsafe will make sure ack event run on the same thread with the channel.
        handle_ack_callback = functools.partial(self._handle_ack,
                                                future=future,
                                                channel=channel,
                                                method_frame=method_frame)
        future.add_done_callback(lambda x: self.connection.add_callback_threadsafe(handle_ack_callback))


if __name__ == '__main__':
    consumer = MultiThreadConsumer(uri="")

    APP_QUEUE_NAME = "queue-a"
    consumer.setup_queue_consumer(queue_name=APP_QUEUE_NAME,
                                  exchange_name="exchange-a",
                                  handler_function=demo_callback)

    try:
        consumer.start_consuming()
    except KeyboardInterrupt:
        consumer.stop_consuming()

    consumer.close()
