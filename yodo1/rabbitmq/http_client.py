import json
import logging
from typing import Dict, Optional
from urllib.parse import quote_plus, urlparse

import elasticapm
import httpx
import pika
from tenacity import AsyncRetrying, Retrying, stop_after_attempt, wait_random

logger = logging.getLogger("yodo1.rabbitmq")


class MQSendFailedException(Exception):
    pass


class RabbitHttpSender:
    def __init__(
        self,
        uri: str,
        *,
        global_max_retry: int = 3,
        apm_client: elasticapm.Client = None,
        async_httpx_client: httpx.AsyncClient = httpx.AsyncClient(),
        sync_httpx_client: httpx.Client = httpx.Client(),
    ):
        """
        :param uri: rabbitmq uri
        :param global_max_retry: max retry count
        :param apm_client: elasticapm client
        :param async_httpx_client: async httpx client
        :param sync_httpx_client: sync httpx client
        """
        self.uri = uri

        uri_obj = urlparse(uri)
        self.host = uri_obj.hostname
        self.username = uri_obj.username
        self.password = uri_obj.password
        self.virtual_host = uri_obj.path[1:]
        self.global_max_retry = global_max_retry
        self.apm_client: elasticapm.Client = apm_client

        self.async_httpx_client = async_httpx_client
        self.sync_httpx_client = sync_httpx_client

        if self.apm_client:
            elasticapm.instrument()

    def declare_exchange(self, exchange_name: str) -> None:
        """
        Declare exchange on start up. We should declare exchange in the code.
        We use pika here for convinience,
        :param queue_name:
        :param exchange_name:
        :return:
        """
        uri = f"https://{self.username}:{self.password}@{self.host}/{self.virtual_host}"
        connect_params = pika.URLParameters(uri)
        connection = pika.BlockingConnection(connect_params)
        channel = connection.channel()

        channel.exchange_declare(
            exchange=exchange_name, exchange_type="fanout", durable=True
        )
        logger.info(f"Exchange {exchange_name} declared")
        channel.close()
        connection.close()

    def publish(
        self,
        *,
        exchange_name: str,
        message_body: Dict,
        event_name: str = None,
        properties: Dict = None,
        routing_key: str = "",
        max_retry: int = None,
        max_delay_on_retry: int = 30,
    ) -> None:
        """
        Publish message using sync http request
        :param event_name: key event name like `app-release, user-register`
        :param exchange_name: target exchange name
        :param message_body: message body, should be able to call json.dumps
        :param properties: message properties
        :param routing_key: routing key
        :param max_retry: max retry count, will use global_max_retry when it set as empty
        :param max_delay_on_retry: max delay when retrying to send message
        :return:
        """
        # setup trace context
        traceparent_string = self._start_trace(event_name=event_name)

        if max_retry is None:
            max_retry = self.global_max_retry

        # Prepare message and url
        message = self._build_message_json(
            message_body=message_body,
            properties=properties,
            routing_key=routing_key,
            traceparent_string=traceparent_string,
            event_name=event_name,
        )
        url = f"https://{self.host}/api/exchanges/{quote_plus(self.virtual_host)}/{exchange_name}/publish"

        try:
            # Retry for n times before give up.
            for attempt in Retrying(
                stop=stop_after_attempt(max_retry),
                reraise=True,
                wait=wait_random(min=1, max=max_delay_on_retry),
            ):
                with attempt:
                    self._sync_publish(
                        url=url,
                        message=message,
                    )

            trace_id = elasticapm.get_trace_id()
            logger.debug(
                f"Successfully send MQ message to exchange: {exchange_name} trace_id: {trace_id}"
            )
            if self.apm_client:
                self.apm_client.end_transaction(name=f"MQ PUBLISH {event_name}", result="success")
        except Exception as e:
            logger.warning(
                "Failed to send MQ message to exchange: {exchange_name} trace_id: {trace_id}"
            )
            self.apm_client.capture_exception()
            self.apm_client.end_transaction(name=f"MQ PUBLISH {event_name}", result="failure")
            raise e

    async def async_publish(
        self,
        *,
        exchange_name: str,
        message_body: Dict,
        event_name: str = None,
        properties: Optional[Dict] = None,
        routing_key: str = "",
        max_retry: int = None,
        max_delay_on_retry: int = 30,
    ) -> None:
        """
        Send mq message with async function
        :param exchange_name: target exchange name
        :param message_body: message body, should be able to call json.dumps
        :param properties: message properties
        :param routing_key: routing key
        :param max_retry: max retry count, will use global_max_retry when it set as empty
        :param max_delay_on_retry: max delay when retrying to send message
        :return:
        """
        # setup trace context
        traceparent_string = self._start_trace(event_name=event_name)

        if max_retry is None:
            max_retry = self.global_max_retry
        message = self._build_message_json(
            message_body=message_body,
            properties=properties,
            routing_key=routing_key,
            traceparent_string=traceparent_string,
            event_name=event_name,
        )
        url = f"https://{self.host}/api/exchanges/{quote_plus(self.virtual_host)}/{exchange_name}/publish"
        try:
            # Retry for n times before give up.
            for attempt in AsyncRetrying(
                stop=stop_after_attempt(max_retry),
                reraise=True,
                wait=wait_random(min=1, max=max_delay_on_retry),
            ):
                with attempt:
                    await self._async_publish(
                        url=url,
                        message=message,
                    )
            trace_id = elasticapm.get_trace_id()
            logger.debug(
                f"Successfully send MQ message to exchange: {exchange_name} trace_id: {trace_id}"
            )
            # If successly send message
            if self.apm_client:
                self.apm_client.end_transaction(name=event_name, result="success")
        except Exception as e:
            logger.warning(
                "Failed to send MQ message to exchange: {exchange_name} trace_id: {trace_id}"
            )
            self.apm_client.capture_exception()
            self.apm_client.end_transaction(name=event_name, result="failure")
            raise e

    async def close(self) -> None:
        self.sync_httpx_client.close()
        await self.async_httpx_client.aclose()

    @staticmethod
    def _build_message_json(
        *,
        message_body: Dict,
        properties: Optional[Dict] = None,
        routing_key: str = "",
        traceparent_string: str = None,
        event_name: str = None,
    ) -> Dict:
        if properties is None:
            properties = {}

        # Add traceparent_string to headers
        if traceparent_string is not None and event_name is not None:
            if "headers" in properties:
                properties["headers"]["traceparent"] = traceparent_string
                properties["headers"]["event_name"] = event_name
            else:
                properties["headers"] = {
                    "traceparent": traceparent_string,
                    "event_name": event_name,
                }

        message = {
            "properties": properties,
            "routing_key": routing_key,
            "payload_encoding": "string",
            "payload": json.dumps(message_body),
        }
        return message

    @staticmethod
    def _check_mq_response(response: httpx.Response) -> None:
        if response.status_code == 200:
            pass
        else:
            raise MQSendFailedException(response.text)

    def _sync_publish(self, *, url: str, message: Dict) -> None:
        """
        publish MQ using sync http request
        """
        try:
            r = self.sync_httpx_client.post(
                url,
                json=message,
                auth=httpx.BasicAuth(self.username, self.password),
            )
            self._check_mq_response(r)
        except MQSendFailedException as e:
            raise e
        except Exception as e:
            raise MQSendFailedException(str(e))

    async def _async_publish(self, *, url: str, message: Dict) -> None:
        """
        publish MQ using async http request
        """
        try:
            r = await self.async_httpx_client.post(
                url,
                json=message,
                auth=httpx.BasicAuth(self.username, self.password),
            )
            self._check_mq_response(r)
        except MQSendFailedException as e:
            raise e
        except Exception as e:
            raise MQSendFailedException(str(e))

    def _start_trace(self, event_name: str) -> Optional[str]:
        if self.apm_client:
            if event_name is None:
                raise ValueError("Must set event name when using with apm client")
            # Get trace parent from the context if exists
            # This will correlate this MQ with the trigger request
            traceparent_string = elasticapm.get_trace_parent_header()
            if traceparent_string:
                parent = elasticapm.trace_parent_from_string(traceparent_string)
            else:
                parent = None
            self.apm_client.begin_transaction(
                transaction_type="RabbitMQ", trace_parent=parent
            )
            traceparent_string = elasticapm.get_trace_parent_header()
        else:
            traceparent_string = None
        return traceparent_string
