from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

# =========================
# TABELA DE USUÁRIOS
# =========================
class User(db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(120), nullable=True)  # ← campo novo

    # logo da empresa — armazenada em base64 (texto)
    company_name  = db.Column(db.String(200), nullable=True)
    company_cnpj  = db.Column(db.String(30),  nullable=True)
    company_address = db.Column(db.String(300), nullable=True)
    company_logo  = db.Column(db.Text, nullable=True)   # base64

    transactions  = db.relationship("Transaction", backref="user", lazy=True)
    bills         = db.relationship("Bill",        backref="user", lazy=True)
    products      = db.relationship("Product",     backref="user", lazy=True)
    quotes        = db.relationship("Quote",       backref="user", lazy=True)

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)


# =========================
# TABELA DE TRANSAÇÕES
# =========================
class Transaction(db.Model):
    __tablename__ = "transactions"
    id          = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount      = db.Column(db.Float,       nullable=False)
    type        = db.Column(db.String(10),  nullable=False)   # "income" | "expense"
    category    = db.Column(db.String(100), nullable=True)
    date        = db.Column(db.String(20),  nullable=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


# =========================
# TABELA DE CONTAS
# =========================
class Bill(db.Model):
    __tablename__ = "bills"
    id          = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount      = db.Column(db.Float,       nullable=False)
    type        = db.Column(db.String(10),  nullable=False)    # "payable" | "receivable"
    status      = db.Column(db.String(10),  nullable=False, default="pending")
    due_date    = db.Column(db.String(20),  nullable=False)
    paid_date   = db.Column(db.String(20),  nullable=True)
    category    = db.Column(db.String(100), nullable=True)
    notes       = db.Column(db.String(500), nullable=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


# =========================
# TABELA DE PRODUTOS/SERVIÇOS
# =========================
class Product(db.Model):
    __tablename__ = "products"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    type        = db.Column(db.String(20),  nullable=False, default="service")  # "product" | "service"
    unit        = db.Column(db.String(50),  nullable=True)   # "un", "hr", "kg", "m²" …
    cost        = db.Column(db.Float,       nullable=False, default=0.0)   # custo
    price       = db.Column(db.Float,       nullable=False, default=0.0)   # preço de venda
    category    = db.Column(db.String(100), nullable=True)
    active      = db.Column(db.Boolean,     nullable=False, default=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    @property
    def profit(self):
        return self.price - self.cost

    @property
    def margin(self):
        if self.price == 0:
            return 0.0
        return round((self.profit / self.price) * 100, 2)


# =========================
# TABELA DE ORÇAMENTOS
# =========================
class Quote(db.Model):
    __tablename__ = "quotes"
    id              = db.Column(db.Integer, primary_key=True)
    number          = db.Column(db.String(30),  nullable=False)   # ex: "ORC-2024-001"
    client_name     = db.Column(db.String(200), nullable=False)
    client_email    = db.Column(db.String(200), nullable=True)
    client_phone    = db.Column(db.String(50),  nullable=True)
    client_document = db.Column(db.String(50),  nullable=True)    # CPF/CNPJ
    client_address  = db.Column(db.String(300), nullable=True)
    status          = db.Column(db.String(20),  nullable=False, default="draft")
    # "draft" | "sent" | "approved" | "rejected" | "cancelled"
    valid_until     = db.Column(db.String(20),  nullable=True)
    payment_terms   = db.Column(db.String(300), nullable=True)
    notes           = db.Column(db.Text,        nullable=True)
    discount        = db.Column(db.Float,       nullable=False, default=0.0)  # % desconto global
    # itens armazenados como JSON string
    items_json      = db.Column(db.Text,        nullable=False, default="[]")
    # totais calculados e salvos para facilitar listagem
    subtotal        = db.Column(db.Float,       nullable=False, default=0.0)
    total           = db.Column(db.Float,       nullable=False, default=0.0)
    created_at      = db.Column(db.String(20),  nullable=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)