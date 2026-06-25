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
from app.routes.commission_routes import commission_bp
from app.routes.nfe_routes import nfe_bp
from app.routes.brand_routes import brand_bp
from app.routes.checkin_routes import checkin_bp
from app.routes.limpeza_routes import limpeza_bp
from app.routes.nfse_routes import nfse_bp   # ← NFS-e via Focus NF-e
from app.routes.billing_routes import billing_bp
from costwise.routes import costwise_bp

load_dotenv()

def create_app():
    app = Flask(__name__)
    print("🔥 APP INICIALIZADO")

    app.config["SECRET_KEY"]                     = os.environ.get("SECRET_KEY")
    app.config["JWT_SECRET_KEY"]                 = os.environ.get("JWT_SECRET_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"]        = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"]             = 16 * 1024 * 1024  # 16MB
    app.config["JWT_ACCESS_TOKEN_EXPIRES"]       = timedelta(hours=8)

    CORS(
        app,
        origins="*",
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
    app.register_blueprint(import_bp,         url_prefix="/api")
    app.register_blueprint(dre_bp,            url_prefix="/api")
    app.register_blueprint(cashflow_bp,       url_prefix="/api")
    app.register_blueprint(bills_report_bp,   url_prefix="/api")
    app.register_blueprint(sales_report_bp,   url_prefix="/api")
    app.register_blueprint(stock_report_bp,   url_prefix="/api")
    app.register_blueprint(product_report_bp, url_prefix="/api")
    app.register_blueprint(dev_bp)
    app.register_blueprint(commission_bp,     url_prefix="/api")
    app.register_blueprint(nfe_bp,            url_prefix="/api")
    app.register_blueprint(brand_bp,          url_prefix="/api")
    app.register_blueprint(checkin_bp,        url_prefix="/api")
    app.register_blueprint(limpeza_bp)
    app.register_blueprint(nfse_bp)           # url_prefix já definido na rota (/api/nfse)
    app.register_blueprint(billing_bp)
    app.register_blueprint(costwise_bp)   # produto costwise — /costwise/*

    return app