Hello World!

This repo is dedicated to an In-House Bot I am making with a friend of mine for a small League of Legends Discord community.

The intended features of this bot are:
Member Management:
  1. Entering New Member Info (Discord ID, Discord Name, Roles (2+), Preferred Role (1)
  2. Save Member Info to a .json file ('members.json')
  3. Edit Member Details
  4. Delete Member
  5. Display All Members in a Tabular View in Desc. Order by ELO (with an Indexed 'Rank' value starting with '1')
  6. Have match results save into the 'members.json' file
  7. Have match results saved into a 'match_history.json' file
  8. Riot API Usage (WIP)

Queue:
  1. Add Members to Queue (Primary Key = Discord ID)
  2. Save Queue to .json file ('queue.json)
  3. Edit Members in Queue
  4. Remove Member from Queue
  5. Display Queue in tabular view in Desc. Order by ELO
  6. Display "X members needed to start game" & a Print when the game can be started
  7. Option to Start the game, triggering the Matchmaking / Team Balancing

Matchmaking / Team Balancing Algorithm:
Requirements: 1 player per role, each team has 5 unique roles (Top, Jungle, Mid, ADC, Support)
This matchmaking algorithm balances in 1 of 3 methods
  Method 1: Prioritizing Balanced Matchups
    1. Run iterations of each possible matchup given a player's preferred role (5!)
    2. Balance the teams if 3 matchups are within a set X ELO difference
  Method 2: Prioritizing Role Assignment Accuracy
    1. Try to have as many players get their roles in this order (Preferences for Non-Fill Players -> Playable Roles -> Fill 'Fill' Players -> Fill Remaining Unassigned Players to Unassigned Roles)
    2. The players who get priority to their preferences should be those with the least playable roles
  Method 3: Prioritizing Avg. Team ELO Balancing (difference between teams set to 'X' ELO)
    1. First find the iteration of the teams that provide the smallest Average ELO Difference between the 2 teams
    2. Assign roles afterwards like in Method 2
Teams are displayed in 2 tables, in role sorted order (Top --> Support)

Post-Game
  1. When the result of a game is entered, ELO is rewarded or deducted (MAX of X, MIN of Y) to each player
  2. The change in a player's ELO (without the Riot API) will be decided by their weight % of the Team's Average ELO (EX: The Rank 1 player will always gain the least / lose the most ELO)
  3. When the Riot API is integrated, this will be performance-based based on factors decided by us, the developers, with whatever key metrics & calculations we decide.
  
