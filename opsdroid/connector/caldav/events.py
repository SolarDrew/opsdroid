from opsdroid import events


class UpcomingEvent(events.Event):
    def __init__(self, name, start_time, end_time, *args, **kwargs):
        self.name = name
        self.start_time = start_time
        self.end_time = end_time


class CalDavEventCreator(events.EventCreator):
    """Create opsdroid events from caldav ones."""

    def __init__(self, connector, *args, **kwargs):
        """Initialise the event creator."""
        super().__init__(connector, *args, **kwargs)

        self.event_types["type-key-for-upcoming-events"] = self.create_upcoming_event

    async def create_upcoming_event(self, event, calendar):
        # extract name
        # extract start_time
        # extract end_time
        # return UpcomingEvent(name, start_time, end_time)
        print("Constructing UpcomingEvent")
