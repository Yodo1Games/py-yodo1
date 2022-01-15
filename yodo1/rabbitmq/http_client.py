import json
import logging

import httpx
from typing import Dict
from urllib.parse import quote_plus, urlparse
from tenacity import (
    AsyncRetrying,
    Retrying,
    stop_after_attempt,
    wait_random,
)

logger = logging.getLogger("yodo1.rabbitmq")


class MQSendFailedException(Exception):
    pass


class RabbitHttpSender:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        virtual_host: str,
        global_max_retry: int = 3,
    ):
        self.host = host
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        self.global_max_retry = global_max_retry

    @classmethod
    def server_param_from_uri(cls, uri: str) -> Dict:
        """
        Parse uri info server param, used to simplified env variables in the container.
        Example:

        >>> server_params = RabbitHttpSender.server_param_from_uri(demo_uri)
        >>> s = RabbitHttpSender(**server_params)
        """
        obj = urlparse(uri)
        return {
            "host": obj.hostname,
            "username": obj.username,
            "password": obj.password,
            "virtual_host": obj.path[1:],
        }

    def check_queue(self, queue_name: str, exchange_name: str = None):
        """
        Check queue and exchange on start up
        :param queue_name:
        :param exchange_name:
        :return:
        """
        # TODO: implement cheking and init function
        pass

    def publish(
        self,
        *,
        exchange_name: str,
        message_body: Dict,
        properties: Dict = None,
        routing_key: str = "",
        max_retry: int = None,
        max_delay_on_retry: int = 30,
    ) -> None:
        """
        Publish message using sync http request
        :param exchange_name: target exchange name
        :param message_body: message body, should be able to call json.dumps
        :param properties: message properties
        :param routing_key: routing key
        :param max_retry: max retry count, will use global_max_retry when it set as empty
        :param max_delay_on_retry: max delay when retrying to send message
        :return:
        """
        if max_retry is None:
            max_retry = self.global_max_retry

        # Prepare message and url
        message = self._build_message_json(
            message_body=message_body, properties=properties, routing_key=routing_key
        )
        url = f"https://{self.host}/api/exchanges/{quote_plus(self.virtual_host)}/{exchange_name}/publish"

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
                logger.debug(
                    f"Successfully send MQ message to exchange: {exchange_name}"
                )

    async def async_publish(
        self,
        *,
        exchange_name: str,
        message_body: Dict,
        properties: Dict = None,
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
        if max_retry is None:
            max_retry = self.global_max_retry
        message = self._build_message_json(
            message_body=message_body, properties=properties, routing_key=routing_key
        )
        url = f"https://{self.host}/api/exchanges/{quote_plus(self.virtual_host)}/{exchange_name}/publish"
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
                logger.debug(
                    f"Successfully send MQ message to exchange: {exchange_name}"
                )

    @staticmethod
    def _build_message_json(
        *, message_body: Dict, properties: Dict = None, routing_key: str = ""
    ) -> Dict:
        if properties is None:
            properties = {}
        message = {
            "properties": properties,
            "routing_key": routing_key,
            "payload_encoding": "string",
            "payload": json.dumps(message_body),
        }
        return message

    def _sync_publish(self, *, url: str, message: Dict):
        """
        publish MQ using sync http request
        """
        try:
            r = httpx.post(
                url, json=message, auth=httpx.BasicAuth(self.username, self.password)
            )
            if r.status_code == 200:
                pass
            else:
                logger.warning(f"Failed to send MQ message, server response: {r.text}")
                raise MQSendFailedException
        except MQSendFailedException as e:
            raise e
        except Exception as e:
            logger.warning(f"Message send failed, error: {e}")
            raise MQSendFailedException

    async def _async_publish(self, *, url: str, message: Dict) -> None:
        """
        publish MQ using async http request
        """
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(
                    url,
                    json=message,
                    auth=httpx.BasicAuth(self.username, self.password),
                )
                if r.status_code == 200:
                    pass
                else:
                    logger.warning(
                        f"Failed to send MQ message, server response: {r.text}"
                    )
                    raise MQSendFailedException
            except MQSendFailedException as e:
                raise e
            except Exception as e:
                logger.warning(f"Message send failed, error: {e}")
                raise MQSendFailedException
