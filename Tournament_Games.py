import random

class GameLobby:
    def __init__(self, max_players=10):
        self.max_players = max_players
        self.players = []
        self.team_a = []
        self.team_b = []

    def add_player(self, player_name):
        if len(self.players) < self.max_players:
            self.players.append(player_name)
            print(f"{player_name} has joined the lobby.")
        else:
            print(f"Lobby is full. {player_name} could not join.")

    def balance_teams(self):
        # Shuffle players to ensure random distribution
        random.shuffle(self.players)
        mid = len(self.players) // 2
        self.team_a = self.players[:mid]
        self.team_b = self.players[mid:]

    def start_match(self):
        if len(self.players) < self.max_players:
            print("Not enough players to start the match.")
            return

        self.balance_teams()

        print("\nMatch Starting!")
        print(f"Team A: {', '.join(self.team_a)}")
        print(f"Team B: {', '.join(self.team_b)}")

        # Simulate match completion
        self.end_match()

    def end_match(self):
        print("\nMatch ended. Congratulations!")

# Example usage
lobby = GameLobby(max_players=10)

# Adding players to the lobby
players = ['Player1', 'Player2', 'Player3', 'Player4', 'Player5',
           'Player6', 'Player7', 'Player8', 'Player9', 'Player10']

for player in players:
    lobby.add_player(player)

# Start the match
lobby.start_match()
