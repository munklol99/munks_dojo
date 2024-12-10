import time
from match import Match
import asyncio

import yaml

# Load the config file
with open('./config.yaml', 'r') as file:
    config = yaml.safe_load(file)

TEST_MODE = config['test_mode']

if TEST_MODE:
    in_queue_role_id = 1299617990513397771
else:
    in_queue_role_id = 1297971948302635088

class Queue:
    def __init__(self, store_match_callback=None):
        self.queue = []
        self.time_since_last_pop = 0.0
        self.last_time_someone_joined = None
        self.prequeue = []
        self.store_match_callback = store_match_callback
        self.match_size = 2 if TEST_MODE else 10
        self.bot = None
        self.disc_bot = None


    async def setup(self, channel, bot, leaderboard_channel):
        """Perform asynchronous setup tasks."""
        self.dequeuing_task = asyncio.create_task(self.monitor_queue())
        self.bot = channel
        self.disc_bot = bot
        self.leaderboard_channel = leaderboard_channel
        self.in_queue_role = self.bot.guild.get_role(in_queue_role_id)

    def __str__(self):
        string = '------ Current Queue ------ \n'
        string += f'Time since last queue pop: {round(self.time_since_last_pop)} seconds \n'
        for i, player in enumerate(self.queue):
            name = player['player_name']
            discord_name = player['discord_name']
            primary_role = player['primary_role']
            secondary_role = player['secondary_role']
            string += f'{i+1}. {name} | {discord_name} | {primary_role} | {secondary_role} \n'
        return string
    
    def __len__(self):
        return len(self.queue)
    
    def __iter__(self):
        return iter(self.queue)
    
    def user_exists(self, discord_name):
        return any(x['discord_name'] == discord_name for x in self.queue)

    async def enqueue(self, player, ctx=None):
        player_name = player['player_name']
        discord_name = player['discord_name']
        prim_role = player['primary_role'].lower()
        sec_role = player['secondary_role'].lower()
        elo = player['elo']
        discord_id = player['discord_id']
        if not self.queue:  # If queue was empty, start the timer
            self.last_time_someone_joined = time.time()
            self.time_since_last_pop = 0  # Reset time since last dequeue
        else:
            self.time_since_last_pop += time.time() - self.last_time_someone_joined
            self.last_time_someone_joined = time.time()
        
        if self.user_exists(discord_name):
            self.leave_queue(discord_name)
        self.queue.append({'player_name':player_name, 'discord_name':discord_name, 'primary_role':prim_role, 'secondary_role':sec_role, 'elo':elo, 'discord_id':discord_id, 'ready': False})
        print(self)

        return
    
    async def monitor_queue(self):
        while True:
            if len(self.queue) >= self.match_size:
                await self.dequeue()
            await asyncio.sleep(1)  # Check every second
    
    async def ready_up(self, discord_name, discord_user):
        for player in self.prequeue:
            if player['discord_name'] == discord_name:
                player['ready'] = True
                ready_count = sum(1 for p in self.prequeue if p.get('ready'))
                total_players = len(self.prequeue)
                await self.bot.send(f'<@{discord_user.id}> is ready! There are now {ready_count}/{total_players} players ready.')

                # Show only players not ready
                not_ready_players = [p for p in self.prequeue if not p.get('ready')]
                if not_ready_players:
                    prequeue_message = "**__Players needing to `!ready`:__**\n"
                    for p in not_ready_players:
                        prequeue_message += (
                            f"- **Player:** {p['discord_name']}\n"
                        )
                    await self.bot.send(prequeue_message)
                else:
                    await self.bot.send("All players are ready.")
                return
        await self.bot.send(f'<@{discord_user.id}> is not part of a `!ready` check.')

    async def dequeue(self, ctx=None):
        dequeued_items = self.queue[:self.match_size]
        self.queue = self.queue[self.match_size:]  # Remove dequeued items from queue
        names = [x['player_name'] for x in dequeued_items]
        discord_ids = [x['discord_id'] for x in dequeued_items]
        # Wait for players to all ready up before starting match
        prequeue = dequeued_items.copy()
        self.prequeue.extend(prequeue)
        # Wait for all players to be ready
        if self.bot:
            message = ''
            for d_id in discord_ids:
                member = self.disc_bot.get_user(d_id)
                message += f'<@{d_id}>, '
            await self.bot.send(f'{message}Match found, all players have 60-seconds to ready up with `!ready`.')
        try:
            print(f'Waiting for {len(prequeue)} players to be ready')
            wait_result = await asyncio.wait_for(self.wait_for_ready(prequeue), timeout=60)  # 60 seconds
            if wait_result:
                self.time_since_last_pop = 0  # Reset time since last dequeue
                print(f'Creating match with players: {names}')
                match = Match(dequeued_items, self.bot, self.disc_bot, self.leaderboard_channel)
                if self.store_match_callback:
                    await self.store_match_callback(match)
                await match.print_teams()
                await match.assign_roles()
                return 'Match created'
            else:
                await self.bot.send('Match was declined, continuing queue')
                return 'Match not created'
        except asyncio.TimeoutError:
            print("Matchmaking timed out. Returning players to queue")
            await self.bot.send('Matchmaking timed out. Returning players to queue')
            for player in prequeue:
                ready = False
                for p in self.prequeue:
                    if p['discord_id'] == player['discord_id']:
                        ready = p['ready']
                        break
                if ready:
                    print(f'Returning {player} to queue')
                    player['ready'] = False
                    self.queue.insert(0, player)
                else:
                    if 'discord_id' in player.keys():
                        user = self.bot.guild.get_member(player['discord_id'])
                        await user.remove_roles(self.in_queue_role)
            discord_ids = [x['discord_id'] for x in prequeue]
            self.prequeue = [x for x in self.prequeue if x['discord_id'] not in discord_ids]

        except Exception as e:
            print(e)
            

    async def wait_for_ready(self, prequeue):
        readied_players = []
        valid_names = [x['discord_name'] for x in prequeue]
        while len(readied_players) != len(prequeue):
            print(f'Readied up {len(readied_players)}/{len(prequeue)}')
            check_list = [x for x in self.prequeue if x['discord_name'] in valid_names]
            if len(check_list) != self.match_size:
                discord_ids = [x['discord_id'] for x in prequeue]
                for player in prequeue:
                    disc_ids = [x['discord_id'] for x in self.prequeue]
                    if player['discord_id'] in disc_ids:
                        # Add back to queue at front
                        self.queue.insert(0, player)
                        # Add queue role back
                        if 'discord_id' in player.keys():
                            user = self.bot.guild.get_member(player['discord_id'])
                            await user.add_roles(self.in_queue_role)
                self.prequeue = [x for x in self.prequeue if x['discord_id'] not in discord_ids]
                return False
            for player in check_list:
                if player['ready'] and player['discord_name'] not in readied_players:
                    readied_players.append(player['discord_name'])
            await asyncio.sleep(1)  # Check every second
        print(f'Readied up {len(readied_players)}/{len(prequeue)}')
        discord_ids = [x['discord_id'] for x in prequeue]
        self.prequeue = [x for x in self.prequeue if x['discord_id'] not in discord_ids]
        return True

    
    def start_match(self, players):
        player_list = []
        for player in players:
            p = {"name": player['player_name'], "primary_role": player['primary_role'], "secondary_role": player['secondary_role'], "elo": player['elo']}
            player_list.append(p)
        match = Match(player_list, self.bot, self.disc_bot)
        print(self)
        return match
        
    async def leave_queue(self, discord_name):
        self.queue = [x for x in self.queue if x['discord_name'] != discord_name]
        self.prequeue = [x for x in self.prequeue if x['discord_name'] != discord_name]
        print(self)
    
if __name__ == '__main__':
    async def main():
        queue = Queue()
        await queue.enqueue({
            'player_name': 'con.r',
            'discord_name': 'con.r',
            'primary_role': 'Jungle',
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 123456789
        })
        await asyncio.sleep(2)
        await queue.enqueue({
            'player_name': 'munk',
            'discord_name': 'munk', 
            'primary_role': 'Jungle',
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 234567890
        })
        await asyncio.sleep(2)
        await queue.enqueue({
            'player_name': 'munk1',
            'discord_name': 'munk1',
            'primary_role': 'Jungle', 
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 345678901
        })
        await asyncio.sleep(2)
        await queue.enqueue({
            'player_name': 'munk2',
            'discord_name': 'munk2',
            'primary_role': 'Jungle',
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 456789012
        })
        await asyncio.sleep(2)
        await queue.enqueue({
            'player_name': 'munk3',
            'discord_name': 'munk3',
            'primary_role': 'Jungle',
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 567890123
        })
        await queue.enqueue({
            'player_name': 'munk4',
            'discord_name': 'munk4',
            'primary_role': 'Jungle',
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 678901234
        })
        await queue.enqueue({
            'player_name': 'munk5',
            'discord_name': 'munk5',
            'primary_role': 'Jungle',
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 789012345
        })
        await asyncio.sleep(2)
        await queue.enqueue({
            'player_name': 'munk6',
            'discord_name': 'munk6',
            'primary_role': 'Jungle',
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 890123456
        })
        await queue.enqueue({
            'player_name': 'munk7',
            'discord_name': 'munk7',
            'primary_role': 'Jungle',
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 901234567
        })
        await queue.enqueue({
            'player_name': 'munk8',
            'discord_name': 'munk8',
            'primary_role': 'Jungle',
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 123456780
        })
        await queue.enqueue({
            'player_name': 'munk9',
            'discord_name': 'munk9',
            'primary_role': 'Jungle',
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 234567801
        })
        await queue.enqueue({
            'player_name': 'munk10',
            'discord_name': 'munk10',
            'primary_role': 'Jungle',
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 345678012
        })
        await asyncio.sleep(2)
        await queue.ready_up('con.r')
        await asyncio.sleep(2)
        await queue.ready_up('munk')
        await asyncio.sleep(2)
        await queue.ready_up('munk1')
        await asyncio.sleep(2)
        await queue.ready_up('munk2')
        await asyncio.sleep(2)
        await queue.ready_up('munk3')
        await asyncio.sleep(2)
        await queue.ready_up('munk4')
        await asyncio.sleep(2)
        await queue.ready_up('munk5')
        await asyncio.sleep(2)
        await queue.ready_up('munk6')
        await queue.ready_up('munk7')
        await queue.ready_up('munk8')
        await queue.ready_up('munk9')
        await queue.ready_up('munk10')
        await asyncio.sleep(10)

    asyncio.run(main())