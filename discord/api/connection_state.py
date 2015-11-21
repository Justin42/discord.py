import copy
from collections import deque

from ..event.listener import EventListener
from ..event.event_type import EventType
from ..event.events import Event
from .. import utils
from ..message import Message
from ..channel import Channel, PrivateChannel
from ..role import Role
from ..server import Server
from ..member import Member
from ..user import User


class ConnectionState(EventListener):
    def __init__(self, client, dispatcher, **kwargs):
        self.client = client
        self.dispatch = dispatcher
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

    def on_ready(self, event: Event):
        self.user = User(**event.user)
        guilds = event.guilds

        for guild in guilds:
            self._add_server(guild)

        for pm in event.private_channels:
            self.private_channels.append(PrivateChannel(id=pm['id'],
                                         user=User(**pm['recipient'])))

    def on_message_create(self, event: Event):
        channel = self.get_channel(event.channel_id)
        message = Message(channel=channel, **event.data)
        self.messages.append(message)

    def on_message_delete(self, event: Event):
        message_id = event.id
        found = self._get_message(message_id)
        if found is not None:
            event.channel = self.get_channel(event.channel_id)
            self.messages.remove(found)

    def on_message_update(self, event: Event):
        older_message = self._get_message(event.id)
        if older_message is not None:
            # create a copy of the new message
            message = copy.deepcopy(older_message)
            # update the new update
            for attr in event.data:
                if attr == 'channel_id' or attr == 'author':
                    continue
                value = event.data[attr]
                if 'time' in attr:
                    setattr(message, attr, utils.parse_time(value))
                else:
                    setattr(message, attr, value)
            event.old_message = older_message
            event.new_message = message
            self.dispatch(event)

    def on_presence_update(self, event: Event):
        server = self._get_server(event.guild_id)
        if server is not None:
            status = event.status
            user = event.user
            member_id = user['id']
            member = utils.find(lambda m: m.id == member_id, server.members)
            if member is not None:
                member.status = event.status
                member.game_id = event.game_id
                member.name = user.get('username', member.name)
                member.avatar = user.get('avatar', member.avatar)

                # call the event now
                event.member = member

    def on_user_update(self, event: Event):
        self.user = User(**event.data)

    def on_channel_delete(self, event: Event):
        server =  self._get_server(event.guild_id)
        if server is not None:
            channel_id = event.id
            channel = utils.find(lambda c: c.id == channel_id, server.channels)
            server.channels.remove(channel)
            event.channel = channel

    def on_channel_update(self, event: Event):
        server = self._get_server(event.guild_id)
        if server is not None:
            channel_id = event.id
            channel = utils.find(lambda c: c.id == channel_id, server.channels)
            channel.update(server=server, **event.data)
            event.channel = channel

    def on_channel_create(self, event: Event):
        is_private = getattr(event, 'is_private', False)
        channel = None
        if is_private:
            recipient = User(**event.recipient)
            pm_id = event.id
            channel = PrivateChannel(id=pm_id, user=recipient)
            self.private_channels.append(channel)
        else:
            server = self._get_server(event.guild_id)
            if server is not None:
                channel = Channel(server=server, **event.data)
                server.channels.append(channel)

    def on_guild_member_add(self, event: Event):
        server = self._get_server(event.guild_id)
        member = Member(server=server, deaf=False, mute=False, **event.data)
        server.members.append(member)
        event.member = member

    def on_guild_member_remove(self, event: Event):
        server = self._get_server(event.guild_id)
        if server is not None:
            user_id = event.user['id']
            member = utils.find(lambda m: m.id == user_id, server.members)
            server.members.remove(member)
            event.member = member

    def on_guild_member_update(self, event: Event):
        server = self._get_server(event.guild_id)
        user_id = event.user['id']
        member = utils.find(lambda m: m.id == user_id, server.members)
        if member is not None:
            user = event.user
            member.name = user['username']
            member.discriminator = user['discriminator']
            member.avatar = user['avatar']
            member.roles = []
            # update the roles
            for role in server.roles:
                if role.id in event.roles:
                    member.roles.append(role)
            event.member = member

    def on_guild_create(self, event: Event):
        self._add_server(event.data)
        event.server = self.servers[-1]

    def on_guild_delete(self, event: Event):
        server = self._get_server(event.id)
        self.servers.remove(server)
        event.server = server

    def on_guild_role_create(self, event: Event):
        server = self._get_server(event.guild_id)
        role_data = event.data.get('role', {})
        everyone = server.id == role_data.get('id')
        role = Role(everyone=everyone, **role_data)
        server.roles.append(role)
        event.server = server
        event.role = role

    def on_guild_role_delete(self, event: Event):
        server = self._get_server(event.guild_id)
        if server is not None:
            role_id = event.data.get('role_id')
            role = utils.find(lambda r: r.id == role_id, server.roles)
            server.roles.remove(role)
            event.server = server
            event.role = role

    def on_guild_role_update(self, event: Event):
        server = self._get_server(event.guild_id)
        if server is not None:
            role_id = event.role['id']
            role = utils.find(lambda r: r.id == role_id, server.roles)
            role.update(**event.role)
            event.role = role

    def on_voice_state_update(self, event: Event):
        server = self._get_server(event.guild_id)
        if server is not None:
            updated_member = self._update_voice_state(server, event.data)
            event.member = updated_member

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
