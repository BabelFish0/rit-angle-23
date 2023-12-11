import numpy as np
import gurobipy as gp
import math
#from gurobipy import GRB

n_R = 3 # Rounds
n_I = 10 # Individuals per team | Boards --- n_I*n_R must be even
n_T = 11 # Teams

pairs_of_players_0 = [] #Each possible pair of players

for p1 in range(n_I*n_T):
    for p2 in range(n_I*n_T):
        if p1 % n_I == p2 % n_I or p1 % n_I == p2 % n_I + 1 or p1 % n_I == p2 % n_I - 1: # check if rank only differs by 1 max.
            if p1 // n_I != p2 // n_I: # check that not on same team.
                for r in range(n_R):
                    if (r, p2, p1) not in pairs_of_players_0 and p1!= p2:
                        pairs_of_players_0.append((r, p1, p2)) # this means p1 < p2

game_happens = pairs_of_players_0
game_id = [str(game) for game in game_happens] # list of all possible games
round_players = [(r, i) for r in range(n_R) for i in range(n_I*n_T)]
player_id = [str(player) for player in round_players] # for each round list of all players
#print(game_id)

#-----------------   Integer Program

m = gp.Model("mip1")

'''create a dict, `games`, where the key is the game configuration in the format (round, player1, player2) and the associated value is 1 or 0 for if the game happens or not.'''
games = m.addVars(game_happens, vtype = gp.GRB.BINARY, name = game_id)
'''create a dict, `colours`, where the key is the player of a certain round in the format (round, player) and the associated value is 1 or 0 for if they play white or not.'''
colours = m.addVars(round_players, vtype = gp.GRB.BINARY, name = player_id)

#-----------------   Constraints


# Utility
def find_const_ranges(tuple_list, e=2):
    global n_I
    constant_ranges = []
    start_index = 0

    for i in range(1, len(tuple_list)):
        if tuple_list[i][e] // n_I != tuple_list[i - 1][e] // n_I:
            constant_ranges.append((start_index, i - 1))
            start_index = i

    constant_ranges.append((start_index, len(tuple_list) - 1))
    constant_entries = [tuple_list[cr[0]:cr[1]+1] for cr in constant_ranges]

    return constant_entries

def find_by_element(tuple_list, key, e):
    entries_with_e = []

    for tuple in tuple_list:
        if tuple[e] == key:
            entries_with_e.append(tuple)
    return entries_with_e
       

# (1) No-one plays twice against the same team
for player_id in range(n_I*n_T):
    # find all games that player_id is in
    players_games = find_by_element(game_happens, player_id, 1)
    players_games.extend(find_by_element(game_happens, player_id, 2))
    for team_id in range(n_T):
        players_team_games = []
        if team_id != player_id // n_I: #check not same team as player
            for opp_player in [team_id*n_I+i for i in range(n_I)]: #list of opponents in certain team
                players_team_games.extend(find_by_element(players_games, opp_player, 1))
                players_team_games.extend(find_by_element(players_games, opp_player, 2))
            m.addConstr(sum([games[g] for g in players_team_games]) <= 1)

 
# (2) Each Individual must play exactly once per round
for player_id in range(n_I*n_T):
    players_games = find_by_element(game_happens, player_id, 1)
    players_games.extend(find_by_element(game_happens, player_id, 2))
    for round in range(n_R):
        m.addConstr(sum([games[g] for g in find_by_element(players_games, round, 0)]) == 1)


# (3) If a game happens, the players in it play white and black
for game_option in game_happens:
    r = game_option[0]
    p1 = game_option[1]
    p2 = game_option[2]
    m.addConstr((games[game_option] == 1) >> (colours[(r, p1)] + colours[(r, p2)] == 1)) #colour bools of the two players add to one (one plays white=1, other plays black=0)


# (4) Each Team plays each other team floor or ceil RB/(N-1)
'''The total games played by a team is RB. The number of opponent teams is N-1. This constraint exists to ensure an even distribution of matches between teams (the ideal being non-integer RB/(N-1))'''
for team_id in range(n_T):
    teams_games = []
    for i in range(n_I):
        teams_games.extend(find_by_element(game_happens, team_id*n_I+i, 1))
        teams_games.extend(find_by_element(game_happens, team_id*n_I+i, 2))
    # find sets of opponents belonging to one team
    for opp_team_id in range(n_T):
        if opp_team_id != team_id:
            opp_teams_games = []
            for opp_player in [opp_team_id*n_I+i for i in range(n_I)]:
                opp_teams_games.extend(find_by_element(teams_games, opp_player, 1))
                opp_teams_games.extend(find_by_element(teams_games, opp_player, 2))
            m.addConstr(sum([games[g] for g in opp_teams_games]) == [math.floor(n_R*n_I/(n_T-1)), math.ceil(n_R*n_I/(n_T-1))])


# (5) Each Player gets white and black the same number of times ± 1
for player_id in range(n_I*n_T):
    m.addConstr(sum([colours[(r, player_id)] for r in range(n_R)]) == [math.floor(n_R/2), math.ceil(n_R/2)])


# (6) Each Team plays black the same number of times as white
for team_id in range(n_T):
    teams_colours = []
    for player_id in [team_id*n_I+i for i in range(n_I)]:
        teams_colours.extend([(r, player_id) for r in range(n_R)])
    # print(teams_colours)
    m.addConstr(sum([colours[t] for t in teams_colours]) == int(n_I*n_R/2)) #number of games played by the team in total / 2


# (7) For an even number of teams no floats occur
if n_T % 2 == 0:
    for game_option in game_happens:
        if game_option[1] % n_I != game_option[2] % n_I: #if player ranks don't align
            m.addConstr(games[game_option] == 0)


# (8) One up/down float per board per round max **CHECK THIS IS WORKING**
for r in range(n_R):
    round_games = find_by_element(game_happens, r, 0) # find every game in round r
    for b in range(n_I): # look at each board in turn
        float_games = []
        for game in round_games: # look at all games in round r
            if (game[1] % n_I == b or game[2] % n_I == b) and (game[1] % n_I != b or game[2] % n_I != b):
                float_games.append(game)
        #print([g for g in float_games])
        m.addConstr(sum([games[g] for g in float_games]) <= 1)


# (9) No Player gets more than one float
for player_id in range(n_I*n_T):
    players_games = find_by_element(game_happens, player_id, 1)
    players_games.extend(find_by_element(game_happens, player_id, 2))
    float_games = []
    for game in players_games:
        if game[1] % n_I != player_id % n_I or game[2] % n_I != player_id % n_I:
            float_games.append(game)
    m.addConstr(sum([games[g] for g in float_games]) <= 1)


# (10) Each team gets 2 + floor(RB/(2N)) up/down floats each max
for team_id in range(n_T):
    up_floats = []
    down_floats = []
    for game in game_happens:
        if game[1] // n_I == team_id:
            if game[1] % n_I == game[2] % n_I - 1: #downfloat for our team
                down_floats.append(game)
            if game[1] % n_I == game[2] % n_I + 1: #upfloat for our team
                up_floats.append(game)
        if game[2] // n_I == team_id:
            if game[2] % n_I == game[1] % n_I - 1: #downfloat for our team
                down_floats.append(game)
            if game[2] % n_I == game[1] % n_I + 1: #upfloat for our team
                up_floats.append(game)
    m.addConstr(sum([games[g] for g in up_floats]) <= 2 + math.floor(n_R*n_I/(2*n_T)))
    m.addConstr(sum([games[g] for g in down_floats]) <= 2 + math.floor(n_R*n_I/(2*n_T)))


# (11) All upfloats have the white pieces
for game_option in game_happens:
    if game_option[1] % n_I == game_option[2] % n_I + 1: #upfloat for p1
        m.addConstr((games[game_option] == 1) >> (colours[(game_option[0], game_option[1])] == 1))
    if game_option[2] % n_I == game_option[1] % n_I + 1: #upfloat for p2
        m.addConstr((games[game_option] == 1) >> (colours[(game_option[0], game_option[2])] == 1))


#-----------------   Cost functions

# (1) X
x = m.addVar(vtype=gp.GRB.INTEGER, name='x')
wb_deviation = m.addVars([(r, t) for t in range(n_T) for r in range(n_R)], lb=-100000, vtype = gp.GRB.INTEGER, name=[str((r, t)) for t in range(n_T) for r in range(n_R)])
abs_wb_deviation = m.addVars([(r, t) for t in range(n_T) for r in range(n_R)], vtype = gp.GRB.INTEGER, name=[str((r, t)) for t in range(n_T) for r in range(n_R)])
for t in range(n_T):
    for r in range(n_R):
        m.addConstr(wb_deviation[(r, t)] == gp.quicksum([colours[(r, n_I*t+i)] for i in range(n_I)])-n_I/2)
        m.addConstr(abs_wb_deviation[(r, t)] == gp.abs_(wb_deviation[(r, t)]))
m.addConstr(x == sum([abs_wb_deviation[(r, t)] for t in range(n_T) for r in range(n_R)]))

# x = gp.quicksum([gp.quicksum([gp.abs_(gp.quicksum([colours[(r, n_I*t+i)] for i in range(n_I)])-n_I/2) for t in range(n_T)]) for r in range(n_R)])
# x = m.addVar(vtype=gp.GRB.INTEGER, name='x')
# exprs = []
# temp_vars = []
# for t in range(n_T):
#     for r in range(n_R):
#         expr = gp.quicksum([colours[(r, n_I*t+i)] for i in range(n_I)])-n_I/2
#         wb_deviation = m.addVar(vtype=gp.GRB.INTEGER, name=str((r, t)))
#         m.addConstr(wb_deviation == gp.abs_(expr))
#         temp_vars.append(wb_deviation)
# x = gp.quicksum(temp_vars)
        
# (2) Y

y = m.addVar(vtype=gp.GRB.INTEGER, name='y')
float_deviation = m.addVars([t for t in range(n_T)], lb=-100000, vtype=gp.GRB.INTEGER, name=[str(t) for t in range(n_T)])
abs_float_deviation = m.addVars([t for t in range(n_T)], vtype=gp.GRB.INTEGER, name=[str(t) for t in range(n_T)])
for team_id in range(n_T): #identical method to constraint (10)
    up_floats = []
    down_floats = []
    for game in game_happens:
        if game[1] // n_I == team_id:
            if game[1] % n_I == game[2] % n_I - 1: #downfloat for our team
                down_floats.append(game)
            if game[1] % n_I == game[2] % n_I + 1: #upfloat for our team
                up_floats.append(game)
        if game[2] // n_I == team_id:
            if game[2] % n_I == game[1] % n_I - 1: #downfloat for our team
                down_floats.append(game)
            if game[2] % n_I == game[1] % n_I + 1: #upfloat for our team
                up_floats.append(game)
    m.addConstr(float_deviation[team_id] == sum([games[g] for g in up_floats]) - sum([games[g] for g in down_floats]))
    m.addConstr(abs_float_deviation[team_id] == gp.abs_(float_deviation[team_id]))
m.addConstr(y == sum([abs_float_deviation[t] for t in range(n_T)]))

# (3) Z

'''
$Z$. For each team, the black games and white games should be evenly distributed down the team (i.e. it is undesirable for the higher boards to have a preponderance of whites and the lower boards to have a preponderance of blacks).

To measure the detriment $Q_Z$ against goal $Z$, calculate
$$
Q_Z=\sum_{i=1}^N\left|1-\frac{4}{R B(B+1)} \sum_{l=1}^B l w_{i l}\right|
$$
where $w_{i l}$ is the number of times that the player on board $l$ of team $i$ has white.
'''

z = m.addVar(vtype=gp.GRB.INTEGER, name='z')
colour_deviation = m.addVars([t for t in range(n_T)], lb=-100000, vtype=gp.GRB.INTEGER, name=[str(t) for t in range(n_T)])
abs_colour_deviation = m.addVars([t for t in range(n_T)], vtype=gp.GRB.INTEGER, name=[str(t) for t in range(n_T)])
for t in range(n_T):
    #print([(i+1)*colours[(r, t*n_I+i)] for r in range(n_R) for i in range(n_I)])
    m.addConstr(colour_deviation[t] == n_R*n_I*(n_I+1) - 4*sum([(i+1)*colours[(r, t*n_I+i)] for r in range(n_R) for i in range(n_I)]))
    m.addConstr(abs_colour_deviation[t] == gp.abs_(colour_deviation[t]))
m.addConstr(z == sum([abs_colour_deviation[t] for t in range(n_T)]))

m.setObjective(x + y + (1/(n_R*n_I*(n_I+1)))*z, gp.GRB.MINIMIZE)
m.Params.CSClientLog = 0

m.optimize()

played_games = []
for game_option in games:
    if games[game_option].X == 1:
        if colours[(game_option[0], game_option[1])].X == 1: #p1 plays white
            played_games.append(game_option)
        else:
            played_games.append((game_option[0], game_option[2], game_option[1]))
played_games = np.array(played_games)
# print(played_games)

#-----------------   Printer

#x
q_x = 0
for t in range(n_T):
    for r in range(n_R):
        black = 0
        white = 0
        for game in played_games:
            if game[0] == r:
                if game[1] // n_I == t:
                    white += 1
                if game[2] // n_I == t:
                    black += 1
        q_x += abs(white-black)

#y
q_y = 0
for t in range(n_T):
    up_f = 0
    down_f = 0
    for game in played_games:
        if game[1] // n_I == t and game[1] % n_I != game[2] % n_I: #an up float (always w) for team t
            up_f += 1
        if game[2] // n_I == t and game[1] % n_I != game[2] % n_I:
            down_f += 1
    q_y += abs(up_f - down_f)

#z
q_z = 0
for t in range(n_T):
    sum_whites = 0
    for game in played_games:
        if game[1] // n_I == t:
            sum_whites += (game[1] % n_I + 1)
    q_z += abs(1 - (4/(n_R*n_I*(n_I+1)))*sum_whites)        

print(f'{q_x} + {q_y} + {q_z:.2f}')
for game in played_games[np.argsort(played_games[:, 0])]:
    r = game[0] + 1
    t_w = game[1] // n_I
    S = chr(ord('A')+t_w)
    i_w = game[1] % n_I + 1
    t_b = game[2] // n_I
    T = chr(ord('A')+t_b)
    i_b = game[2] % n_I + 1
    print(f'{r},{S}.{i_w:02d},{T}.{i_b:02d}')

gp.disposeDefaultEnv()

