"""Classes to describe different kinds of Slack specific event."""

import json
import logging
from collections import defaultdict

from opsdroid import events

_LOGGER = logging.getLogger(__name__)


class Blocks(events.Message):
    """A blocks object.

    Slack uses blocks to add advenced interactivity and formatting to messages.
    https://api.slack.com/messaging/interactivity
    Blocks are provided in JSON format to Slack which renders them.

    Args:
        blocks (string or dict): String or dict of json for blocks
        room (string, optional): String name of the room or chat channel in
                                 which message was sent
        connector (Connector, optional): Connector object used to interact with
                                         given chat service
        raw_event (dict, optional): Raw message as provided by chat service.
                                    None by default

    Attributes:
        created: Local date and time that message object was created
        user: String name of user sending message
        room: String name of the room or chat channel in which message was sent
        connector: Connector object used to interact with given chat service
        blocks: Blocks JSON as string
        raw_event: Raw message provided by chat service
        raw_match: A match object for a search against which the message was
            matched. E.g. a regular expression or natural language intent
        responded_to: Boolean initialized as False. True if event has been
            responded to

    """

    def __init__(self, blocks, *args, **kwargs):
        """Create object with minimum properties."""
        super().__init__("", *args, **kwargs)

        self.blocks = blocks
        if isinstance(self.blocks, list):
            self.blocks = json.dumps(self.blocks)


class SlackEventCreator(events.EventCreator):
    """Create opsdroid events from Slack ones."""

    def __init__(self, connector, *args, **kwargs):
        """Initialise the event creator"""
        super().__init__(connector, *args, **kwargs)
        self.connector = connector

        # Things for managing various types of message
        self.event_types['message'] = self.create_room_message
        self.event_types['channel_created'] = self.create_newroom

        self.message_events = defaultdict(lambda: self.skip)
        self.message_events.update(
            {
                "message": self.create_message,
                "channel_topic": self.topic_changed
            }
        )

        # Things for managing room-level events
        self.event_types['channel_created'] = self.create_newroom

    async def create_room_message(self, event, channel):
        """Dispatch a message event of arbitrary subtype."""
        msgtype = event['subtype'] if 'subtype' in event.keys() else 'message'
        return await self.message_events[msgtype](event, channel)

    async def create_message(self, event, channel):
        """Send a Message event."""

        # Lookup username
        _LOGGER.debug("Looking up sender username")
        user_name = event["user"]
        try:
            user_info = await self.connector.lookup_username(user_name)
            user_name = user_info["name"]
        except ValueError:
            pass

        _LOGGER.debug("Replacing userids in message with usernames")
        text = await self.connector.replace_usernames(event["text"])

        return events.Message(
            text,
            user_info["name"],
            channel,
            self.connector,
            event_id=event["ts"],
            raw_event=event
        )

    async def create_newroom(self, event, channel):
        """Send a NewRoom event"""
        return events.NewRoom(name=event['channel'].pop('name'),
                              params=None,
                              target=channel['id'],
                              connector=self.connector,
                              event_id=event['event_ts'],
                              raw_event=event)

    async def topic_changed(self, event, channel):
        """Send a RoomDescription event"""
        return events.RoomDescription(description=event['topic'],
                                      target=channel,
                                      connector=self.connector,
                                      event_id=event['ts'],
                                      raw_event=event)
