## PokerLearner Instructions
To run the program, you must have python3.

Simply clown or download the repository and cd into the root directory. Then type:
`python3 main.py <num_hands> <opponent_type>`

Opponent types include:
  - HumanPlayer: instructions will be printed and take responses from the command line.
  - QLearningPlayer: makes q-learning players play against itself.
  - RandomPlayer: randomly chooses an action from the list of legal actions.
  - TightPlayer: a player that heuristically bets conservatively.
  - AggressivePlayer: a player that heuristically bets aggressively. 
  
The weights that the q-learning agent are pickled and stored in `/learning_data/q_learning_weights_*.p` where `*` changes depending on what type of opponent the computer is playing against.
To see what these weights are, you can simply run python3 from the root directory and type:
```
>>> import pickle
>>> weights = pickle.load(open("learning_data/q_learning_weights_*.p", "rb"))
```

### Credits
deuces: https://github.com/worldveil/deuces 
