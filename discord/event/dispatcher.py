import logging
import threading

from discord.event.event_type import EventType
from ..event.listener import EventListener
from .events import Event

log = logging.getLogger(__name__)


class EventDispatcher:
    def __init__(self):
        self.dispatch_lock = threading.RLock()
        self.listeners = []

    def dispatch(self, event: Event):
        with self.dispatch_lock:
            log.debug("Dispatching event {}".format(event.data))
            event_method = '_'.join(('on', event.type.name.lower()))
            # noinspection PyBroadException
            for listener in self.listeners:
                try:
                    getattr(listener, event_method, self.unhandled_event)(event)
                except Exception as e:
                    event = Event(EventType.ERROR, event.data, event.client)
                    self.dispatch(event)
        pass

    def add_listener(self, listener: EventListener):
        self.listeners.append(listener)

    def unhandled_event(self, event):
        pass
