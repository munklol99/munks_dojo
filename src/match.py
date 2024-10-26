from mongo_helpers import get_user_data, get_database, update_users_elo
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpInteger, value, PULP_CBC_CMD

class Match():
    def __init__(self, discord_users: list):
        if len(discord_users) < 10:
            print(f"Not enough users to start a match {len(discord_users)} / 10")
        elif len(discord_users) > 10:
            print(f"Too many users to start a match {len(discord_users)} / 10")
        
        users = get_user_data(discord_users)
        print(users)
        self.teams = self.balance_teams(users.to_dict('records'))
        self.print_teams(self.teams[0], self.teams[1])
        self.end_match(0)
    
    def print_teams(self, team1, team2):
        print('-----Team 1-----')
        for player in team1:
            assigned_role = player['assigned_role']
            username = player['Discord Username']
            elo = player['Current ELO']
            print(f'Role: {assigned_role} Player: {username} Elo: {elo}')
        print('-----Team 2-----')
        for player in team2:
            assigned_role = player['assigned_role']
            username = player['Discord Username']
            elo = player['Current ELO']
            print(f'Role: {assigned_role} Player: {username} Elo: {elo}')
    
    def balance_teams(self, players):
        # Define teams and roles
        teams = [0, 1]  # Team A, Team B
        roles = ["Top", "Mid", "Jungle", "ADC", "Support"]

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
                    2 if players[i]["Preferred Role"] == role else 1 if role in players[i].get("Roles", []) else 0
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
        team_a_elo = lpSum(player_team_role[(i, 0, role)] * players[i]["Current ELO"] for i in range(len(players)) for role in roles)
        team_b_elo = lpSum(player_team_role[(i, 1, role)] * players[i]["Current ELO"] for i in range(len(players)) for role in roles)
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

    def end_match(self, winner):
        elo_change = 20 # Make constant for now but will add enhancements later
        loser = 0
        if winner == 0:
            loser = 1
        update_users_elo([x['Discord Username'] for x in self.teams[winner]], [elo_change for x in range(len(self.teams[winner]))])
        update_users_elo([x['Discord Username'] for x in self.teams[loser]], [-elo_change for x in range(len(self.teams[winner]))])

if __name__ == '__main__':
    dbname = get_database()
    
    dojo_collection = dbname['userData']
    
    test_users = []
    for item in dojo_collection.find()[0:10]:
        test_users.append(item['Discord Username'])
        
    test = Match(discord_users=test_users)