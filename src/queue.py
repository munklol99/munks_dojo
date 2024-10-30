import time
from .match import Match

class Queue:
    def __init__(self):
        self.queue = []
        self.time_since_last_pop = 0.0
        self.last_time_someone_joined = None

    def __str__(self):
        string = '------ Current Queue ------ \n'
        string += f'Time since last queue pop: {self.time_since_last_pop:2f} \n'
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

    def enqueue(self, player):
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
        self.queue.append({'player_name':player_name, 'discord_name':discord_name, 'primary_role':prim_role, 'secondary_role':sec_role, 'elo':elo, 'discord_id':discord_id})
        print(self)

    def dequeue(self):
        dequeued_items = self.queue[:10]
        self.items = self.queue[10:]  # Remove dequeued items from queue
        names = [x['player'] for x in dequeued_items]
        print(f'Creating match with players: {names}')

        self.time_since_last_pop = 0  # Reset time since last dequeue
        
        return dequeued_items
    
    def start_match(self, players):
        player_list = []
        for player in players:
            p = {"name": player['player'], "primary_role": player['primary_role'], "secondary_role": player['secondary_role'], "elo": player['elo']}
            player_list.append(p)
        match = Match(player_list)
        return match
        
    def leave_queue(self, discord_name):
        self.queue = [x for x in self.queue if x['discord_name'] != discord_name]
        print(self)
    
if __name__ == '__main__':
    queue = Queue()
    queue.enqueue({
        'player_name': 'con.r',
        'discord_name': 'con.r',
        'primary_role': 'Jungle',
        'secondary_role': 'Mid',
        'elo': 800
    })
    time.sleep(2)
    queue.enqueue({
        'player_name': 'munk',
        'discord_name': 'munk', 
        'primary_role': 'Jungle',
        'secondary_role': 'Mid',
        'elo': 800
    })
    time.sleep(2)
    queue.enqueue({
        'player_name': 'munk1',
        'discord_name': 'munk1',
        'primary_role': 'Jungle', 
        'secondary_role': 'Mid',
        'elo': 800
    })
    time.sleep(2)
    queue.enqueue({
        'player_name': 'munk2',
        'discord_name': 'munk2',
        'primary_role': 'Jungle',
        'secondary_role': 'Mid',
        'elo': 800
    })
    time.sleep(2)
    queue.enqueue({
        'player_name': 'munk3',
        'discord_name': 'munk3',
        'primary_role': 'Jungle',
        'secondary_role': 'Mid',
        'elo': 800
    })
    queue.enqueue({
        'player_name': 'munk4',
        'discord_name': 'munk4',
        'primary_role': 'Jungle',
        'secondary_role': 'Mid',
        'elo': 800
    })
    queue.enqueue({
        'player_name': 'munk5',
        'discord_name': 'munk5',
        'primary_role': 'Jungle',
        'secondary_role': 'Mid',
        'elo': 800
    })
    time.sleep(2)
    queue.enqueue({
        'player_name': 'munk6',
        'discord_name': 'munk6',
        'primary_role': 'Jungle',
        'secondary_role': 'Mid',
        'elo': 800
    })
    queue.enqueue({
        'player_name': 'munk7',
        'discord_name': 'munk7',
        'primary_role': 'Jungle',
        'secondary_role': 'Mid',
        'elo': 800
    })
    queue.enqueue({
        'player_name': 'munk8',
        'discord_name': 'munk8',
        'primary_role': 'Jungle',
        'secondary_role': 'Mid',
        'elo': 800
    })
    queue.enqueue({
        'player_name': 'munk9',
        'discord_name': 'munk9',
        'primary_role': 'Jungle',
        'secondary_role': 'Mid',
        'elo': 800
    })
    queue.enqueue({
        'player_name': 'munk10',
        'discord_name': 'munk10',
        'primary_role': 'Jungle',
        'secondary_role': 'Mid',
        'elo': 800
    })
    queue.dequeue()