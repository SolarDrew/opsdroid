"""Connector for CalDav calendar format."""

import logging

from opsdroid.connector import Connector, register_event
from opsdroid import events
from . import events as cdevents


_LOGGER = logging.getLogger(__name__)

__all__ = ["ConnectorCalDav"]


class ConnectorCalDav(Connector):
    """Connector for CalDav calendar format."""

    def __init__(self, config, opsdroid=None):  # noqa: D107
        """Init the config for the connector."""
        super().__init__(config, opsdroid=opsdroid)

        self.name = "caldav"  # The name of your connector
        self.default_target = "something"

        self._event_creator = cdevents.CalDavEventCreator(self)

    async def connect(self):
        """Create connection object with configured calendar provider."""

    async def disconnect(self):
        """Close the session."""

    async def listen(self):  # pragma: no cover
        """Listen for new messages from the chat service."""
        while True:  # pylint: disable=R1702
            try:
                response = "some way of getting a reponse"
            except:
                _LOGGER.exception(_("An error happened."))

    @register_event(events.Message)
    async def _send_message(self, message):
        """Do something when the connector gets a Message event from opsdroid."""

