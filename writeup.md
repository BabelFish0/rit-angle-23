# Explanation of final solution
## Jude Young
----

Our approach to the final question is centred around the [Gurobi python optimiser](https://support.gurobi.com/hc/en-us/articles/17278438215313-Tutorial-Getting-Started-with-the-Gurobi-Python-API).

## Imports & Params

```python
import numpy as np
import gurobipy as gp
import math

n_R = 3 # Rounds
n_I = 10 # Individuals per team | Boards --- n_I*n_R must be even
n_T = 11 # Teams
```

## Specifying the Problem

One of the largest challenges is figuring out how to specify the problem. There are so many categories - Teams, Boards, Players, Rounds, Pieces - that this seems overwhelming at the start. After much thought, the approach I took was to describe the entire problem in two binary arrays:

- `games`, a dictionary where every round-specific pairing that is possible is associated with a binary variable. A 1 represents a game pairing that happens whilst a 0 represents that it does not happen. For example, the Gurobi `Var` associated with round 1, A.01 against B.01 is `games[(0, 0, 4)]`.

- `colours`, another dictionary where every player in each round is associated with a binary variable for if they play white (1) or not (0). For example, the Gurobi `Var` associated with A.01's round 2 colour is `colours[(1, 0)]`.

It should be noted here that to simplify the problem, the players are just represented as a number from $0$ to $BN-1$ (written as `n_I * n_T - 1` in the code's nomenclature). So the player's rank is their number, $i \mod{n_I}$ aka `i % n_I` and their team is the floor division of their global id by the number of people per team, `i // n_I`. In this way all the information is still retained, but it is just easier to work with one axis rather than Teams, Individuals, Boards in numbers and letters!

Now the first order of business is to create all the valid pairings (duplicated across each round):

```python
pairs_of_players_0 = [] #Each possible pair of players

for p1 in range(n_I*n_T):
    for p2 in range(n_I*n_T):
        if p1 % n_I == p2 % n_I or p1 % n_I == p2 % n_I + 1 or p1 % n_I == p2 % n_I - 1: # check if rank only differs by 1 max.
            if p1 // n_I != p2 // n_I: # check that not on same team.
                for r in range(n_R):
                    if (r, p2, p1) not in pairs_of_players_0 and p1!= p2:
                        pairs_of_players_0.append((r, p1, p2)) # this means p1 < p2
```

This is quite ugly but makes it unlikely to accidentally skip a configuration. The order of players does not matter so duplicates are not added to the list. Then the model can be initialized and the previously mentioned variables added.

```python
m = gp.Model("mip1")

game_happens = pairs_of_players_0
game_id = [str(game) for game in game_happens] # list of all possible games
round_players = [(r, i) for r in range(n_R) for i in range(n_I*n_T)]
player_id = [str(player) for player in round_players] # for each round list of all players

'''create a dict, `games`, where the key is the game configuration in the format (round, player1, player2) and the associated value is 1 or 0 for if the game happens or not.'''
games = m.addVars(game_happens, vtype = gp.GRB.BINARY, name = game_id)
'''create a dict, `colours`, where the key is the player of a certain round in the format (round, player) and the associated value is 1 or 0 for if they play white or not.'''
colours = m.addVars(round_players, vtype = gp.GRB.BINARY, name = player_id)
```

The `addVars` method adds a Gurobi `Var` object with the specified data type for every entry in the array passed as the first parameter. The `name` specifies what to use as the key in the dictionary that `addVars` returns. Here the game conficuration (call it the 'game_id') is used so that the associated `Var` can be accessed as previously mentioned.

## Constraints

Most of the code is devoted to describing the constraints to the optimiser. A useful function is first defined:

```python
def find_by_element(tuple_list, key, e):
    entries_with_e = []

    for tuple in tuple_list:
        if tuple[e] == key:
            entries_with_e.append(tuple)
    return entries_with_e
```

which is heavily used for finding games that a player is in and all the games of a team etc.

The first constraints are 'trivial' in that they describe the basic prinicple of the game in relation to the variables we have created.

```python
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
```

For each of these, the code generally finds the games or players relevant to the constraint, and then adds a constraint to the model using the `addConstr` method which takes a linear expression of `Var` objects. Most commonly this is a big sum of the associated binary variables. For example, in (2) we use the `find_by_element` function to find all the games a player plays and split them by round. Then we dictate that the binary associated variables must sum to 1 for each of those groups, meaning the player plays exactly once per round.

Note that the constraint in (3) is conditional, meaning that `(A == 1) >> (B == 1)` is interpreted as 'If A = 1, enforce the constraint that B = 1'.

The problem's (less-trivial!) constraints are then added. First, the ones relevant to even $B$ cases:

```python
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
```

These work the same as before. The only new expression is for range, where `A == [x, y]` means $A \isin [x, y]$ whilst obeying the rules of the data type for `A`. Obviously (7) is not necessary, but it makes it easier for the optimizer to be tested in the even cases as we can be sure that the other constraints (8 onwards) are not being used.

Then the odd-case constraints are added also:

```python
# (8) One up/down float per board per round max
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
```

## Objective

The cost functions are not easy to specify to the optimiser because of both the large and sophistocated sums and the inclusion of absolute values. The optimiser stores linear expressions in matrix format with the `Var` objects and their coefficients. This means it cannot store expressions with the absolute value. To get around this, I create a variable for every calculated value $X_t$ inside of $\sum|X_t|$ and another set of variables constrained to $|X_t|$. Then the relevant detriment is obtained from the sum of these.

For $Q_Z$ the fraction has been moved so:

$$Q_Z=\sum_{i=1}^N\left|1-\frac{4}{R B(B+1)} \sum_{l=1}^B l w_{i l}\right|$$

$$R B(B+1)Q_Z=\sum_{i=1}^N\left|R B(B+1)-4 \sum_{l=1}^B l w_{i l}\right|$$.

`z` is set to the RHS of this so in the final cost calculation the expression is `x + y + (1/(n_R*n_I*(n_I+1)))*z`. This allows the data type of `z` to be integer which is helpful to the optimiser.

Also, the way that `z` is calculated differs slightly to the mathematical notation. $\sum l w_{i l}$ is calculated using `sum([(i+1)*colours[(r, t*n_I+i)] for r in range(n_R) for i in range(n_I)])`. What this means is across each of the players in the team their board no. (+1 to account for indexing) is multiplied by the colour (0 for black, 1 for white) in each round and added up. This is equivalent to the expression but more convenient for how the data is stored.

```python
# (1) X

x = m.addVar(vtype=gp.GRB.INTEGER, name='x')
wb_deviation = m.addVars([(r, t) for t in range(n_T) for r in range(n_R)], lb=-100000, vtype = gp.GRB.INTEGER, name=[str((r, t)) for t in range(n_T) for r in range(n_R)])
abs_wb_deviation = m.addVars([(r, t) for t in range(n_T) for r in range(n_R)], vtype = gp.GRB.INTEGER, name=[str((r, t)) for t in range(n_T) for r in range(n_R)])
for t in range(n_T):
    for r in range(n_R):
        m.addConstr(wb_deviation[(r, t)] == gp.quicksum([colours[(r, n_I*t+i)] for i in range(n_I)])-n_I/2)
        m.addConstr(abs_wb_deviation[(r, t)] == gp.abs_(wb_deviation[(r, t)]))
m.addConstr(x == sum([abs_wb_deviation[(r, t)] for t in range(n_T) for r in range(n_R)]))
        
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

z = m.addVar(vtype=gp.GRB.INTEGER, name='z')
colour_deviation = m.addVars([t for t in range(n_T)], lb=-100000, vtype=gp.GRB.INTEGER, name=[str(t) for t in range(n_T)])
abs_colour_deviation = m.addVars([t for t in range(n_T)], vtype=gp.GRB.INTEGER, name=[str(t) for t in range(n_T)])
for t in range(n_T):
    m.addConstr(colour_deviation[t] == n_R*n_I*(n_I+1) - 4*sum([(i+1)*colours[(r, t*n_I+i)] for r in range(n_R) for i in range(n_I)]))
    m.addConstr(abs_colour_deviation[t] == gp.abs_(colour_deviation[t]))
m.addConstr(z == sum([abs_colour_deviation[t] for t in range(n_T)]))

# objective

m.setObjective(x + y + (1/(n_R*n_I*(n_I+1)))*z, gp.GRB.MINIMIZE)
m.Params.CSClientLog = 0

# run

m.optimize()

played_games = []
for game_option in games:
    if games[game_option].X == 1:
        if colours[(game_option[0], game_option[1])].X == 1: #p1 plays white
            played_games.append(game_option)
        else:
            played_games.append((game_option[0], game_option[2], game_option[1]))
played_games = np.array(played_games)
```

The solution printer then double checks the cost using a different method and converts the solution to the desired format.