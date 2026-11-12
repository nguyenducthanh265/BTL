"""Game rules. Every game exposes the same small interface used by the search code.

Interface
---------
to_play          +1 or -1, the player to move (+1 moves first)
legal_moves()    list of moves, empty once the game is over
play(move)       apply a move in place
undo()           revert the last move
winner()         None while running, +1 / -1 for a win, 0 for a draw
clone()          independent copy
evaluate()       heuristic score from the point of view of player +1
simulate(p, rng) finish the game from here with rollout policy p, may mutate the
                 state, returns the reward of player +1 in [0, 1]
move_prior(m)    cheap heuristic quality of a move in [0, 1]
key()            hashable description of the position
"""
