import json
import requests
from flask import jsonify, request
from saltbeef import app, db, models
from config import SLACK_WEBHOOK_URL


@app.route('/')
def index():
    return jsonify(results={
        'message': 'saltbeef'
    })


@app.route('/creatures', methods=['POST'])
def creatures():
    """
    List creatures for a trainer.
    """
    name = request.form['user_name']
    trainer = models.Trainer.get_or_create(name)
    creatures = [str(c) for c in trainer.creatures]

    if not creatures:
        messages = [
            'You have no creatures.'
        ]
    else:
        messages = [
            'You have these creatures:',
            '\n'.join(['[{}] {}'.format(i, creature) for i, creature in enumerate(creatures)]),
            'To choose a creature, say `/ichoose <creature number>`'
        ]

    return '\n'.join(messages)


@app.route('/items', methods=['POST'])
def items():
    """
    List items for a trainer.
    """
    name = request.form['user_name']
    trainer = models.Trainer.get_or_create(name)

    if not trainer.items:
        messages = [
            'You have no items.'
        ]
    else:
        messages = [
            'You have these items:',
            '\n'.join(['[{}] {} {}'.format(i, item, '(equipped)' if item.active else '')
                       for i, item in enumerate(trainer.items)]),
            'To equip an item, say `/equip <item number>`'
        ]

    return '\n'.join(messages)


@app.route('/equip', methods=['POST'])
def equip():
    """
    Equip an item (one-time use)
    """
    name = request.form['user_name']
    trainer = models.Trainer.get_or_create(name)

    try:
        i = int(request.form['text'])
    except ValueError:
        return 'That\'s not a number!'
    except KeyError:
        return 'Tell me the number of the item you want to equip!'

    try:
        item = trainer.items[i]
    except IndexError:
        return 'You don\'t have that many items!'

    trainer.equip(item)
    db.session.commit()

    return 'You equipped {}'.format(item)


@app.route('/choose', methods=['POST'])
def choose():
    """
    Choose a creature.
    """
    name = request.form['user_name']
    trainer = models.Trainer.get_or_create(name)

    try:
        i = int(request.form['text'])
    except ValueError:
        return 'That\'s not a number!'
    except KeyError:
        return 'Tell me the number of the creature you want to use!'

    try:
        creature = trainer.creatures[i]
    except IndexError:
        return 'You don\'t have that many creatures!'

    trainer.choose(creature)
    db.session.commit()

    return 'You chose {}'.format(creature)


@app.route('/random_battle', methods=['POST'])
def random_battle():
    """
    Random battle between two users (for testing)
    """
    atk_user = models.Trainer.get_or_create(request.form['user_name'])
    dfn_user = models.Trainer.get_or_create(request.form['text'])

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
    requests.post(SLACK_WEBHOOK_URL, data=json.dumps({'text':'\n'.join(messages)}))

    return ''
