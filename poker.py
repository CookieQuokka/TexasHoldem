from modal import Stub, Image, Mount

image = (
    Image.debian_slim()
)

stub = Stub("poker", image=image)

with image.run_inside():
    from joblib import Parallel, delayed
    from math import sqrt
    from itertools import combinations
    import random
    from collections import Counter

VALUES = {str(i): i for i in range(2, 11)}
VALUES['J'] = 11
VALUES['Q'] = 12
VALUES['K'] = 13
VALUES['A'] = 14

SUITS = {
    'S': 'Spade',
    'H': 'Heart',
    'C': 'Club',
    'D': 'Diamond',
}

class Card:
    
    def __init__(self, card_str):
        self.card_str = card_str
        self.value = VALUES[card_str[:-1]]
        self.suit = SUITS[card_str[-1]]
    
    def __str__(self):
        return self.card_str
    

class Hand:
    def __init__(self, cards_str):
        # Adding a dictionary for memoization
        self.memo = {}
        assert len(set(cards_str.split(','))) == 5
        self.cards = sorted([Card(c) for c in cards_str.split(',')], key=lambda x: x.value, reverse=True)
        # Using Counter to create the histogram
        self.hist = Counter(c.value for c in self.cards)

        self.long = max(self.hist.values())
        self.comp_order = []
        for l in [4, 3, 2, 1]:
            for c in self.cards:
                if self.hist[c.value] == l:
                    self.comp_order.append(c.value)
        self.score = self.check_hand() * 15**5
        for i, n in enumerate(self.comp_order):
            self.score += n * 15**(4-i)


    def check_hand(self, verbose=False):
        if 'rank' in self.memo:
            return self.memo['rank']

        if self.is_royal_flush(verbose):
            rank = 9
        elif self.is_straight_flush(verbose):
            rank = 8
        elif self.is_four(verbose):
            rank = 7
        elif self.is_full_house(verbose):
            rank = 6
        elif self.is_flush(verbose):
            rank = 5
        elif self.is_straight(verbose):
            rank = 4
        elif self.is_set(verbose):
            rank = 3
        elif self.is_two_pair(verbose):
            rank = 2
        elif self.is_pair(verbose):
            rank = 1
        else:
            if verbose: print('High card')
            rank = 0

        self.memo['rank'] = rank
        return rank
    
    def is_royal_flush(self, verbose=False):
        if self.is_straight_flush(verbose) and sum([c.value for c in self.cards]) == 60:
            if verbose: print('Royal flush !!!!!')
            return True
        return False
    
    def is_straight_flush(self, verbose=False):
        if self.is_straight() and self.is_flush():
            if verbose: print('Straight flush')
            return True
        return False
    
    def is_four(self, verbose=False):
        if len(self.hist) == 2 and self.long == 4:
            if verbose: print('Four of a kind')
            return True
        return False
    
    def is_full_house(self, verbose=False):
        if len(self.hist) == 2 and self.long == 3:
            if verbose: print('Full house')
            return True
        return False
    
    def is_flush(self, verbose=False):
        for c in self.cards:
            if c.suit != self.cards[0].suit:
                return False
        if verbose: print('Flush')
        return True
    
    def is_straight(self, verbose=False):
        if [c.value for c in self.cards] == [14, 2, 3, 4, 5]:
            if verbose: print('Straight')
            return True  # A2345
        for i, c in enumerate(self.cards):
            if i > 0 and c.value != self.cards[i-1].value+1:
                return False
        if verbose: print('Straight')
        return True
    
    def is_set(self, verbose=False):
        if self.long == 3 and not self.is_full_house():
            if verbose: print('Set')
            return True
        return False
    

    def is_two_pair(self, verbose=False):
        if self.long == 2 and len(self.hist) == 3:
            if verbose: print('Two pairs')
            return True
        return False
    

    def is_pair(self, verbose=False):
        if self.long == 2 and len(self.hist) == 4:
            if verbose: print('Pair')
            return True
        return False

def create_batches(lst, n):
    # lst: original list of inputs
        # number of batches
    k, m = divmod(len(lst), n)
    return (lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))

        
def top_hand(cards_str):
    assert len(cards_str.split(',')) == 7
    top_score = 0
    top_hand = None
    for h in combinations(cards_str.split(','), 5):
        hand = Hand(','.join(h))
        if hand.score > top_score:
            top_hand = hand
            top_score = hand.score
    return top_hand, top_score

DECK = [
    ''.join([v, s]) for v in '2,3,4,5,6,7,8,9,10,J,Q,K,A'.split(',') for s in ['S', 'H', 'C', 'D']
]

@stub.function(timeout = 2400)
def poker_game(players, flop=None, turn=None, verbose=True):     
    drawn = []
    for p in players:
        assert len(p.split(',')) == 2
        drawn += p.split(',')
    
    if flop:
        assert len(flop.split(',')) == 3
        drawn += flop.split(',')
        players = [','.join([p, flop]) for p in players]
    
    if turn:
        assert turn in DECK
        assert flop is not None
        drawn.append(turn)
        players = [','.join([p, turn]) for p in players]
        
    remain_deck = [c for c in DECK if c not in drawn]
    draw = ','.join(random.sample(remain_deck, 7-len(players[0].split(','))))
    
    high_score = 0
    winner = 0
    for i, p in enumerate(players):
        
        th, score = top_hand(','.join([p, draw]))
        if score > high_score:
            winner = i
            high_score = score
        if verbose:
            print(','.join([p, draw]))
            print('->', th)
            th.check_hand(verbose=True)
            print()
    return winner

@stub.function(timeout = 2400)
def poker_mc(players, flop=None, turn=None, n_rounds=100):
    wins = [0 for _ in players]
    session_arg = [
        (players, None, None, False)
    ]


    # customize here
    batch_num = min(10, n_rounds)
    res = []
    # for i in range(0, batch_num):
    #     res.extend(list(poker_game.starmap(session_arg * int(n_rounds / batch_num))))

    for i in res:
        wins[i] += 1
    
    return [w / n_rounds for w in wins]

@stub.local_entrypoint()
def main():
    # session_arg = [('2C,2D', '3C,4D', '10H,KD')]
    session_args = []

    # customize here
    mine = ['2C','2D']

    # customize here
    sample_suit = ['S','H']
        
    remain_deck = [c for c in DECK if c not in mine]
    
    opponent = list(combinations(remain_deck, 2))
    # Getting all combinations of 2 cards from the remaining deck
    all_combinations = list(combinations(remain_deck, 2))

    # Filtering combinations to include only those with different suits
    opponent = [pair for pair in all_combinations if (pair[0][-1] == sample_suit[0] and
                pair[1][-1] == sample_suit[1]) or (pair[0][-1] == sample_suit[1] and
                pair[1][-1] == sample_suit[0])]

    mine_str = ','.join(mine)
    flop = None
    turn = None
    n_rounds = 1000
    for e in opponent:
        session_args.append(((mine_str, ','.join(e)), flop, turn, n_rounds))

    # session_args = [(('2C,2D', '5S,6D'), None, None, 5), 
    #                 (('2C,2D', '9H,8S'), None, None, 5)]
    # target processing 10000 trajectories for 0.08s

    # batch processing the input
    # customize here
    batch_num = min(1, len(session_args))
    batches = list(create_batches(session_args, batch_num))
    results = []
    # for batch in batches:
    #     results.extend(list(poker_mc.starmap(batch)))

    results = Parallel(n_jobs=8)(delayed(poker_mc.remote)(batch) for batch in session_args)

    # Calculate the average across columns
    averages = [sum(column) / len(column) for column in zip(*results)]
    print(averages)