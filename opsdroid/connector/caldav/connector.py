"""Connector for CalDav calendar format."""

import logging

from opsdroid.connector import Connector, register_event
from opsdroid import events
from . import events as cdevents

import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# requires pip-installable: google-api-python-client google-auth-httplib2 google-auth-oauthlib

_LOGGER = logging.getLogger(__name__)

__all__ = ["ConnectorCalDav"]


def _build_service():
    """pretty much mostly google example code

    needs a credentials.json in the same directory
    and at first launch it will make you launch a browser, then create
    the token.pickle file; I'm not
    yet sure how to dodge that problem
    """
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service


class ConnectorCalDav(Connector):
    """Connector for CalDav calendar format."""

    def __init__(self, config, opsdroid=None):  # noqa: D107
        """Init the config for the connector."""
        super().__init__(config, opsdroid=opsdroid)

        self.target_calendar_summary = 'PlasmaPy'    # TODO needs to be configurable`
        self.poll_delay = 900  # * u.s               # TODO needs to be configurable
        self.name = "caldav"  # The name of your connector
        self.default_target = "something"

        self._event_creator = cdevents.CalDavEventCreator(self)

    async def connect(self):
        """Create connection object with configured calendar provider."""
        self.service = _build_service()

        calendars = self.service.calendarList().list().execute()['items']
        filtered_calendars = [c for c in calendars if self.target_calendar_summary in c['summary']]
        if not filtered_calendars:
            raise RuntimeError(f"Could not find calendars with summary matching {EXPECTED_CALENDAR_SUMMARY}")
        self.calendar = filtered_calendars[0]

    async def disconnect(self):
        """Close the session."""

    @staticmethod
    def get_reminders(event, calendar):
        event_start_time = datetime.datetime.fromisoformat(event['start']['dateTime'])
        if event['reminders']['useDefault']:
            reminders = calendar['defaultReminders']
        else:
            reminders = event['reminders']['overrides']
        return [event_start_time - datetime.timedelta(minutes=r['minutes']) for r in reminders]

    async def listen(self):  # pragma: no cover
        """Poll for starting-soon events"""
        while True:  # pylint: disable=R1702
            try:
                # Poll the service for new events
                now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
                # Call the Calendar API and grab 10 events
                events_result = service.events().list(calendarId=calendar['id'], timeMin=now,
                                                      maxResults=10,  # could be adjusted to 1 to just get the next one;
                                                                      # would break with multiple events in quick succession
                                                                      # (mostly an edge case?)
                                                      singleEvents=True,
                                                      orderBy='startTime').execute()
                events = events_result.get('items', [])

                # an event is a dict with the following structure:
                # {'kind': 'calendar#event',
                #  'etag': '"3175282902571000"',
                #  'id': '3nll0h2iifp9s4i63iibirr4sp',
                #  'status': 'confirmed',
                #  'htmlLink': 'https://www.google.com/calendar/event?eid=M25sbDBoMmlpZnA5czRpNjNpaWJpcnI0c3AgN3RtMWhpcjBlbW5xZDliZDh2cTN2aXE1ZjhAZw',
                #  'created': '2020-04-23T11:28:23.000Z',
                #  'updated': '2020-04-23T11:28:23.910Z',
                #  'summary': 'Test event',
                #  'creator': {'email': 'stanczakdominik@gmail.com'},
                #  'organizer': {'email': '7tm1hir0emnqd9bd8vq3viq5f8@group.calendar.google.com',
                #   'displayName': 'FUW',
                #   'self': True},
                #  'start': {'dateTime': '2020-04-23T19:00:00+02:00'},
                #  'end': {'dateTime': '2020-04-23T19:30:00+02:00'},
                #  'iCalUID': '3nll0h2iifp9s4i63iibirr4sp@google.com',
                #  'sequence': 0,
                #  'reminders': {'useDefault': False,
                #   'overrides': [{'method': 'popup', 'minutes': 10},
                #    {'method': 'popup', 'minutes': 14400},
                #    {'method': 'popup', 'minutes': 60}]}}

                event_start_time = datetime.datetime.fromisoformat(event['start']['dateTime'])
                sample_message = f"Planned event: {event['summary']} happening at {event_start_time}"
                reminder_datetimes = [self.get_reminders(event, self.calendar) for event in events]

                # Parse those events through the event creator to convert it to an opsdroid event
                await self.opsdroid.parse(event)  # send the opsdroid event out to be handled by skills
                await asyncio.sleep(self.poll_delay)   # avoid flooding the network
            except:
                _LOGGER.exception(_("An error happened."))

    @register_event(events.Message)
    async def _send_message(self, message):
        """Do something when the connector gets a Message event from opsdroid."""
