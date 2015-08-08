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
    'help': []
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
        return 'Invalid command'

    # Validate number of arguments
    valid_args = valid_cmds[cmd]
    if len(raw_args) != len(valid_args):
        return '{} accepts {} arguments, not {}.'.format(cmd, len(valid_args), len(raw_args))

    # Validate argument types
    args = []
    for arg, arg_type in zip(raw_args, valid_args):
        try:
            args.append(arg_type(arg))
        except ValueError:
            return '{} is not a {}!'.format(arg, arg_type)

    return cmd, args


@app.route('/', methods=['POST'])
def index():
    name = request.form['user_name']
    cmd, args = parse_slack_cmd(request.form['text'])
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
    elif cmd == 'help':
        return '\n'.join([
            'The following commands are available:',
            '- `battle <username>` - fight a user',
            '- `items` - list your items',
            '- `equip <item #>` equip an item for the next battle (one-time use)',
            '- `creatures` - list your creatures',
            '- `ichoose <creature #>` - choose a creature for your next battle'
        ])

    return ''


def creatures(trainer):
    """
    List creatures for a trainer.
    """
    creatures = [str(c) for c in trainer.creatures]

    if not creatures:
        messages = [
            'You have no creatures.'
        ]
    else:
        messages = [
            'You have these creatures:',
            '\n'.join(['[{}] {}'.format(i, creature) for i, creature in enumerate(creatures)]),
            'To choose a creature, say `/pokemon ichoose <creature #>`'
        ]

    return '\n'.join(messages)


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


def choose(trainer, creature_id):
    """
    Choose a creature.
    """
    try:
        creature = trainer.creatures[creature_id]
    except IndexError:
        return 'You don\'t have that many creatures!'

    trainer.choose(creature)
    db.session.commit()

    return 'You chose {}'.format(creature)


def battle(atk_user, target_user):
    """
    Battle between two users
    """
    dfn_user = models.Trainer.get_or_create(target_user)

    # Use existing creature if available,
    # otherwise create a new one
    if not atk_user.creatures:
        atk_user.creatures.append(models.Creature())
    if not dfn_user.creatures:
        dfn_user.creatures.append(models.Creature())
    attacker = atk_user.creatures[0]
    defender = dfn_user.creatures[0]

    attacker.atk_bonus = 0
    attacker.dfn_bonus = 0
    defender.atk_bonus = 0
    defender.dfn_bonus = 0
    for i in atk_user.active_items:
        attacker.use_item(i)
    for i in dfn_user.active_items:
        defender.use_item(i)

    messages = ['*{}* IS ATTACKING *{}*!!'.format(atk_user.name, dfn_user.name)]
    while attacker.current_hp > 0 and defender.current_hp > 0:
        move, attack = attacker.attack()
        atk_msg = '*{}* attacked with *{}*!'.format(attacker.name, move)

        damage = defender.defend(attack)
        dfn_msg = '*{}* was hit for _{} damage_!'.format(defender.name, damage)

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

    # Send to slack incoming webhook
    requests.post(SLACK_WEBHOOK_URL, data=json.dumps({
        'text': '\n'.join(messages),
        'attachments': [{
            'title': 'WINNER' if winner == attacker else 'LOSER',
            'fallback': attacker.name,
            'text': '{} ({})'.format(attacker.name, atk_user.name),
            'color': '#22D683' if winner == attacker else '#D73F33',
            'image_url': attacker.image
        }, {
            'title': 'WINNER' if winner == defender else 'LOSER',
            'fallback': defender.name,
            'text': '{} ({})'.format(defender.name, dfn_user.name),
            'color': '#22D683' if winner == defender else '#D73F33',
            'image_url': defender.image
        }]
    }))

    return ''
