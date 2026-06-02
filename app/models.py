from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
from sqlalchemy.dialects.postgresql import JSON as PGJSON


class Company(db.Model):
    __tablename__ = "companies"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(200), nullable=False)
    cnpj       = db.Column(db.String(30),  nullable=True)
    address    = db.Column(db.String(300), nullable=True)
    logo       = db.Column(db.Text,        nullable=True)
    plan       = db.Column(db.String(20),  nullable=False, default="free")
    nicho      = db.Column(db.String(30),  nullable=False, server_default="generic")
    created_at = db.Column(db.String(20),  nullable=True)
    active     = db.Column(db.Boolean,     nullable=False, default=True)

    inscricao_estadual  = db.Column(db.String(30),  nullable=True)
    inscricao_municipal = db.Column(db.String(30),  nullable=True)
    regime_tributario   = db.Column(db.String(2),   nullable=True, server_default="1")
    cep                 = db.Column(db.String(10),  nullable=True)
    logradouro          = db.Column(db.String(200), nullable=True)
    numero              = db.Column(db.String(20),  nullable=True)
    complemento         = db.Column(db.String(100), nullable=True)
    bairro              = db.Column(db.String(100), nullable=True)
    municipio           = db.Column(db.String(100), nullable=True)
    uf                  = db.Column(db.String(2),   nullable=True)
    codigo_municipio    = db.Column(db.String(10),  nullable=True)
    telefone            = db.Column(db.String(20),  nullable=True)
    token_focusnfe      = db.Column(db.String(100), nullable=True)

    users            = db.relationship("User",          backref="company", lazy=True)
    transactions     = db.relationship("Transaction",   backref="company", lazy=True)
    bills            = db.relationship("Bill",          backref="company", lazy=True)
    products         = db.relationship("Product",       backref="company", lazy=True)
    quotes           = db.relationship("Quote",         backref="company", lazy=True)
    clients          = db.relationship("Client",        backref="company", lazy=True)
    orders           = db.relationship("Order",         backref="company", lazy=True)
    stock_movements  = db.relationship("StockMovement", backref="company", lazy=True)
    service_records  = db.relationship("ServiceRecord", backref="company", lazy=True)
    brand_projects   = db.relationship("BrandProject",  backref="company", lazy=True)
    brand_assets     = db.relationship("BrandAsset",    backref="company", lazy=True)
    service_checkins = db.relationship("ServiceCheckin", back_populates="company_rel", lazy=True)


class User(db.Model):
    __tablename__ = "users"

    id           = db.Column(db.Integer,     primary_key=True)
    email        = db.Column(db.String(120), unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)
    name         = db.Column(db.String(120), nullable=True)
    active       = db.Column(db.Boolean,     nullable=False, default=True)
    role         = db.Column(db.String(20),  nullable=False, default="admin")
    account_type = db.Column(db.String(20),  nullable=False, default="business")

    email_verified           = db.Column(db.Boolean,     default=False)
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
    def is_admin(self):         return self.role == "admin"
    @property
    def can_sell(self):         return self.role in ["admin", "seller"]
    @property
    def can_finance(self):      return self.role in ["admin", "financial"]
    @property
    def can_stock(self):        return self.role in ["admin", "stock"]
    @property
    def can_manage_field(self): return self.role in ["admin", "encarregado"]


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

    ncm        = db.Column(db.String(10), nullable=True)
    cfop       = db.Column(db.String(10), nullable=True)
    cst_icms   = db.Column(db.String(5),  nullable=True)
    csosn      = db.Column(db.String(5),  nullable=True)
    cst_pis    = db.Column(db.String(5),  nullable=True, server_default="07")
    cst_cofins = db.Column(db.String(5),  nullable=True, server_default="07")
    origem     = db.Column(db.String(2),  nullable=True, server_default="0")

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

    inscricao_estadual = db.Column(db.String(30),  nullable=True)
    cep                = db.Column(db.String(10),  nullable=True)
    logradouro         = db.Column(db.String(200), nullable=True)
    numero             = db.Column(db.String(20),  nullable=True)
    complemento        = db.Column(db.String(100), nullable=True)
    bairro             = db.Column(db.String(100), nullable=True)
    municipio          = db.Column(db.String(100), nullable=True)
    uf                 = db.Column(db.String(2),   nullable=True)
    codigo_municipio   = db.Column(db.String(10),  nullable=True)

    codigo             = db.Column(db.String(30),  nullable=True)
    cnpj               = db.Column(db.String(30),  nullable=True)

    latitude  = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    contrato_tipo            = db.Column(db.String(20),  nullable=True, server_default="avulso")
    contrato_valor           = db.Column(db.Float(),     nullable=True)
    contrato_forma_pagamento = db.Column(db.String(30),  nullable=True)
    contrato_dia_pagamento   = db.Column(db.Integer(),   nullable=True)
    contrato_inicio          = db.Column(db.String(20),  nullable=True)
    contrato_fim             = db.Column(db.String(20),  nullable=True)
    contrato_status          = db.Column(db.String(20),  nullable=True, server_default="ativo")
    contrato_dias_semana     = db.Column(db.String(50),  nullable=True)
    contrato_observacoes     = db.Column(db.Text(),      nullable=True)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_client_company"), nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",     name="fk_client_user"),    nullable=False)

    orders          = db.relationship("Order",         backref="client", lazy=True)
    service_records = db.relationship("ServiceRecord", backref="client", lazy=True)
    quotes          = db.relationship("Quote",         backref="client", lazy=True)
    checkins        = db.relationship(
        "ServiceCheckin",
        back_populates="client_rel",
        lazy=True,
        foreign_keys="ServiceCheckin.client_id"
    )

    @property
    def endereco_completo(self):
        partes = [self.logradouro, self.numero, self.bairro, self.municipio, self.uf]
        return ", ".join([p for p in partes if p]) or (self.address or "—")


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

    nfe_chave  = db.Column(db.String(50),  nullable=True)
    nfe_status = db.Column(db.String(20),  nullable=True)
    nfe_numero = db.Column(db.String(10),  nullable=True)
    nfe_ref    = db.Column(db.String(64),  nullable=True)  # referência Focus NF-e

    company_id     = db.Column(db.Integer, db.ForeignKey("companies.id",    name="fk_order_company"),     nullable=True)
    client_id      = db.Column(db.Integer, db.ForeignKey("clients.id",      name="fk_order_client"),      nullable=False)
    quote_id       = db.Column(db.Integer, db.ForeignKey("quotes.id",       name="fk_order_quote"),       nullable=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id", name="fk_order_transaction"), nullable=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id",        name="fk_order_user"),        nullable=False)
    seller_id      = db.Column(db.Integer, db.ForeignKey("users.id",        name="fk_order_seller"),      nullable=True)


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
    type       = db.Column(db.String(10),  nullable=False)
    entity     = db.Column(db.String(30),  nullable=False)
    sistema    = db.Column(db.String(30),  nullable=True)
    filename   = db.Column(db.String(200), nullable=True)
    total      = db.Column(db.Integer,     nullable=False, default=0)
    created    = db.Column(db.Integer,     nullable=False, default=0)
    updated    = db.Column(db.Integer,     nullable=False, default=0)
    skipped    = db.Column(db.Integer,     nullable=False, default=0)
    errors     = db.Column(db.Integer,     nullable=False, default=0)
    errors_log = db.Column(db.Text,        nullable=True)
    created_at = db.Column(db.String(30),  nullable=False)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_importlog_company"), nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",     name="fk_importlog_user"),    nullable=False)


class CommissionRule(db.Model):
    __tablename__ = "commission_rules"

    id         = db.Column(db.Integer,    primary_key=True)
    seller_id  = db.Column(db.Integer,   db.ForeignKey("users.id",     name="fk_commission_seller"),  nullable=False)
    admin_id   = db.Column(db.Integer,   db.ForeignKey("users.id",     name="fk_commission_admin"),   nullable=False)
    company_id = db.Column(db.Integer,   db.ForeignKey("companies.id", name="fk_commission_company"), nullable=True)
    type       = db.Column(db.String(20), nullable=False, default="percent_total")
    value      = db.Column(db.Float,     nullable=False, default=0.0)
    active     = db.Column(db.Boolean,   nullable=False, default=True)
    created_at = db.Column(db.String(20), nullable=True)


class BrandProject(db.Model):
    __tablename__ = "brand_projects"

    id          = db.Column(db.Integer,     primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    canvas_data = db.Column(db.Text,        nullable=False, server_default="{}")
    format      = db.Column(db.String(30),  nullable=False, server_default="insta_post")
    created_at  = db.Column(db.String(20),  nullable=True)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_brandproj_company"), nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",     name="fk_brandproj_user"),    nullable=False)


class BrandAsset(db.Model):
    __tablename__ = "brand_assets"

    id         = db.Column(db.Integer,     primary_key=True)
    filename   = db.Column(db.String(200), nullable=True)
    url        = db.Column(db.Text,        nullable=False)
    created_at = db.Column(db.String(20),  nullable=True)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_brandasset_company"), nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",     name="fk_brandasset_user"),    nullable=False)


class ServiceCheckin(db.Model):
    """
    Registro de check-in e check-out de serviço via QR Code mestre.

    FLUXO:
    1. ADM cria OS para o cliente
    2. Colaborador abre a OS no celular → toca "Iniciar serviço"
    3. Câmera abre → escaneia QR Code fixo na vitrine
    4. Sistema registra checkin_at + vincula à OS
    5. OS muda para "em andamento" automaticamente
    6. Colaborador executa o serviço
    7. Toca "Finalizar serviço" → escaneia QR Code novamente
    8. Sistema registra checkout_at e calcula duration_min

    OFFLINE: local_id (UUID do celular) garante idempotência no sync em lote.
    """
    __tablename__ = "service_checkins"

    id           = db.Column(db.Integer,    primary_key=True)
    executed_at  = db.Column(db.String(30), nullable=False)
    checkin_at   = db.Column(db.String(30), nullable=True)
    checkout_at  = db.Column(db.String(30), nullable=True)
    duration_min = db.Column(db.Integer,    nullable=True)
    type         = db.Column(db.String(10), nullable=False, server_default="checkin")
    latitude     = db.Column(db.Float,      nullable=True)
    longitude    = db.Column(db.Float,      nullable=True)
    notes        = db.Column(db.Text,       nullable=True)

    local_id       = db.Column(db.String(40), nullable=True)
    synced_offline = db.Column(db.Boolean,    nullable=False, server_default="false")

    client_id  = db.Column(db.Integer, db.ForeignKey("clients.id",   name="fk_checkin_client"),  nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",     name="fk_checkin_user"),    nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", name="fk_checkin_company"), nullable=False)
    order_id   = db.Column(db.Integer, db.ForeignKey("orders.id",    name="fk_checkin_order"),   nullable=True)

    client_rel  = db.relationship(
        "Client", back_populates="checkins",
        foreign_keys=[client_id], lazy="joined"
    )
    user_rel    = db.relationship(
        "User", foreign_keys=[user_id], lazy="joined"
    )
    order_rel   = db.relationship(
        "Order", foreign_keys=[order_id], lazy="joined"
    )
    company_rel = db.relationship(
        "Company", back_populates="service_checkins",
        foreign_keys=[company_id], lazy="joined"
    )

    def to_dict(self):
        dur = self.duration_min
        if dur is not None:
            h       = dur // 60
            m       = dur % 60
            dur_str = f"{h}h{m:02d}min" if h > 0 else f"{m}min"
        else:
            dur_str = None

        client_address = self.client_rel.endereco_completo if self.client_rel else "—"

        return {
            "id":             self.id,
            "executed_at":    self.executed_at,
            "checkin_at":     self.checkin_at,
            "checkout_at":    self.checkout_at,
            "duration_min":   self.duration_min,
            "duration_str":   dur_str,
            "type":           self.type,
            "latitude":       self.latitude,
            "longitude":      self.longitude,
            "notes":          self.notes,
            "local_id":       self.local_id,
            "synced_offline": self.synced_offline,
            "client_id":      self.client_id,
            "client_name":    self.client_rel.name  if self.client_rel else "",
            "client_address": client_address,
            "user_id":        self.user_id,
            "user_name":      self.user_rel.name    if self.user_rel   else "",
            "company_id":     self.company_id,
            "order_id":       self.order_id,
            "order_number":   self.order_rel.number if self.order_rel  else "",
        }

    def __repr__(self):
        return f"ServiceCheckin(id={self.id}, client_id={self.client_id}, at='{self.checkin_at}')"


class CheckinPin(db.Model):
    """
    PIN temporário para liberar check-in de cliente SEM GPS cadastrado.

    Gerado por admin ou encarregado, 6 dígitos, validade curta (5min),
    uso único. Ao ser usado, libera o check-in E salva o GPS do
    colaborador como localização oficial do cliente.
    """
    __tablename__ = "checkin_pins"

    id         = db.Column(db.Integer,    primary_key=True)
    pin        = db.Column(db.String(6),  nullable=False)
    client_id  = db.Column(db.Integer,   db.ForeignKey("clients.id",   name="fk_pin_client"),  nullable=False)
    company_id = db.Column(db.Integer,   db.ForeignKey("companies.id", name="fk_pin_company"), nullable=False)
    created_by = db.Column(db.Integer,   db.ForeignKey("users.id",     name="fk_pin_creator"), nullable=False)
    used_by    = db.Column(db.Integer,   nullable=True)
    created_at = db.Column(db.String(20), nullable=False)
    expires_at = db.Column(db.String(20), nullable=False)
    used_at    = db.Column(db.String(20), nullable=True)
    status     = db.Column(db.String(20), nullable=False, server_default="ativo")

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "pin":        self.pin,
            "client_id":  self.client_id,
            "created_by": self.created_by,
            "used_by":    self.used_by,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "used_at":    self.used_at,
            "status":     self.status,
        }

    def __repr__(self) -> str:
        return f"CheckinPin(id={self.id}, client_id={self.client_id}, status='{self.status}')"


# ── RESTAURA GLASS — Modelos isolados (nicho limpeza, company_id=17) ─────────
# Não afetam nenhum outro nicho ou empresa do SV Finance.

class LimpezaServiceCard(db.Model):
    """
    Cartão de visita recorrente da Restaura Glass.
    Um cartão por O.S — registra frequência, dia fixo, mês/ano e execução por semana.
    """
    __tablename__ = "limpeza_service_cards"

    id           = db.Column(db.Integer,     primary_key=True)
    company_id   = db.Column(db.Integer,     nullable=False, index=True)
    order_id     = db.Column(db.Integer,     nullable=False, unique=True, index=True)
    client_id    = db.Column(db.Integer,     nullable=False, server_default="0")
    frequencia   = db.Column(db.String(20),  nullable=False, server_default="semanal")
    mes          = db.Column(db.Integer,     nullable=False, server_default="1")
    ano          = db.Column(db.Integer,     nullable=False, server_default="2024")
    dias_semana  = db.Column(db.String(3),   nullable=False, server_default="seg")
    obs_contrato = db.Column(db.String(255), nullable=True)
    semanas      = db.Column(PGJSON,         nullable=False, server_default="[]")
    created_at   = db.Column(db.DateTime,    nullable=False, server_default=db.func.now())
    updated_at   = db.Column(db.DateTime,    nullable=False, server_default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return {
            "id":           self.id,
            "company_id":   self.company_id,
            "order_id":     self.order_id,
            "client_id":    self.client_id,
            "frequencia":   self.frequencia,
            "mes":          self.mes,
            "ano":          self.ano,
            "dias_semana":  self.dias_semana,
            "obs_contrato": self.obs_contrato,
            "semanas":      self.semanas or [],
            "created_at":   self.created_at.isoformat() if self.created_at else None,
            "updated_at":   self.updated_at.isoformat() if self.updated_at else None,
        }


class LimpezaOccurrence(db.Model):
    """
    Registro das 4 ocorrências de desfecho de visita da Restaura Glass:
    fechou / remarcou / nao_compareceu / mudou_ponto
    """
    __tablename__ = "limpeza_occurrences"

    id                 = db.Column(db.Integer,    primary_key=True)
    company_id         = db.Column(db.Integer,    nullable=False, index=True)
    order_id           = db.Column(db.Integer,    nullable=False, index=True)
    user_id            = db.Column(db.Integer,    nullable=True)
    tipo               = db.Column(db.String(30), nullable=False, server_default="")
    data               = db.Column(db.String(10), nullable=False, server_default="")
    hora               = db.Column(db.String(5),  nullable=True)
    reagendamento_data = db.Column(db.String(10), nullable=True)
    reagendamento_hora = db.Column(db.String(5),  nullable=True)
    descricao          = db.Column(db.Text,       nullable=True)
    created_at         = db.Column(db.DateTime,   nullable=False, server_default=db.func.now())

    def to_dict(self):
        return {
            "id":                 self.id,
            "company_id":         self.company_id,
            "order_id":           self.order_id,
            "user_id":            self.user_id,
            "tipo":               self.tipo,
            "data":               self.data,
            "hora":               self.hora,
            "reagendamento_data": self.reagendamento_data,
            "reagendamento_hora": self.reagendamento_hora,
            "descricao":          self.descricao,
            "created_at":         self.created_at.isoformat() if self.created_at else None,
        }