import random
from saltbeef.generate import data, markov

animals = data.load_lexicon('data/animals.txt')
adjs = data.load_lexicons('data/adjectives/*.txt')
advs = data.load_lexicons('data/adverbs/*.txt')
cnt_nouns = data.load_lexicons('data/countable_nouns/*.txt')
ucnt_nouns = data.load_lexicons('data/uncountable_nouns/*.txt')
verbs = data.load_lexicons('data/verbs/*.txt')
prefixes = data.load_lexicon('data/prefixes.txt')
nation_mkv = markov.Markov('data/countries.txt')
anim_mkv = markov.Markov(['data/pokemon/pokemons.txt',
                          'data/animals.txt',
                          'data/monsters.txt'], state_size=3)
item_mkv  = markov.Markov(['data/pokemon/items.txt',
                           'data/star_trek/techs.txt',
                           'data/w40k/upgrades.txt'], state_size=3)
abil_mkv = markov.Markov(['data/pokemon/moves.txt',
                          'data/heroes_powers.txt',
                          'data/pokemon/abilities.txt',
                          'data/dota_skills.txt',
                          'data/lol_skills.txt',
                          'data/w40k/abilities.txt'], state_size=3)


def name():
    vocabs = [
        random.choice([adjs, nationalities]),
        [anim_mkv.generate() for i in range(100)]
    ]
    names = [random.choice(vocab) for vocab in vocabs]

    if random.random() >= 0.98:
        names[0] = random.choice(prefixes) + names[0]

    return ' '.join(names).title().replace('(', '').replace(')', '')


def item():
    vocabs = [
        adjs,
        ucnt_nouns + [item_mkv.generate() for i in range(10)] + [abil_mkv.generate() for i in range(10)]
    ]
    names = [random.choice(vocab) for vocab in vocabs]

    if random.random() >= 0.98:
        names[0] = random.choice(prefixes) + names[0]

    return ' '.join(names).title().replace('(', '').replace(')', '')


def move():
    move = abil_mkv.generate().replace('(', '').replace(')', '')
    if len(move.split(' ')) == 1:
        return ' '.join([random.choice(advs), move])
    return move



def nationality():
    nation = nation_mkv.generate()
    if nation[-1] == 'a':
        return nation + 'n'
    if nation[-1] == 'i':
        return nation + random.choice(['', 'c', 'sh', 'an'])
    if nation[-1] == 'e':
        return nation + random.choice(['se', 'an'])
    if nation[-1] == 'y':
        return nation[:-1] + 'ian'
    if nation[-1] == 'u':
        return nation + 'vian'
    else:
        return nation + random.choice(['ian', 'ean', 'ese', 'an', 'ish', 'ic', 'i'])


nationalities = [nationality() for n in range(16)]
