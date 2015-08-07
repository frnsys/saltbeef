from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///saltbeef.db'
db = SQLAlchemy(app)

from saltbeef import routes
