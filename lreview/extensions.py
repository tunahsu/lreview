from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_uploads import UploadSet, IMAGES


db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()
photos = UploadSet('photos', IMAGES)
