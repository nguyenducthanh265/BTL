"""Play one game between two agents and record what happened."""
import time


def play_game(game, first, second, rng):
    """Play until the end. ``first`` plays the side that is to move in ``game``."""
    first_side = game.to_play
    second_side = -first_side
    agents = {first_side: first, second_side: second}
    spent = {first_side: 0.0, second_side: 0.0}
    nodes = {first_side: 0, second_side: 0}
    moves = []
    while game.winner() is None:
        side = game.to_play
        agent = agents[side]
        start = time.perf_counter()
        move = agent.choose(game, rng)
        spent[side] += time.perf_counter() - start
        nodes[side] += agent.nodes
        game.play(move)
        moves.append(move)
    return {
        "winner": game.winner(),
        "plies": len(moves),
        "moves": moves,
        "first_time": spent[first_side],
        "second_time": spent[second_side],
        "first_nodes": nodes[first_side],
        "second_nodes": nodes[second_side],
    }
