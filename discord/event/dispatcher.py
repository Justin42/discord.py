import logging
import threading

from ..event.listener import EventListener
from .events import Event

log = logging.getLogger(__name__)


class EventDispatcher:
    def __init__(self):
        self.dispatch_lock = threading.RLock()
        self.listeners = []

    def dispatch(self, event: Event): # TODO Call on_event to add client attribute
        with self.dispatch_lock:
            log.debug("Dispatching event {}".format(event.data))
            event_method = '_'.join(('on', event.type.name.lower()))
            # noinspection PyBroadException
            try:
                getattr(self, event_method, self.unhandled_event)(event)
            except Exception as e:
                getattr(self, 'on_error')(event)
        pass

    def add_listener(self, listener: EventListener):
        self.listeners.append(listener)

    def unhandled_event(self, event):
        pass
