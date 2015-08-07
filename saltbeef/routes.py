from flask import jsonify, request
from saltbeef import app, db, models


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
    name = request.form['username']
    user = models.Trainer(name)
    db.session.add(user)
    db.session.commit()

    return jsonify(results={
        'message': 'Welcome {} ~ your starting creature is {}'.format(name,
                                                                      user.creatures[0])
    })
