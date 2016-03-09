import random
import numpy as np
from hashlib import md5
from saltbeef import db, generate


def gen_id(name):
    return md5(name.encode('utf8')).hexdigest()


class Creature(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    hp = db.Column(db.Integer)
    atk = db.Column(db.Integer)
    dfn = db.Column(db.Integer)
    current_hp = db.Column(db.Integer)
    trainer_id = db.Column(db.String, db.ForeignKey('trainer.id'))
    active = db.Column(db.Boolean, default=False)

    def __init__(self, name=None):
        if name is None:
            self.name = generate.name()
        else:
            self.name = name
        self.id = gen_id(self.name)
        self.hp = np.random.binomial(40, 0.4)
        self.atk = np.random.binomial(20, 0.4)
        self.dfn = np.random.binomial(10, 0.4)
        self.current_hp = self.hp

    def __repr__(self):
        return '{} ({}ATK {}DFN {}/{}HP)'.format(
            self.name,
            self.atk,
            self.dfn,
            self.current_hp,
            self.hp
        )

    def attack(self):
        critical = False
        name = generate.move().title()
        atk = np.random.binomial(self.atk + self.atk_bonus, 0.8)
        if random.random() > 0.98:
            critical = True
            atk *= 1.5
        return name, atk, critical

    def defend(self, attack):
        defense = np.random.binomial(self.dfn + self.dfn_bonus, 0.8)/10
        damage = max(0, int(attack * (1 - defense)))
        self.current_hp -= damage
        return damage

    def use_item(self, item):
        if item.effect_type == 'hp':
            self.current_hp = max(self.hp, self.current_hp + item.effect_str)
        elif item.effect_type == 'atk':
            self.atk_bonus += item.effect_str
        elif item.effect_type == 'dfn':
            self.dfn_bonus += item.effect_str


class Item(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    effect_type = db.Column(db.String)
    effect_str = db.Column(db.Integer)
    trainer_id = db.Column(db.String, db.ForeignKey('trainer.id'))
    active = db.Column(db.Boolean, default=False)

    def __init__(self):
        self.name = generate.item()
        self.id = gen_id(self.name)
        self.effect_type = random.choice(['hp', 'atk', 'dfn'])
        self.effect_str = np.random.binomial(30, 0.3)

    def __repr__(self):
        if self.effect_type == 'hp':
            return '{} (heals {}HP)'.format(
                self.name,
                self.effect_str
            )
        else:
            return '{} (+{} to {})'.format(self.name, self.effect_str, self.effect_type.upper())


class Trainer(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    wins = db.Column(db.Integer)
    losses = db.Column(db.Integer)
    creatures = db.relationship(Creature, backref='trainer', lazy='dynamic')
    items = db.relationship(Item, backref='trainer')
    active_items = db.relationship(Item, backref='trainer_active')

    def __init__(self, name):
        self.name = name
        self.wins = 0
        self.losses = 0
        self.id = gen_id(self.name)
        self.creatures = [Creature()]

    @classmethod
    def get_or_create(cls, name):
        if name[0] == '@':
            name = name[1:]

        id = gen_id(name)
        trainer = cls.query.get(id)
        if trainer is None:
            trainer = Trainer(name)
        return trainer

    def equip(self, item):
        if item not in self.items:
            return False

        item.active = True
        return True

    @property
    def active_items(self):
        return [i for i in self.items if i.active]

    def choose(self, creature):
        if creature not in self.creatures:
            return False

        for c in self.creatures.filter(Creature.active==True):
            c.active = False

        creature.active = True
        return True

    @property
    def active_creature(self):
        c = self.creatures.filter(Creature.active==True).first()
        if c is not None:
            return c

        # Create a new creature if necessary
        if not self.creatures:
            self.creatures.append(Creature())

        # Default to the first creature
        return self.creatures[0]
