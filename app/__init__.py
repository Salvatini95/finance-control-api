from flask import Flask
from flask_cors import CORS
from app.extensions import db, jwt, migrate
from app.routes.auth_routes import auth_bp
from app.routes.transaction_routes import transaction_bp
from app.routes.bill_routes import bill_bp
from app.routes.product_routes import product_bp
from app.routes.quote_routes import quote_bp


def create_app():
    app = Flask(__name__)

    # 🔐 SEGURANÇA
    app.config["SECRET_KEY"]                     = "finance_secret_key_super_segura_123456"
    app.config["JWT_SECRET_KEY"]                 = "jwt_super_secret_finance_1234567890_secure"
    app.config["SQLALCHEMY_DATABASE_URI"]        = "sqlite:///database.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Aumenta limite para aceitar logo em base64 (~4 MB)
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

    # 🔥 CORS LIBERADO
    CORS(app, supports_credentials=True)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)  # ← Flask-Migrate inicializado

    # 🔗 ROTAS
    app.register_blueprint(auth_bp,        url_prefix="/api")
    app.register_blueprint(transaction_bp, url_prefix="/api")
    app.register_blueprint(bill_bp,        url_prefix="/api")
    app.register_blueprint(product_bp,     url_prefix="/api")
    app.register_blueprint(quote_bp,       url_prefix="/api")

    # ⚠️ db.create_all() removido — agora gerenciado pelo Flask-Migrate

    return app