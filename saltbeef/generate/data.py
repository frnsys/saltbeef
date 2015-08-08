from glob import glob


def load_lexicon(fname):
    with open(fname, 'r', encoding='utf8') as f:
        return [l.lower().strip() for l in f.readlines()]

def load_lexicons(pattern):
    return sum([load_lexicon(f) for f in glob(pattern)], [])
