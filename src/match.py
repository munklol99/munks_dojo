from mongo_helpers import get_user_data, get_database, update_users_elo, get_leaderboard
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpInteger, value, PULP_CBC_CMD
import asyncio

TEST_MODE = True

in_game_role_id = 1299620439357788224
registered_role_id = 1299615071131140116
in_queue_role_id = 1299617990513397771

test_users = [
    {"player_name": "Luna", "primary_role": "jungle", "secondary_role": "top", "elo": 823},
    {"player_name": "Ezra", "primary_role": "adc", "secondary_role": "support", "elo": 795},
    {"player_name": "Kai", "primary_role": "mid", "secondary_role": "jungle", "elo": 841},
    {"player_name": "Sage", "primary_role": "top", "secondary_role": "mid", "elo": 767},
    {"player_name": "Finn", "primary_role": "support", "secondary_role": "adc", "elo": 756},
    {"player_name": "Arya", "primary_role": "mid", "secondary_role": "support", "elo": 810},
    {"player_name": "Jace", "primary_role": "support", "secondary_role": "jungle", "elo": 779},
    {"player_name": "Nova", "primary_role": "jungle", "secondary_role": "adc", "elo": 835},
    {"player_name": "Rey", "primary_role": "top", "secondary_role": "mid", "elo": 752},
    {"player_name": "Zara", "primary_role": "adc", "secondary_role": "top", "elo": 847},
]

class Match():
    def __init__(self, discord_users: list, bot=None, disc_bot=None, leaderboard_channel=None):
        if len(discord_users) < 10:
            print(f"Not enough users to start a match {len(discord_users)} / 10")
        elif len(discord_users) > 10:
            print(f"Too many users to start a match {len(discord_users)} / 10")
        
        # users = get_user_data(discord_users)
        print(discord_users)
        users = discord_users
        if TEST_MODE:
            users.extend(test_users[:10-len(users)])
        # self.teams = self.balance_teams(users.to_dict('records'))
        self.bot = bot
        self.disc_bot = disc_bot
        self.leaderboard_channel = leaderboard_channel
        self.teams = self.balance_teams(users)
        self.players = users
        self.match_size = 1 #FOR TESTING
        for player in self.players:
            player['winner_vote'] = None
            

    async def assign_roles(self):
        in_game_role = self.bot.guild.get_role(in_game_role_id)
        in_queue_role = self.bot.guild.get_role(in_queue_role_id)
        for player in self.teams[0] + self.teams[1]:
            if 'discord_id' in player.keys():
                # user = self.disc_bot.get_user(player['discord_id'])
                user = self.bot.guild.get_member(player['discord_id'])
                await user.add_roles(in_game_role)
                await user.remove_roles(in_queue_role)
                
    async def print_teams(self):
        order = ['top', 'jungle', 'mid', 'adc', 'support']
        team1, team2 = self.teams
        # Sort teams by role order
        team1 = sorted(team1, key=lambda x: order.index(x['assigned_role']))
        team2 = sorted(team2, key=lambda x: order.index(x['assigned_role']))
        elo_one = [x['elo'] for x in team1]
        elo_two = [x['elo'] for x in team2]
        elo_one = round(sum(elo_one) / len(elo_one))
        elo_two = round(sum(elo_two) / len(elo_two))
        message = f'**-----Team 1 Average ELO: {elo_one} -----** \n'
        print(f'**-----Team 1 Average ELO: {elo_one} -----**')
        for player in team1:
            assigned_role = player['assigned_role']
            username = player['discord_id'] if 'discord_id' in player else player['player_name']
            elo = player['elo']
            role_pref = 'Primary' if assigned_role == player['primary_role'] else 'Secondary' if assigned_role == player['secondary_role'] else 'Filled'
            print(f'Role: {assigned_role} Player: {username} Elo: {elo} Preference: {role_pref}')
            message += f'Role: {assigned_role} Player: <@{username}> Elo: {elo} Preference: {role_pref}\n'
        print(f'**-----Team 2 Average ELO: {elo_two} -----**')
        message += f'**-----Team 2 Average ELO: {elo_two} -----**\n'
        for player in team2:
            assigned_role = player['assigned_role']
            username = player['discord_id'] if 'discord_id' in player else player['player_name']
            elo = player['elo']
            role_pref = 'Primary' if assigned_role == player['primary_role'] else 'Secondary' if assigned_role == player['secondary_role'] else 'Filled'
            print(f'Role: {assigned_role} Player: {username} Elo: {elo} Preference: {role_pref}')
            message += f'Role: {assigned_role} Player: <@{username}> Elo: {elo} Preference: {role_pref}\n'
        if self.bot:
            await self.bot.send(message)
    
    def balance_teams(self, players):
        # Define teams and roles
        teams = [0, 1]  # Team A, Team B
        roles = ["top", "mid", "jungle", "adc", "support"]

        # Initialize ILP problem
        prob = LpProblem("Team_Balancing", LpMaximize)
        
        # Define variables
        player_team_role = {}
        for i, player in enumerate(players):
            for team in teams:
                for role in roles:
                    player_team_role[(i, team, role)] = LpVariable(
                        f"player_{i}_team_{team}_role_{role}", 0, 1, LpInteger
                    )

        # Define Elo balance variable (absolute Elo difference between teams)
        team_elo_diff = LpVariable("team_elo_diff", 0)

        # Objective function: maximize role preference satisfaction and minimize Elo difference
        prob += (
            lpSum(
                player_team_role[(i, team, role)]
                * (
                    2 if players[i]["primary_role"] == role else 1 if role == players[i]["secondary_role"] else 2 if players[i]["primary_role"] == "fill" else 1 if players[i]["secondary_role"] == "fill" else 0
                )
                for i in range(len(players))
                for team in teams
                for role in roles
            )
            - team_elo_diff
        )

        # Constraints: each team should have one player per role
        for team in teams:
            for role in roles:
                prob += lpSum(player_team_role[(i, team, role)] for i in range(len(players))) == 1

        # Each player should be assigned to exactly one team and one role
        for i in range(len(players)):
            prob += lpSum(player_team_role[(i, team, role)] for team in teams for role in roles) == 1

        # Elo balance constraint
        team_a_elo = lpSum(player_team_role[(i, 0, role)] * players[i]["elo"] for i in range(len(players)) for role in roles)
        team_b_elo = lpSum(player_team_role[(i, 1, role)] * players[i]["elo"] for i in range(len(players)) for role in roles)
        prob += team_elo_diff >= team_a_elo - team_b_elo
        prob += team_elo_diff >= team_b_elo - team_a_elo

        # Solve the problem
        prob.solve(PULP_CBC_CMD(msg=False))

        # Extract the teams based on the solution
        team_a, team_b = [], []
        for i, player in enumerate(players):
            for role in roles:
                if value(player_team_role[(i, 0, role)]) == 1:
                    team_a.append({**player, "assigned_role": role})
                elif value(player_team_role[(i, 1, role)]) == 1:
                    team_b.append({**player, "assigned_role": role})

        return team_a, team_b
    
    async def wait_for_vote(self):
        # This is called when a match is ended and players must type !vote <team_number> to vote for the winning team,
        # needs at least 50% of players to vote for the winning team to end the match, otherwise if time runs out,
        # the team with the most votes wins.
        votes = []
        seen = []
        while len(votes) != self.match_size:
            print(f'End match votes {len(votes)}/{self.match_size}')
            for player in self.players:
                # print('winner_vote', player['winner_vote'])
                if player['winner_vote'] in [1,2] and player['discord_name'] not in seen:
                    seen.append(player['discord_name'])
                    votes.append(player['winner_vote'])
            if len([x for x in votes if x == 1]) > self.match_size // 2:
                return
            if len([x for x in votes if x == 2]) > self.match_size // 2:
                return
            await asyncio.sleep(1)  # Check every second
        return
    
    async def assign_vote(self, vote_author, vote):
        if vote in [1,2]:
            for player in self.players:
                if 'discord_id' in player.keys():
                    disc_id = player['discord_id']
                    vote_id = vote_author.id
                    if disc_id == vote_id:
                        print(f'Assigning vote {vote} to {vote_author}')
                        player['winner_vote'] = vote
                    # return
        return

    async def end_match(self):
        message = ''
        for player in self.players:
            if 'discord_id' in player.keys():
                discord_id = player['discord_id']
                message += f'<@{discord_id}>, '
        await self.bot.send(f'{message}Please vote for the winning team with !vote <team_number>, valid values are 1 or 2')
        print('Waiting for votes')
        # once called give players 3 minutes to vote for the winning team
        await asyncio.wait_for(self.wait_for_vote(), timeout=300)  # 5 minutes
        votes = [x['winner_vote'] for x in self.players if x['winner_vote']]
        # Get the most voted for team
        team_one_votes = len([x for x in votes if x == 1])
        team_two_votes = len([x for x in votes if x == 2])
        print(f'Team 1 votes: {team_one_votes}, Team 2 votes: {team_two_votes}')
        winner =  0 if team_one_votes > team_two_votes else 1
        elo_change = 20 # Make constant for now but will add enhancements later
        loser = 0
        if winner == 0:
            loser = 1

        await self.bot.send(f'Team {winner+1} wins!')

        update_users_elo([x['discord_id'] for x in self.teams[winner] if 'discord_id' in x.keys()], [elo_change for x in range(len(self.teams[winner]))])
        update_users_elo([x['discord_id'] for x in self.teams[loser] if 'discord_id' in x.keys()], [-elo_change for x in range(len(self.teams[winner]))])
        leaderboard = get_leaderboard()
        leaderboard_message = self.get_leaderboard_message(leaderboard)
        await self.leaderboard_channel.send(leaderboard_message)

    def get_leaderboard_message(self, leaderboard):
        message = ''
        for player in leaderboard:
            message += f'{player["Rank"]}. {player["Discord Username"]} - {player["Current ELO"]}\n'
        return message

    def __str__(self) -> str:
        team_str = ""
        for i, team in enumerate(self.teams):
            team_str += f"\nTeam {i+1}:"
            for player in team:
                team_str += f"\n  {player['player_name']} - {player['assigned_role']} (ELO: {player['elo']})"
        return team_str

if __name__ == '__main__':
    test_users = [
        {"player_name": "Luna", "primary_role": "Jungle", "secondary_role": "Top", "elo": 823},
        {"player_name": "Ezra", "primary_role": "ADC", "secondary_role": "Support", "elo": 795},
        {"player_name": "Kai", "primary_role": "Jungle", "secondary_role": "Jungle", "elo": 841},
        {"player_name": "Sage", "primary_role": "Top", "secondary_role": "Mid", "elo": 767},
        {"player_name": "Finn", "primary_role": "Support", "secondary_role": "ADC", "elo": 756},
        {"player_name": "Arya", "primary_role": "Mid", "secondary_role": "Support", "elo": 810},
        {"player_name": "Nova", "primary_role": "Jungle", "secondary_role": "ADC", "elo": 835},
        {"player_name": "Rey", "primary_role": "Top", "secondary_role": "Mid", "elo": 752},
        {"player_name": "Zara", "primary_role": "ADC", "secondary_role": "Top", "elo": 847},
        {"player_name": "Jace", "primary_role": "Support", "secondary_role": "Jungle", "elo": 779}
    ]

    test = Match(discord_users=test_users)