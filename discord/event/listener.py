from ..event.event_type import EventType
from ..event.events import Event


class EventListener:
    def on_error(self, event: Event):
        pass

    def on_socket_opened(self):
        pass

    def on_socket_closed(self):
        pass

    def on_socket_raw_receive(self, raw):
        pass

    def on_socket_response(self, response):
        pass

    def on_socket_raw_send(self, payload, binary):
        pass

    def on_socket_update(self, event_type: EventType, data: map):
        pass

    def on_ready(self, event: Event):
        pass

    def on_message_create(self, event: Event):
        pass

    def on_message_delete(self, event: Event):
        pass

    def on_message_update(self, event: Event):
        pass

    def on_presence_update(self, event: Event):
        pass

    def on_user_update(self, event: Event):
        pass

    def on_channel_delete(self, event: Event):
        pass

    def on_channel_update(self, event: Event):
        pass

    def on_channel_create(self, event: Event):
        pass

    def on_guild_member_add(self, event: Event):
        pass

    def on_guild_member_remove(self, event: Event):
        pass

    def on_guild_member_update(self, event: Event):
        pass

    def on_guild_create(self, event: Event):
        pass

    def on_guild_delete(self, event: Event):
        pass

    def on_guild_role_create(self, event: Event):
        pass

    def on_guild_role_delete(self, event: Event):
        pass

    def on_guild_role_update(self, event: Event):
        pass

    def on_voice_state_update(self, event: Event):
        pass
