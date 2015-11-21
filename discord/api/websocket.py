import json
import logging
import threading

import time
from ws4py.client import WebSocketBaseClient

from discord.event.dispatcher import EventDispatcher
from discord.event.event_type import EventType

log = logging.getLogger(__name__)


class WebSocket(WebSocketBaseClient):
    def __init__(self, dispatch: EventDispatcher, url):
        WebSocketBaseClient.__init__(self, url,
                                     protocols=['http-only', 'chat'])
        self.dispatch = dispatch
        self.keep_alive = None

    def opened(self):
        log.info('Opened at {}'.format(int(time.time())))
        self.dispatch.handle_socket_opened()

    def closed(self, code, reason=None):
        if self.keep_alive is not None:
            self.keep_alive.stop.set()
        log.info('Closed with {} ("{}") at {}'.format(code, reason,
                                                      int(time.time())))
        self.dispatch.handle_socket_closed()

    def handshake_ok(self):
        pass

    def send(self, payload, binary=False):
        self.dispatch.handle_socket_raw_send(payload, binary)
        WebSocketBaseClient.send(self, payload, binary)

    def received_message(self, msg):
        self.dispatch.handle_socket_raw_receive(msg)
        response = json.loads(str(msg))
        log.debug('WebSocket Event: {}'.format(response))
        self.dispatch.handle_socket_response(response)

        op = response.get('op')
        data = response.get('d')

        if op != 0:
            log.info("Unhandled op {}".format(op))
            return # What about op 7?

        event = response.get('t')

        if event == 'READY':
            interval = data['heartbeat_interval'] / 1000.0
            self.keep_alive = KeepAliveHandler(interval, self)
            self.keep_alive.start()

        if event in ('READY', 'MESSAGE_CREATE', 'MESSAGE_DELETE',
                     'MESSAGE_UPDATE', 'PRESENCE_UPDATE', 'USER_UPDATE',
                     'CHANNEL_DELETE', 'CHANNEL_UPDATE', 'CHANNEL_CREATE',
                     'GUILD_MEMBER_ADD', 'GUILD_MEMBER_REMOVE',
                     'GUILD_MEMBER_UPDATE', 'GUILD_CREATE', 'GUILD_DELETE',
                     'GUILD_ROLE_CREATE', 'GUILD_ROLE_DELETE',
                     'GUILD_ROLE_UPDATE', 'VOICE_STATE_UPDATE'):
            self.dispatch.handle_socket_update(getattr(EventType, event, EventType.UNKNOWN), data)
            print(event, data)

        else:
            log.info("Unhandled event {}".format(event))


class KeepAliveHandler(threading.Thread):
    def __init__(self, seconds, socket, **kwargs):
        threading.Thread.__init__(self, **kwargs)
        self.seconds = seconds
        self.socket = socket
        self.stop = threading.Event()

    def run(self):
        while not self.stop.wait(self.seconds):
            payload = {
                'op': 1,
                'd': int(time.time())
            }

            msg = 'Keeping websocket alive with timestamp {0}'
            log.debug(msg.format(payload['d']))
            self.socket.send(json.dumps(payload, separators=(',', ':')))