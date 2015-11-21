from ..event.event_type import EventType
from .events import Event


class EventDispatcher:
    listeners = []

    def dispatch(self, event: Event):

        pass

    def handle_socket_opened(self):
        pass

    def handle_socket_closed(self):
        pass

    def handle_socket_raw_receive(self, raw):
        pass

    def handle_socket_response(self, response):
        pass

    def handle_socket_raw_send(self, payload, binary):
        pass

    def handle_socket_update(self, event_type: EventType, data: map):
        pass

    def handle_ready(self, data: map):
        pass

    def handle_message_create(self, data: map):
        pass

    def handle_message_delete(self, data: map):
        pass

    def handle_message_update(self, data: map):
        pass

    def handle_presence_update(self, data: map):
        pass

    def handle_user_update(self, data: map):
        pass

    def handle_channel_delete(self, data: map):
        pass

    def handle_channel_update(self, data: map):
        pass

    def handle_channel_create(self, data: map):
        pass

    def handle_guild_member_add(self, data: map):
        pass

    def handle_guild_member_remove(self, data: map):
        pass

    def handle_guild_member_update(self, data: map):
        pass

    def handle_guild_create(self, data: map):
        pass

    def handle_guild_delete(self, data: map):
        pass

    def handle_guild_role_create(self, data: map):
        pass

    def handle_guild_role_delete(self, data: map):
        pass

    def handle_guild_role_update(self, data: map):
        pass

    def handle_voice_state_update(self, data: map):
        pass
