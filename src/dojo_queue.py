import time
from match import Match
import asyncio

class Queue:
    def __init__(self):
        self.queue = []
        self.time_since_last_pop = 0.0
        self.last_time_someone_joined = None
        self.prequeue = []

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
        if len(self.queue) >= 10:
            self.dequeue()

        return
    
    async def ready_up(self, discord_name):
        for prequeue in self.prequeue:
            for player in prequeue:
                if player['discord_name'] == discord_name:
                    player['ready'] = True
                    print(f'{discord_name} is ready')
                    return
        print(f'{discord_name} is not in the queue')

    async def dequeue(self, ctx=None):
        dequeued_items = self.queue[:10]
        self.queue = self.queue[10:]  # Remove dequeued items from queue
        names = [x['player_name'] for x in dequeued_items]
        # Wait for players to all ready up before starting match

        readied_players = []

        idx = len(self.prequeue)
        self.prequeue.append(dequeued_items)
        # Wait for all players to be ready
        while len(readied_players) != len(dequeued_items):
            for player in self.prequeue[idx]:
                if player['ready']:
                    readied_players.append(player['discord_name'])
            await asyncio.sleep(1)

        print(f'Creating match with players: {names}')

        self.time_since_last_pop = 0  # Reset time since last dequeue
        match = Match(dequeued_items)
        return match
    
    def start_match(self, players):
        player_list = []
        for player in players:
            p = {"name": player['player_name'], "primary_role": player['primary_role'], "secondary_role": player['secondary_role'], "elo": player['elo']}
            player_list.append(p)
        match = Match(player_list)
        print(self)
        return match
        
    def leave_queue(self, discord_name):
        self.queue = [x for x in self.queue if x['discord_name'] != discord_name]
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
        time.sleep(2)
        await queue.enqueue({
            'player_name': 'munk',
            'discord_name': 'munk', 
            'primary_role': 'Jungle',
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 234567890
        })
        time.sleep(2)
        await queue.enqueue({
            'player_name': 'munk1',
            'discord_name': 'munk1',
            'primary_role': 'Jungle', 
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 345678901
        })
        time.sleep(2)
        await queue.enqueue({
            'player_name': 'munk2',
            'discord_name': 'munk2',
            'primary_role': 'Jungle',
            'secondary_role': 'Mid',
            'elo': 800,
            'discord_id': 456789012
        })
        time.sleep(2)
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
        time.sleep(2)
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
        await queue.ready_up('con.r')
        time.sleep(2)
        await queue.ready_up('munk')
        time.sleep(2)
        await queue.ready_up('munk1')
        time.sleep(2)
        await queue.ready_up('munk2')
        time.sleep(2)
        await queue.ready_up('munk3')
        time.sleep(2)
        await queue.ready_up('munk4')
        time.sleep(2)
        await queue.ready_up('munk5')
        time.sleep(2)
        await queue.ready_up('munk6')
        await queue.ready_up('munk7')
        await queue.ready_up('munk8')
        await queue.ready_up('munk9')
        await queue.ready_up('munk10')

    asyncio.run(main())