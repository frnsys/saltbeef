import json
import requests
from flask import request
from saltbeef import app, db, models
from config import SLACK_WEBHOOK_URL


valid_cmds = {
    'battle': [str],
    'items': [],
    'equip': [int],
    'creatures': [],
    'ichoose': [int],
    'help': [],
    'capture': [],
    'leaderboard': [],
    'spawn': [str]
}

def parse_slack_cmd(input):
    """
    Parse and validate commands from the `text` key
    that Slack provides.
    """
    parts = input.split(' ')

    cmd = parts[0]
    raw_args = parts[1:]
    if cmd not in valid_cmds:
        raise Exception('Invalid command')

    # Validate number of arguments
    valid_args = valid_cmds[cmd]
    if len(raw_args) != len(valid_args):
        raise Exception('{} accepts {} arguments, not {}.'.format(cmd, len(valid_args), len(raw_args)))

    # Validate argument types
    args = []
    for arg, arg_type in zip(raw_args, valid_args):
        try:
            args.append(arg_type(arg))
        except ValueError:
            raise Exception('{} is not a {}!'.format(arg, arg_type))

    return cmd, args


@app.route('/', methods=['POST'])
def index():
    name = request.form['user_name']
    try:
        cmd, args = parse_slack_cmd(request.form['text'])
    except Exception as e:
        return str(e)

    trainer = models.Trainer.get_or_create(name)

    db.session.add(trainer)
    db.session.commit()

    if cmd == 'creatures':
        return creatures(trainer, *args)
    elif cmd == 'items':
        return items(trainer, *args)
    elif cmd == 'equip':
        return equip(trainer, *args)
    elif cmd == 'ichoose':
        return choose(trainer, *args)
    elif cmd == 'battle':
        return battle(trainer, *args)
    elif cmd == 'capture':
        return capture(trainer, *args)
    elif cmd == 'leaderboard':
        return leaderboard(trainer)
    elif cmd == 'spawn':
        return spawn(trainer, *args)
    elif cmd == 'help':
        return '\n'.join([
            'The following commands are available:',
            '- `battle <username>` - fight a user',
            '- `items` - list your items',
            '- `equip <item #>` equip an item for the next battle (one-time use)',
            '- `creatures` - list your creatures',
            '- `ichoose <creature #>` - choose a creature for your next battle',
            '- `capture` - catch a new creature',
            '- `leaderboard` - view the best trainers',
        ])

    return ''


def creatures(trainer):
    """
    List creatures for a trainer.
    """
    creatures = trainer.creatures

    if not creatures:
        messages = [
            'You have no creatures.'
        ]
    else:
        messages = [
            'You have these creatures:',
            '\n'.join(['[{}] {} {}'.format(
                i,
                creature,
                '(Active)' if creature.active else '')
                for i, creature in enumerate(creatures)]),
            'To choose a creature, say `/pokemon ichoose <creature #>`'
        ]

    return '\n'.join(messages)


def capture(trainer):
    """
    'Capture' a new creature.
    """
    creature = models.Creature()
    trainer.creatures.append(creature)
    db.session.add(trainer)
    db.session.commit()
    return 'You captured a {}!'.format(creature)


def spawn(trainer, name):
    """
    'Spawn' a new creature.
    """
    creature = models.Creature(name=name)
    trainer.creatures.append(creature)
    db.session.add(trainer)
    db.session.commit()
    return 'You captured a {}!'.format(creature)


def items(trainer):
    """
    List items for a trainer.
    """
    if not trainer.items:
        messages = [
            'You have no items.'
        ]
    else:
        messages = [
            'You have these items:',
            '\n'.join(['[{}] {} {}'.format(i, item, '(equipped)' if item.active else '')
                       for i, item in enumerate(trainer.items)]),
            'To equip an item, say `/pokemon equip <item #>`'
        ]

    return '\n'.join(messages)


def equip(trainer, item_id):
    """
    Equip an item (one-time use)
    """
    try:
        item = trainer.items[item_id]
    except IndexError:
        return 'You don\'t have that many items!'

    trainer.equip(item)
    db.session.commit()

    return 'You equipped {}'.format(item)


def leaderboard(trainer):
    leaders = models.Trainer.query.order_by(models.Trainer.wins.desc()).limit(10).all()

    messages = [
        '*LEADERBOARD*',
    ] + ['{} ~ {}W {}L'.format(t.name, t.wins, t.losses) for t in leaders]

    # Send to slack incoming webhook
    requests.post(SLACK_WEBHOOK_URL, data=json.dumps({
        'text': '\n'.join(messages),
        'attachments': [{
            'title': 'TOP TRAINER',
            'fallback': leaders[0].name,
            'text': '{} is the best trainer!'.format(leaders[0].name),
            'color': '#22D683'
        }]
    }))
    return ''


def choose(trainer, creature_id):
    """
    Choose a creature.
    """
    try:
        creature = trainer.creatures[creature_id]
    except IndexError:
        return 'You don\'t have that many creatures!'

    trainer.choose(creature)
    db.session.add(trainer)
    db.session.commit()

    return 'You chose {}'.format(creature)


def battle(atk_user, target_user):
    """
    Battle between two users
    """
    if target_user[0] == '@':
        target_user = target_user[1:]

    if target_user == atk_user.name:
        target_user = 'EVIL-{}'.format(target_user)

    dfn_user = models.Trainer.get_or_create(target_user)
    db.session.add(dfn_user)

    messages = ['*{}* IS ATTACKING *{}*!!'.format(atk_user.name, dfn_user.name)]

    # Use existing creature if available,
    # otherwise create a new one
    attacker = atk_user.active_creature
    defender = dfn_user.active_creature

    messages.append('*{}* sent out *{}*!'.format(atk_user.name, attacker))
    messages.append('*{}* sent out *{}*!'.format(dfn_user.name, defender))

    # Apply items
    attacker.atk_bonus = 0
    attacker.dfn_bonus = 0
    defender.atk_bonus = 0
    defender.dfn_bonus = 0
    for i in atk_user.active_items:
        attacker.use_item(i)
        messages.append('*{}* used *{}*!'.format(atk_user.name, i))
    for i in dfn_user.active_items:
        defender.use_item(i)
        messages.append('*{}* used *{}*!'.format(dfn_user.name, i))

    while attacker.current_hp > 0 and defender.current_hp > 0:
        move, attack, crit = attacker.attack()

        if not crit:
            atk_msg = '*{}* used *{}*!'.format(attacker.name, move)
        else:
            atk_msg = '*{}* landed a *CRITICAL HIT* with *{}*!'.format(attacker.name, move)

        damage = defender.defend(attack)
        dfn_msg = '> {} was hit for _{} damage_!'.format(defender.name, damage)

        messages += [atk_msg, dfn_msg]
        attacker, defender = defender, attacker

    if attacker.current_hp <= 0:
        loser, winner = attacker, defender
    else:
        loser, winner = defender, attacker

    messages.append('*{}* was _killed_!'.format(loser.name))

    item = models.Item()
    messages.append('It dropped a *{}* for *{}*!'.format(item, winner.trainer.name))
    messages.append('*{}* is the _WINNER_!'.format(winner.trainer.name))

    winner.trainer.wins += 1
    loser.trainer.losses += 1
    messages.append('{} has a {}W{}L record.'.format(winner.trainer.name, winner.trainer.wins, winner.trainer.losses))
    messages.append('{} has a {}W{}L record.'.format(loser.trainer.name, loser.trainer.wins, loser.trainer.losses))

    # Send to slack incoming webhook
    requests.post(SLACK_WEBHOOK_URL, data=json.dumps({
        'text': '\n'.join(messages),
        'attachments': [{
            'title': 'WINNER - {}'.format(winner.trainer.name),
            'fallback': winner.name,
            'text': '{} ({})'.format(winner.name, winner.trainer.name),
            'color': '#22D683'
        }, {
            'title': 'LOSER - {}'.format(loser.trainer.name),
            'fallback': loser.name,
            'text': '{} ({})'.format(loser.name, loser.trainer.name),
            'color': '#D73F33'
        }]
    }))

    loser.trainer.creatures.append(models.Creature())
    loser.trainer.creatures.remove(loser)
    winner.trainer.items.append(item)

    for i in atk_user.active_items:
        atk_user.items.remove(i)
    for i in dfn_user.active_items:
        dfn_user.items.remove(i)
    attacker.atk_bonus = 0
    attacker.dfn_bonus = 0
    defender.atk_bonus = 0
    defender.dfn_bonus = 0

    db.session.add(atk_user)
    db.session.add(dfn_user)
    db.session.commit()

    return ''
