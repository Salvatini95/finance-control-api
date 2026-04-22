from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date


class Company(db.Model):
    __tablename__ = "companies"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(200), nullable=False)
    cnpj       = db.Column(db.String(30),  nullable=True)
    address    = db.Column(db.String(300), nullable=True)
    logo       = db.Column(db.Text,        nullable=True)
    plan       = db.Column(db.String(20),  nullable=False, default="free")
    created_at = db.Column(db.String(20),  nullable=True)
    active     = db.Column(db.Boolean,     nullable=False, default=True)

    users           = db.relationship("User",          backref="company", lazy=True)
    transactions    = db.relationship("Transaction",   backref="company", lazy=True)
    bills           = db.relationship("Bill",          backref="company", lazy=True)
    products        = db.relationship("Product",       backref="company", lazy=True)
    quotes          = db.relationship("Quote",         backref="company", lazy=True)
    clients         = db.relationship("Client",        backref="company", lazy=True)
    orders          = db.relationship("Order",         backref="company", lazy=True)
    stock_movements = db.relationship("StockMovement", backref="company", lazy=True)
    service_records = db.relationship("ServiceRecord", backref="company", lazy=True)


class User(db.Model):
    __tablename__ = "users"

    id           = db.Column(db.Integer,     primary_key=True)
    email        = db.Column(db.String(120), unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)
    name         = db.Column(db.String(120), nullable=True)
    active       = db.Column(db.Boolean,     nullable=False, default=True)
    role         = db.Column(db.String(20),  nullable=False, default="admin")
    account_type = db.Column(db.String(20),  nullable=False, default="business")

    email_verified           = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(200), nullable=True)
    reset_password_token     = db.Column(db.String(200), nullable=True)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_user_company"), nullable=True)

    company_name    = db.Column(db.String(200), nullable=True)
    company_cnpj    = db.Column(db.String(30),  nullable=True)
    company_address = db.Column(db.String(300), nullable=True)
    company_logo    = db.Column(db.Text,        nullable=True)

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)

    @property
    def is_admin(self):   return self.role == "admin"
    @property
    def can_sell(self):   return self.role in ["admin", "seller"]
    @property
    def can_finance(self):return self.role in ["admin", "financial"]
    @property
    def can_stock(self):  return self.role in ["admin", "stock"]


class Transaction(db.Model):
    __tablename__ = "transactions"

    id          = db.Column(db.Integer,     primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount      = db.Column(db.Float,       nullable=False)
    type        = db.Column(db.String(10),  nullable=False)
    category    = db.Column(db.String(100), nullable=True)
    date        = db.Column(db.String(20),  nullable=True)
    source      = db.Column(db.String(20),  nullable=False, default="manual")

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_transaction_company"), nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",     name="fk_transaction_user"),    nullable=False)


class Bill(db.Model):
    __tablename__ = "bills"

    id          = db.Column(db.Integer,     primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount      = db.Column(db.Float,       nullable=False)
    type        = db.Column(db.String(10),  nullable=False)
    status      = db.Column(db.String(10),  nullable=False, default="pending")
    due_date    = db.Column(db.String(20),  nullable=False)
    paid_date   = db.Column(db.String(20),  nullable=True)
    category    = db.Column(db.String(100), nullable=True)
    notes       = db.Column(db.String(500), nullable=True)

    company_id     = db.Column(db.Integer, db.ForeignKey("companies.id",    name="fk_bill_company"),     nullable=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id",        name="fk_bill_user"),        nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id", name="fk_bill_transaction"), nullable=True)


class Product(db.Model):
    __tablename__ = "products"

    id             = db.Column(db.Integer,     primary_key=True)
    name           = db.Column(db.String(200), nullable=False)
    sku            = db.Column(db.String(100), nullable=True)
    description    = db.Column(db.String(500), nullable=True)
    type           = db.Column(db.String(20),  nullable=False, default="service")
    unit           = db.Column(db.String(50),  nullable=True)
    cost           = db.Column(db.Float,       nullable=False, default=0.0)
    price          = db.Column(db.Float,       nullable=False, default=0.0)
    category       = db.Column(db.String(100), nullable=True)
    active         = db.Column(db.Boolean,     nullable=False, default=True)
    stock_qty      = db.Column(db.Float,       nullable=False, default=0.0)
    stock_min      = db.Column(db.Float,       nullable=False, default=0.0)
    stock_avg_cost = db.Column(db.Float,       nullable=False, default=0.0)
    services_count = db.Column(db.Integer,     nullable=False, default=0)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_product_company"), nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",     name="fk_product_user"),    nullable=False)

    stock_movements = db.relationship("StockMovement", backref="product", lazy=True)
    service_records = db.relationship("ServiceRecord", backref="product", lazy=True)

    @property
    def profit(self): return self.price - self.cost
    @property
    def margin(self):
        return 0.0 if self.price == 0 else round((self.profit / self.price) * 100, 2)
    @property
    def stock_alert(self): return self.type == "product" and self.stock_qty <= self.stock_min


class Quote(db.Model):
    __tablename__ = "quotes"

    id              = db.Column(db.Integer,     primary_key=True)
    number          = db.Column(db.String(30),  nullable=False)
    client_name     = db.Column(db.String(200), nullable=False)
    client_email    = db.Column(db.String(200), nullable=True)
    client_phone    = db.Column(db.String(50),  nullable=True)
    client_document = db.Column(db.String(50),  nullable=True)
    client_address  = db.Column(db.String(300), nullable=True)
    status          = db.Column(db.String(20),  nullable=False, default="draft")
    valid_until     = db.Column(db.String(20),  nullable=True)
    payment_terms   = db.Column(db.String(300), nullable=True)
    notes           = db.Column(db.Text,        nullable=True)
    discount        = db.Column(db.Float,       nullable=False, default=0.0)
    items_json      = db.Column(db.Text,        nullable=False, default="[]")
    subtotal        = db.Column(db.Float,       nullable=False, default=0.0)
    total           = db.Column(db.Float,       nullable=False, default=0.0)
    created_at      = db.Column(db.String(20),  nullable=True)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_quote_company"), nullable=True)
    client_id  = db.Column(db.Integer, db.ForeignKey("clients.id",   name="fk_quote_client"),  nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",     name="fk_quote_user"),    nullable=False)


class Client(db.Model):
    __tablename__ = "clients"

    id         = db.Column(db.Integer,     primary_key=True)
    name       = db.Column(db.String(200), nullable=False)
    email      = db.Column(db.String(200), nullable=True)
    phone      = db.Column(db.String(50),  nullable=True)
    document   = db.Column(db.String(50),  nullable=True)
    address    = db.Column(db.String(300), nullable=True)
    notes      = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.String(20),  nullable=True)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_client_company"), nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",     name="fk_client_user"),    nullable=False)

    orders          = db.relationship("Order",         backref="client", lazy=True)
    service_records = db.relationship("ServiceRecord", backref="client", lazy=True)
    quotes          = db.relationship("Quote",         backref="client", lazy=True)


class Order(db.Model):
    __tablename__ = "orders"

    id            = db.Column(db.Integer,     primary_key=True)
    number        = db.Column(db.String(30),  nullable=False)
    status        = db.Column(db.String(20),  nullable=False, default="open")
    origin        = db.Column(db.String(20),  nullable=False, default="direct")
    notes         = db.Column(db.Text,        nullable=True)
    payment_terms = db.Column(db.String(300), nullable=True)
    discount      = db.Column(db.Float,       nullable=False, default=0.0)
    items_json    = db.Column(db.Text,        nullable=False, default="[]")
    subtotal      = db.Column(db.Float,       nullable=False, default=0.0)
    total         = db.Column(db.Float,       nullable=False, default=0.0)
    created_at    = db.Column(db.String(20),  nullable=True)
    finished_at   = db.Column(db.String(20),  nullable=True)

    company_id     = db.Column(db.Integer, db.ForeignKey("companies.id",    name="fk_order_company"),     nullable=True)
    client_id      = db.Column(db.Integer, db.ForeignKey("clients.id",      name="fk_order_client"),      nullable=False)
    quote_id       = db.Column(db.Integer, db.ForeignKey("quotes.id",       name="fk_order_quote"),       nullable=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id", name="fk_order_transaction"), nullable=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id",        name="fk_order_user"),        nullable=False)


class StockMovement(db.Model):
    __tablename__ = "stock_movements"

    id         = db.Column(db.Integer,     primary_key=True)
    type       = db.Column(db.String(10),  nullable=False)
    qty        = db.Column(db.Float,       nullable=False)
    cost       = db.Column(db.Float,       nullable=True)
    reason     = db.Column(db.String(200), nullable=True)
    date       = db.Column(db.String(20),  nullable=True)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_stock_company"), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id",  name="fk_stock_product"), nullable=False)
    order_id   = db.Column(db.Integer, db.ForeignKey("orders.id",    name="fk_stock_order"),   nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",     name="fk_stock_user"),    nullable=False)


class ServiceRecord(db.Model):
    __tablename__ = "service_records"

    id           = db.Column(db.Integer,     primary_key=True)
    date         = db.Column(db.String(20),  nullable=True)
    duration_min = db.Column(db.Integer,     nullable=True)
    amount       = db.Column(db.Float,       nullable=False, default=0.0)
    notes        = db.Column(db.String(500), nullable=True)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_svcrecord_company"), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id",  name="fk_svcrecord_product"), nullable=False)
    client_id  = db.Column(db.Integer, db.ForeignKey("clients.id",   name="fk_svcrecord_client"),  nullable=True)
    order_id   = db.Column(db.Integer, db.ForeignKey("orders.id",    name="fk_svcrecord_order"),   nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",     name="fk_svcrecord_user"),    nullable=False)


class Goal(db.Model):
    __tablename__ = "goals"

    id          = db.Column(db.Integer,     primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    target      = db.Column(db.Float,       nullable=False)
    current     = db.Column(db.Float,       nullable=False, default=0.0)
    category    = db.Column(db.String(100), nullable=True)
    icon        = db.Column(db.String(10),  nullable=True, default="🎯")
    deadline    = db.Column(db.String(20),  nullable=True)
    status      = db.Column(db.String(20),  nullable=False, default="active")
    created_at  = db.Column(db.String(20),  nullable=True)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_goal_company"), nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",     name="fk_goal_user"),    nullable=False)

    @property
    def progress(self):
        return 0.0 if self.target == 0 else round(min((self.current / self.target) * 100, 100), 1)
    @property
    def remaining(self): return max(self.target - self.current, 0)


class ImportLog(db.Model):
    __tablename__ = "import_logs"

    id         = db.Column(db.Integer,     primary_key=True)
    type       = db.Column(db.String(10),  nullable=False)   # import | export
    entity     = db.Column(db.String(30),  nullable=False)   # clientes | transacoes | produtos
    sistema    = db.Column(db.String(30),  nullable=True)    # generico | conta_azul | omie | nibo | linx
    filename   = db.Column(db.String(200), nullable=True)
    total      = db.Column(db.Integer,     nullable=False, default=0)
    created    = db.Column(db.Integer,     nullable=False, default=0)
    updated    = db.Column(db.Integer,     nullable=False, default=0)
    skipped    = db.Column(db.Integer,     nullable=False, default=0)
    errors     = db.Column(db.Integer,     nullable=False, default=0)
    errors_log = db.Column(db.Text,        nullable=True)    # JSON com lista de erros
    created_at = db.Column(db.String(30),  nullable=False)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_importlog_company"), nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",     name="fk_importlog_user"),    nullable=False)