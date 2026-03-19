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

    transactions = db.relationship("Transaction", backref="user", lazy=True)

    def set_password(self, raw_password):
        """Gera o hash da senha antes de salvar."""
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        """Verifica se a senha informada bate com o hash salvo."""
        return check_password_hash(self.password, raw_password)


# =========================
# TABELA DE TRANSAÇÕES
# =========================

class Transaction(db.Model):

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)   # "income" ou "expense"
    category = db.Column(db.String(100), nullable=True)
    date = db.Column(db.String(20), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)