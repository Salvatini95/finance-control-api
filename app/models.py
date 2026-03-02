from app import db
from werkzeug.security import generate_password_hash, check_password_hash


# =====================================
# MODEL USER
# =====================================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password = db.Column(db.String(200), nullable=False)

    # Relacionamento com transações
    transactions = db.relationship(
        "Transaction",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    # Método para criar hash da senha
    def set_password(self, password):
        self.password = generate_password_hash(password)

    # Método para verificar senha
    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"<User {self.email}>"



# =====================================
# MODEL TRANSACTION
# =====================================

class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)

    description = db.Column(db.String(200), nullable=False)

    amount = db.Column(db.Float, nullable=False)

    type = db.Column(db.String(20), nullable=False)  # income ou expense

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    # Chave estrangeira
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    def __repr__(self):
        return f"<Transaction {self.description} - {self.amount}>"