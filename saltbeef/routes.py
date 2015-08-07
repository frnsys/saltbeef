import requests
from flask import jsonify, request
from saltbeef import app, db, models
from config import SLACK_WEBHOOK_URL


@app.route('/')
def index():
    return jsonify(results={
        'message': 'saltbeef'
    })


@app.route('/creatures/<trainer>')
def creatures(trainer):
    """
    List creatures for a trainer.
    """
    tid = models.gen_id(trainer)
    trainer = models.Trainer.query.get(tid)
    creatures = [str(c) for c in trainer.creatures]
    return jsonify(results=creatures)


@app.route('/items/<trainer>')
def items(trainer):
    """
    List items for a trainer.
    """
    tid = models.gen_id(trainer)
    trainer = models.Trainer.query.get(tid)
    items = [str(i) for i in trainer.items]

    return jsonify(results=items)


@app.route('/battle', methods=['POST'])
def battle():
    """
    Battle two creatures against each other.
    """
    attacker = request.form['attacker']
    defender = request.form['defender']
    aid = models.gen_id(attacker)
    did = models.gen_id(defender)

    attacker = models.Creature.query.get(aid)
    defender = models.Creature.query.get(did)

    move, attack = attacker.attack()
    atk_msg = '{} attacked with {}!'.format(attacker.name, move)

    damage = defender.defend(attack)
    dfn_msg = '{} was hit for {} damage!'.format(defender.name, damage)

    messages = [atk_msg, dfn_msg]

    if defender.current_hp <= 0:
        item = models.Item()
        messages.append('{} was killed!'.format(defender.name))
        messages.append('It dropped a {} for {}!'.format(item, attacker.trainer.name))
        attacker.trainer.items.append(item)

    db.session.commit()

    return jsonify(results=messages)


@app.route('/register', methods=['POST'])
def register():
    """
    Register a new user
    """
    name = request.form['user_name']
    user = models.Trainer(name)
    db.session.add(user)
    db.session.commit()

    return jsonify(results={
        'message': 'Welcome {} ~ your starting creature is {}'.format(name,
                                                                      user.creatures[0])
    })



@app.route('/random_battle', methods=['POST'])
def random_battle():
    """
    Random battle between two users (for testing)
    """
    atk_user = models.Trainer(request.form['user_name'])
    dfn_user = models.Trainer(request.form['text'])
    attacker = atk_user.creatures[0]
    defender = dfn_user.creatures[0]

    messages = []
    while attacker.current_hp > 0 and defender.current_hp > 0:
        move, attack = attacker.attack()
        atk_msg = '*{}* attacked with *{}*!'.format(attacker.name, move)

        damage = defender.defend(attack)
        dfn_msg = '*{}* was hit for _{} damage_!'.format(defender.name, damage)

        messages += [atk_msg, dfn_msg]
        attacker, defender = defender, attacker

    if attacker.current_hp < 0:
        loser, winner = attacker, defender
    else:
        loser, winner = defender, attacker

    item = models.Item()
    messages.append('*{}* was _killed_!'.format(loser.name))
    messages.append('It dropped a *{}* for *{}*!'.format(item, winner.trainer.name))
    messages.append('*{}* is the _WINNER_!'.format(winner.trainer.name))
    #winner.trainer.items.append(item)
    #db.session.commit()

    requests.post(SLACK_WEBHOOK_URL, params={
        'text': '\n'.join(messages)
    })

    return jsonify(results=messages)
