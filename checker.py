import numpy as np
import math

n_R = 3 # Rounds
n_I = 4 # Individuals per team | Boards
n_T = 6 # Teams

letter_games = [
    '1,D.01,C.01',
    '1,A.01,B.01',
    '1,F.01,E.01',
    '2,E.01,A.01',
    '2,C.01,F.01',
    '2,B.01,D.01',
    '3,B.01,E.01',
    '3,D.01,F.01',
    '3,C.01,A.01',
    '1,C.02,B.02',
    '1,F.02,A.02',
    '1,E.02,D.02',
    '2,A.02,E.02',
    '2,B.02,D.02',
    '2,F.02,C.02',
    '3,A.02,C.02',
    '3,E.02,B.02',
    '3,D.02,F.02',
    '1,E.03,A.03',
    '1,C.03,F.03',
    '1,B.03,D.03',
    '2,F.03,D.03',
    '2,B.03,E.03',
    '2,A.03,C.03',
    '3,F.03,B.03',
    '3,D.03,A.03',
    '3,C.03,E.03',
    '1,D.04,A.04',
    '1,F.04,B.04',
    '1,C.04,E.04',
    '2,D.04,C.04',
    '2,E.04,F.04',
    '2,A.04,B.04',
    '3,A.04,F.04',
    '3,E.04,D.04',
    '3,B.04,C.04'
]

def convert_strings(input_list, n_I):
    result = []
    
    for item in input_list:
        parts = item.split(',')
        first_num = int(parts[0]) - 1
        second_letter, second_num, third_letter, third_num = parts[1][0], int(parts[1][2:]) - 1, parts[2][0], int(parts[2][2:]) - 1
        
        second_entry = (ord(second_letter) - ord('A')) * n_I + second_num
        third_entry = (ord(third_letter) - ord('A')) * n_I + third_num
        
        result.append((first_num, second_entry, third_entry))
    
    return result

played_games = np.array(convert_strings(letter_games, n_I))
print(played_games)

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
            sum_whites += (game[1] % n_I + 1) #board number
    q_z += abs(1 - (4/(n_R*n_I*(n_I+1)))*sum_whites)        

print(f'{q_x},{q_y},{q_z:.2f}')
for game in played_games[np.argsort(played_games[:, 0])]:
    r = game[0] + 1
    t_w = game[1] // n_I
    S = chr(ord('A')+t_w)
    i_w = game[1] % n_I + 1
    t_b = game[2] // n_I
    T = chr(ord('A')+t_b)
    i_b = game[2] % n_I + 1
    print(f'{r},{S}.{i_w:02d},{T}.{i_b:02d}')

#2/30