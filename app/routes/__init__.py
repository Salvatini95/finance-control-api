from .auth_routes import auth_bp
from .transaction_routes import transaction_bp
from .bill_routes import bill_bp
from .product_routes import product_bp
from .quote_routes import quote_bp
from .client_routes import client_bp
from .order_routes import order_bp
from .stock_routes import stock_bp
from .company_routes import company_bp


def register_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(transaction_bp)
    app.register_blueprint(bill_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(quote_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(company_bp)