from flask import Flask
from flask_cors import CORS

from app.extensions import db, jwt

from app.routes.auth_routes import auth_bp
from app.routes.transaction_routes import transaction_bp


def create_app():

    app = Flask(__name__)

    # 🔐 SEGURANÇA (corrigido)
    app.config["SECRET_KEY"] = "finance_secret_key_super_segura_123456"

    # 🔥 MUITO IMPORTANTE → mínimo 32 caracteres
    app.config["JWT_SECRET_KEY"] = "jwt_super_secret_finance_1234567890_secure"

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # 🔥 CORS LIBERADO (importante pro React)
    CORS(app, supports_credentials=True)

    db.init_app(app)
    jwt.init_app(app)

    # 🔗 ROTAS
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(transaction_bp, url_prefix="/api")

    # 📦 CRIA BANCO
    with app.app_context():
        db.create_all()

    return app