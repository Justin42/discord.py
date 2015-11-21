import copy
from collections import deque

from ..event.event_type import EventType
from ..event.events import Event
from ..event.dispatcher import EventDispatcher
from .. import utils
from ..message import Message
from ..channel import Channel, PrivateChannel
from ..role import Role
from ..server import Server
from ..member import Member
from ..user import User


class ConnectionState(EventDispatcher):
    def __init__(self, client, **kwargs):
        self.client = client
        self.dispatch = client.dispatch
        self.user = None
        self.email = None
        self.servers = []
        self.private_channels = []
        self.messages = deque([], maxlen=kwargs.get('max_length', 5000))

    def _get_message(self, msg_id):
        return utils.find(lambda m: m.id == msg_id, self.messages)

    def _get_server(self, guild_id):
        return utils.find(lambda g: g.id == guild_id, self.servers)

    def _update_voice_state(self, server, data):
        user_id = data.get('user_id')
        member = utils.find(lambda m: m.id == user_id, server.members)
        if member is not None:
            ch_id = data.get('channel_id')
            channel = utils.find(lambda c: c.id == ch_id, server.channels)
            member.update_voice_state(voice_channel=channel, **data)
        return member

    def _add_server(self, guild):
        guild['roles'] = [Role(everyone=(guild['id'] == role['id']), **role) for role in guild['roles']]
        members = guild['members']
        owner = guild['owner_id']
        for i, member in enumerate(members):
            roles = member['roles']
            for j, roleid in enumerate(roles):
                role = utils.find(lambda r: r.id == roleid, guild['roles'])
                if role is not None:
                    roles[j] = role
            members[i] = Member(**member)

            # found the member that owns the server
            if members[i].id == owner:
                owner = members[i]

        for presence in guild['presences']:
            user_id = presence['user']['id']
            member = utils.find(lambda m: m.id == user_id, members)
            if member is not None:
                member.status = presence['status']
                member.game_id = presence['game_id']

        server = Server(owner=owner, **guild)

        # give all the members their proper server
        for member in server.members:
            member.server = server

        channels = [Channel(server=server, **channel)
                    for channel in guild['channels']]
        server.channels = channels
        for obj in guild.get('voice_states', []):
            self._update_voice_state(server, obj)
        self.servers.append(server)

    def handle_ready(self, data):
        self.user = User(**data['user'])
        guilds = data.get('guilds')

        for guild in guilds:
            self._add_server(guild)

        for pm in data.get('private_channels'):
            self.private_channels.append(PrivateChannel(id=pm['id'],
                                         user=User(**pm['recipient'])))

        # we're all ready
        self.dispatch(Event(EventType.READY, data, self.client))

    def handle_message_create(self, data):
        channel = self.get_channel(data.get('channel_id'))
        message = Message(channel=channel, **data)
        self.dispatch(Event(EventType.MESSAGE_CREATE, data, self.client))
        self.messages.append(message)

    def handle_message_delete(self, data):
        message_id = data.get('id')
        found = self._get_message(message_id)
        if found is not None:
            event = Event(EventType.MESSAGE_DELETE, data, self.client)
            event.channel = self.get_channel(data.get('channel_id'))
            self.dispatch(event)
            self.messages.remove(found)

    def handle_message_update(self, data):
        older_message = self._get_message(data.get('id'))
        if older_message is not None:
            # create a copy of the new message
            message = copy.deepcopy(older_message)
            # update the new update
            for attr in data:
                if attr == 'channel_id' or attr == 'author':
                    continue
                value = data[attr]
                if 'time' in attr:
                    setattr(message, attr, utils.parse_time(value))
                else:
                    setattr(message, attr, value)
            event = Event(EventType.MESSAGE_UPDATE, data, self.client)
            event.old_message = older_message
            event.new_message = message
            self.dispatch(event)

    def handle_presence_update(self, data):
        server = self._get_server(data.get('guild_id'))
        if server is not None:
            status = data.get('status')
            user = data['user']
            member_id = user['id']
            member = utils.find(lambda m: m.id == member_id, server.members)
            if member is not None:
                member.status = data.get('status')
                member.game_id = data.get('game_id')
                member.name = user.get('username', member.name)
                member.avatar = user.get('avatar', member.avatar)

                # call the event now
                event = Event(EventType.PRESENCE_UPDATE, data, self.client)
                event.member = member
                self.dispatch(event)

    def handle_user_update(self, data):
        self.user = User(**data)

    def handle_channel_delete(self, data):
        server =  self._get_server(data.get('guild_id'))
        if server is not None:
            channel_id = data.get('id')
            channel = utils.find(lambda c: c.id == channel_id, server.channels)
            server.channels.remove(channel)
            event = Event(EventType.CHANNEL_DELETE, data, self.client)
            event.channel = channel

    def handle_channel_update(self, data):
        server = self._get_server(data.get('guild_id'))
        if server is not None:
            channel_id = data.get('id')
            channel = utils.find(lambda c: c.id == channel_id, server.channels)
            channel.update(server=server, **data)
            event = Event(EventType.CHANNEL_UPDATE, data, self.client)
            event.channel = channel
            self.dispatch(event)

    def handle_channel_create(self, data):
        is_private = data.get('is_private', False)
        channel = None
        if is_private:
            recipient = User(**data.get('recipient'))
            pm_id = data.get('id')
            channel = PrivateChannel(id=pm_id, user=recipient)
            self.private_channels.append(channel)
        else:
            server = self._get_server(data.get('guild_id'))
            if server is not None:
                channel = Channel(server=server, **data)
                server.channels.append(channel)

        self.dispatch(Event(EventType.CHANNEL_CREATE, data, self.client))

    def handle_guild_member_add(self, data):
        server = self._get_server(data.get('guild_id'))
        member = Member(server=server, deaf=False, mute=False, **data)
        server.members.append(member)
        event = Event(EventType.GUILD_MEMBER_ADD, data, self.client)
        event.member = member
        self.dispatch(event)

    def handle_guild_member_remove(self, data):
        server = self._get_server(data.get('guild_id'))
        if server is not None:
            user_id = data['user']['id']
            member = utils.find(lambda m: m.id == user_id, server.members)
            server.members.remove(member)
            event = Event(EventType.GUILD_MEMBER_REMOVE, data, self.client)
            event.member = member
            self.dispatch(event)

    def handle_guild_member_update(self, data):
        server = self._get_server(data.get('guild_id'))
        user_id = data['user']['id']
        member = utils.find(lambda m: m.id == user_id, server.members)
        if member is not None:
            user = data['user']
            member.name = user['username']
            member.discriminator = user['discriminator']
            member.avatar = user['avatar']
            member.roles = []
            # update the roles
            for role in server.roles:
                if role.id in data['roles']:
                    member.roles.append(role)
            event = Event(EventType.GUILD_MEMBER_UPDATE, data, self.client)
            event.member = member
            self.dispatch(event)

    def handle_guild_create(self, data):
        self._add_server(data)
        event = Event(EventType.GUILD_CREATE, data, self.client)
        event.server = self.servers[-1]
        self.dispatch(event)

    def handle_guild_delete(self, data):
        server = self._get_server(data.get('id'))
        self.servers.remove(server)
        event = Event(EventType.GUILD_DELETE, data, self.client)
        event.server = server
        self.dispatch(event)

    def handle_guild_role_create(self, data):
        server = self._get_server(data.get('guild_id'))
        role_data = data.get('role', {})
        everyone = server.id == role_data.get('id')
        role = Role(everyone=everyone, **role_data)
        server.roles.append(role)
        event = Event(EventType.GUILD_ROLE_CREATE, data, self.client)
        event.server = server
        event.role = role
        self.dispatch(event)

    def handle_guild_role_delete(self, data):
        server = self._get_server(data.get('guild_id'))
        if server is not None:
            role_id = data.get('role_id')
            role = utils.find(lambda r: r.id == role_id, server.roles)
            server.roles.remove(role)
            event = Event(EventType.GUILD_ROLE_DELETE, data, self.client)
            event.server = server
            event.role = role
            self.dispatch(event)

    def handle_guild_role_update(self, data):
        server = self._get_server(data.get('guild_id'))
        if server is not None:
            role_id = data['role']['id']
            role = utils.find(lambda r: r.id == role_id, server.roles)
            role.update(**data['role'])
            event = Event(EventType.GUILD_ROLE_UPDATE, data, self.client)
            event.role = role
            self.dispatch(event)

    def handle_voice_state_update(self, data):
        server = self._get_server(data.get('guild_id'))
        if server is not None:
            updated_member = self._update_voice_state(server, data)
            event = Event(EventType.VOICE_STATE_UPDATE, data, self.client)
            event.member = updated_member
            self.dispatch(event)

    def get_channel(self, id):
        if id is None:
            return None

        for server in self.servers:
            for channel in server.channels:
                if channel.id == id:
                    return channel

        for pm in self.private_channels:
            if pm.id == id:
                return pm
