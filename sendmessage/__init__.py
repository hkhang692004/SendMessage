


from flask import Flask
from urllib.parse import quote
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import cloudinary
from flask_socketio import SocketIO



app = Flask(__name__)
app.secret_key = 'HGHJAHA^&^&*AJAVAHJ*^&^&*%&*^GAFGFAG'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:%s@127.0.0.1/sendmessagedb?charset=utf8mb4" % quote('Admin@123')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

cloudinary.config(
    cloud_name='dblzpkokm',
    api_key='629135199449497',
    api_secret='YanTDoC3S-bHO-i4I9S8G2hBevs',
    secure=True

)
