from .event_type import EventType


class Event:
    def __init__(self, event_type: EventType, data: dict, client):
        self.data = data
        self.client = client
        self.type = event_type

    def __getattr__(self, item):
        return self.data[item]
