import os
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from app.extensions import db, jwt, migrate
from app.routes.auth_routes import auth_bp
from app.routes.transaction_routes import transaction_bp
from app.routes.bill_routes import bill_bp
from app.routes.product_routes import product_bp
from app.routes.quote_routes import quote_bp
from app.routes.client_routes import client_bp
from app.routes.order_routes import order_bp
from app.routes.stock_routes import stock_bp
from app.routes.company_routes import company_bp
from app.routes.goal_routes import goal_bp
from app.routes.import_export_routes import import_export_bp
from app.routes.import_routes import import_bp
from app.routes.dre_routes import dre_bp
from app.routes.cashflow_routes import cashflow_bp
from app.routes.bills_report_routes import bills_report_bp
from app.routes.sales_report_routes import sales_report_bp
from app.routes.stock_report_routes import stock_report_bp
from app.routes.product_report_routes import product_report_bp
from app.routes.dev_routes import dev_bp

load_dotenv()

def create_app():
    app = Flask(__name__)

    print("🔥 APP INICIALIZADO")

    app.config["SECRET_KEY"]                     = os.environ.get("SECRET_KEY")
    app.config["JWT_SECRET_KEY"]                 = os.environ.get("JWT_SECRET_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"]        = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"]             = 4 * 1024 * 1024
    app.config["JWT_ACCESS_TOKEN_EXPIRES"]       = timedelta(hours=8)

    CORS(
        app,
        origins=[
            "http://localhost:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5173",
            "https://finance-control-web-five.vercel.app",
            "https://*.vercel.app",
            "https://svfinance.com.br",
            "https://www.svfinance.com.br",
        ],
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(auth_bp,           url_prefix="/api")
    app.register_blueprint(transaction_bp,    url_prefix="/api")
    app.register_blueprint(bill_bp,           url_prefix="/api")
    app.register_blueprint(product_bp,        url_prefix="/api")
    app.register_blueprint(quote_bp,          url_prefix="/api")
    app.register_blueprint(client_bp,         url_prefix="/api")
    app.register_blueprint(order_bp,          url_prefix="/api")
    app.register_blueprint(stock_bp,          url_prefix="/api")
    app.register_blueprint(company_bp,        url_prefix="/api")
    app.register_blueprint(goal_bp,           url_prefix="/api")
    app.register_blueprint(import_export_bp,  url_prefix="/api/import-export")
    app.register_blueprint(import_bp,         url_prefix="/api/import-export")
    app.register_blueprint(dre_bp,            url_prefix="/api")
    app.register_blueprint(cashflow_bp,        url_prefix="/api")
    app.register_blueprint(bills_report_bp,    url_prefix="/api")
    app.register_blueprint(sales_report_bp,    url_prefix="/api")
    app.register_blueprint(stock_report_bp,    url_prefix="/api")
    app.register_blueprint(product_report_bp,  url_prefix="/api")
    app.register_blueprint(dev_bp)

    return app