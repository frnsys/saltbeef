import random
from collections import defaultdict
from saltbeef.generate import data


def weighted_choice(choices):
    """
    Random selects a key from a dictionary,
    where each key's value is its probability weight.
    """
    # Randomly select a value between 0 and
    # the sum of all the weights.
    rand = random.uniform(0, sum(choices.values()))

    # Seek through the dict until a key is found
    # resulting in the random value.
    summ = 0.0
    for key, value in choices.items():
        summ += value
        if rand < summ: return key

    # If this returns False,
    # it's likely because the knowledge is empty.
    return False


class Markov():
    def __init__(self, fnames, state_size=3):
        """
        Recommended `state_size` in [2,5]
        """
        if isinstance(fnames, str):
            fnames = [fnames]

        terms = []
        for fname in fnames:
            terms += data.load_lexicon(fname)
        mem = defaultdict(lambda: defaultdict(int))

        for t in terms:
            # Beginning & end
            mem['^'][t[:state_size]] += 1
            mem[t[-state_size:]]['$'] += 1

            for i in range(len(t) - state_size):
                prev = t[i:i+state_size]
                next = t[i+1:i+1+state_size]
                mem[prev][next] += 1

        self.mem = mem
        self.state_size = state_size

    def generate(self):
        ch = weighted_choice(self.mem['^'])
        out = [ch]
        while True:
            ch = weighted_choice(self.mem[ch])
            if ch == '$':
                break
            out.append(ch[self.state_size-1])
        return ''.join(out)


