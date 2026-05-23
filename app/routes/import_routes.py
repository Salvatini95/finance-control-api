"""
import_routes.py — Importação de dados no SV Finance
Suporta:
  - CSV genérico com mapeamento customizado de colunas
  - Templates pré-mapeados: Conta Azul, Omie, Nibo, Linx
  - Preview antes de confirmar
  - Detecção e tratamento de duplicatas
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import User, Client, Product, Transaction, Bill, StockMovement, ImportLog
from datetime import date, datetime
import csv, io, re, json

import_bp = Blueprint("import", __name__)


def _get_user(uid): return User.query.get(int(uid))

# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZAÇÃO DE ENTITY — aceita inglês e português
# ─────────────────────────────────────────────────────────────────────────────

ENTITY_ALIASES = {
    # inglês → português (padrão interno)
    "clients":      "clientes",
    "products":     "produtos",
    "transactions": "transacoes",
    "bills":        "contas",
    "team":         "equipe",
    "sales":        "vendas",
    "quotes":       "orcamentos",
    # português já correto
    "clientes":     "clientes",
    "produtos":     "produtos",
    "transacoes":   "transacoes",
    "contas":       "contas",
    "equipe":       "equipe",
}

def _normalize_entity(raw):
    """Converte entity em inglês ou português para o padrão interno."""
    return ENTITY_ALIASES.get(str(raw).strip().lower(), raw)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE NORMALIZAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def _parse_float(v):
    if not v: return 0.0
    try:
        return float(re.sub(r"[^\d,\.]", "", str(v)).replace(",", ".") or 0)
    except:
        return 0.0

def _parse_date(v):
    """Aceita DD/MM/YYYY, YYYY-MM-DD, MM/DD/YYYY."""
    if not v: return str(date.today())
    v = str(v).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
        try: return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
        except: continue
    return str(date.today())

def _clean_doc(v):
    return re.sub(r"\D", "", str(v or ""))

def _parse_bool(v, true_values=("sim","true","1","ativo","yes","s")):
    return str(v).strip().lower() in true_values

def _already_exists_client(user, name, document):
    q = Client.query.filter_by(company_id=user.company_id) if user.company_id \
        else Client.query.filter_by(user_id=user.id)
    doc = _clean_doc(document)
    if doc:
        c = q.filter(Client.document == doc).first()
        if c: return c
    return q.filter(Client.name.ilike(name.strip())).first() if name else None

def _already_exists_product(user, name, sku):
    q = Product.query.filter_by(company_id=user.company_id) if user.company_id \
        else Product.query.filter_by(user_id=user.id)
    if sku:
        p = q.filter(Product.sku == sku.strip()).first()
        if p: return p
    return q.filter(Product.name.ilike(name.strip())).first() if name else None

def _read_csv(text):
    reader = csv.DictReader(io.StringIO(text))
    rows   = list(reader)
    return reader.fieldnames or [], rows


# ─────────────────────────────────────────────────────────────────────────────
# MAPEAMENTOS DE SISTEMAS ESPECÍFICOS
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_MAPS = {
    "conta_azul": {
        "clientes": {
            "name":     ["Nome"],
            "document": ["CPF/CNPJ"],
            "email":    ["Email"],
            "phone":    ["Celular", "Telefone"],
            "address":  ["Logradouro", "Numero", "Bairro", "Cidade", "Estado"],
            "active":   ["Ativo"],
        },
        "transacoes": {
            "date":        ["Data"],
            "description": ["Descricao"],
            "amount":      ["Valor"],
            "type":        ["Tipo"],
            "category":    ["Categoria"],
        },
        "produtos": {
            "name":      ["Nome"],
            "sku":       ["Codigo"],
            "price":     ["Preco de Venda"],
            "cost":      ["Custo"],
            "category":  ["Categoria"],
            "type":      ["Tipo"],
            "unit":      ["Unidade"],
            "stock_qty": ["Estoque Atual"],
            "stock_min": ["Estoque Minimo"],
        }
    },
    "omie": {
        "clientes": {
            "name":     ["razao_social", "nome_fantasia"],
            "document": ["cnpj_cpf"],
            "email":    ["email"],
            "phone":    ["telefone1_numero"],
            "active":   ["inativo"],
        },
        "transacoes": {
            "date":        ["data_lancamento"],
            "description": ["descricao"],
            "amount":      ["valor"],
            "type":        ["tipo"],
            "category":    ["categoria"],
        },
        "produtos": {
            "name":      ["descricao"],
            "sku":       ["codigo_produto"],
            "price":     ["preco_unitario"],
            "cost":      ["valor_unitario_compra"],
            "type":      ["tipo"],
            "unit":      ["unidade"],
        }
    },
    "linx": {
        "clientes": {
            "name":     ["RazaoSocial","NomeFantasia","Nome","NOME"],
            "document": ["CNPJ","CPF","CpfCnpj","CPF_CNPJ"],
            "email":    ["Email","EMAIL"],
            "phone":    ["Celular","Telefone","CELULAR"],
            "address":  ["Logradouro","Endereco","ENDERECO"],
            "active":   ["Ativo","ATIVO","Status"],
        },
        "transacoes": {
            "date":        ["DataEmissao","DataLancamento","Data","DataMovimento"],
            "description": ["Descricao","Historico","NomeProduto"],
            "amount":      ["Valor","ValorTotal","ValorLiquido"],
            "type":        ["TipoMovimento","Tipo","NaturezaOperacao"],
            "category":    ["Categoria","GrupoProduto","ContaContabil"],
        },
        "produtos": {
            "name":      ["DescricaoProduto","Descricao","NomeProduto","Nome"],
            "sku":       ["CodigoProduto","Codigo","SKU","CodigoBarras"],
            "price":     ["PrecoVenda","PrecoPadrao","Preco"],
            "cost":      ["PrecoCusto","CustoMedio","Custo"],
            "category":  ["GrupoProduto","Categoria","GRUPO"],
            "type":      ["TipoProduto","Tipo"],
            "unit":      ["UnidadeMedida","Unidade"],
            "stock_qty": ["SaldoAtual","EstoqueAtual","Estoque"],
            "stock_min": ["EstoqueMinimo","SaldoMinimo"],
        }
    },
    "nibo": {
        "clientes": {
            "name":     ["Nome"],
            "document": ["Documento"],
            "email":    ["Email"],
            "phone":    ["Celular","Telefone"],
            "active":   ["Ativo"],
        },
        "transacoes": {
            "date":        ["Data"],
            "description": ["Descricao"],
            "amount":      ["Valor"],
            "type":        ["TipoTransacao"],
            "category":    ["Categoria","SubCategoria"],
        },
        "produtos": {
            "name":      ["Nome"],
            "sku":       ["Codigo"],
            "price":     ["PrecoVenda"],
            "cost":      ["CustoMedio"],
            "type":      ["Tipo"],
            "unit":      ["UnidadeMedida"],
            "stock_qty": ["EstoqueAtual"],
            "stock_min": ["EstoqueMinimo"],
        }
    },
}

def _get_val(row, keys):
    for k in keys:
        if k in row and str(row[k]).strip():
            return str(row[k]).strip()
    return ""

def _resolve_type_transacao(v, sistema):
    v = str(v).strip().lower()
    if sistema == "conta_azul":
        return "income" if "receita" in v else "expense"
    if sistema == "omie":
        return "income" if v == "r" else "expense"
    if sistema == "nibo":
        return "income" if "recebimento" in v else "expense"
    if sistema == "linx":
        return "income" if v in ("e","entrada","receita","c","credito","crédito","venda") else "expense"
    # genérico — aceita PT e EN
    return "income" if v in ("income","receita","entrada","r","recebimento","1") else "expense"

def _resolve_type_produto(v, sistema):
    v = str(v).strip().lower()
    if sistema in ("conta_azul","nibo"):
        return "product" if "produto" in v else "service"
    if sistema == "omie":
        return "product" if v == "p" else "service"
    if sistema == "linx":
        return "service" if v in ("s","servico","serviço","serv") else "product"
    return "product" if v in ("product","produto","p","1") else "service"

def _resolve_active_client(v, sistema):
    v = str(v).strip().lower()
    if sistema == "omie":
        return v == "0"
    return v in ("sim","true","1","ativo","yes","s")

def _build_address_ca(row):
    parts = [row.get("Logradouro",""), row.get("Numero",""),
             row.get("Bairro",""), row.get("Cidade",""), row.get("Estado","")]
    return ", ".join(p for p in parts if p)


# ─────────────────────────────────────────────────────────────────────────────
# CONVERSOR: ROW → OBJETO NORMALIZADO
# Aceita cabeçalhos em PT ou EN automaticamente
# ─────────────────────────────────────────────────────────────────────────────

def _row_to_client(row, sistema, col_map=None):
    if sistema == "generico":
        m = col_map or {}
        # tenta col_map primeiro, depois PT, depois EN
        name     = row.get(m.get("name",""),     row.get("nome",      row.get("name",     "")))
        document = row.get(m.get("document",""), row.get("documento", row.get("document", row.get("cpf_cnpj", ""))))
        email    = row.get(m.get("email",""),    row.get("email",     ""))
        phone    = row.get(m.get("phone",""),    row.get("telefone",  row.get("phone",    row.get("celular", ""))))
        address  = row.get(m.get("address",""),  row.get("endereco",  row.get("address",  "")))
        notes    = row.get(m.get("notes",""),    row.get("observacoes", row.get("notes",  "")))
    else:
        mp      = SYSTEM_MAPS[sistema]["clientes"]
        name    = _get_val(row, mp["name"])
        document= _get_val(row, mp["document"])
        email   = _get_val(row, mp["email"])
        phone   = _get_val(row, mp["phone"])
        notes   = ""
        active  = _resolve_active_client(_get_val(row, mp["active"]), sistema)
        address = _build_address_ca(row) if sistema == "conta_azul" else \
                  _get_val(row, ["endereco","address","Logradouro"])

    return {
        "name":     str(name).strip(),
        "document": _clean_doc(document),
        "email":    str(email).strip(),
        "phone":    str(phone).strip(),
        "address":  str(address).strip(),
        "notes":    str(notes).strip(),
    }


def _row_to_transaction(row, sistema, col_map=None):
    if sistema == "generico":
        m = col_map or {}
        date_v  = row.get(m.get("date",""),        row.get("data",      row.get("date",        "")))
        desc    = row.get(m.get("description",""),  row.get("descricao", row.get("description", row.get("descricão", ""))))
        amount  = row.get(m.get("amount",""),       row.get("valor",     row.get("amount",      "0")))
        type_v  = row.get(m.get("type",""),         row.get("tipo",      row.get("type",        "income")))
        cat     = row.get(m.get("category",""),     row.get("categoria", row.get("category",    "")))
        t_type  = _resolve_type_transacao(type_v, "generico")
    else:
        mp     = SYSTEM_MAPS[sistema]["transacoes"]
        date_v = _get_val(row, mp["date"])
        desc   = _get_val(row, mp["description"])
        amount = _get_val(row, mp["amount"])
        type_v = _get_val(row, mp["type"])
        cat    = _get_val(row, mp["category"])
        t_type = _resolve_type_transacao(type_v, sistema)

    return {
        "date":        _parse_date(date_v),
        "description": str(desc).strip(),
        "amount":      _parse_float(amount),
        "type":        t_type,
        "category":    str(cat).strip(),
        "source":      "import",
    }


def _row_to_product(row, sistema, col_map=None):
    if sistema == "generico":
        m = col_map or {}
        name  = row.get(m.get("name",""),      row.get("nome",         row.get("name",      "")))
        sku   = row.get(m.get("sku",""),        row.get("sku",          row.get("codigo",    "")))
        price = row.get(m.get("price",""),      row.get("preco",        row.get("price",     row.get("preço", row.get("Preço de Venda", "0")))))
        cost  = row.get(m.get("cost",""),       row.get("custo",        row.get("cost",      "0")))
        cat   = row.get(m.get("category",""),   row.get("categoria",    row.get("category",  "")))
        type_v= row.get(m.get("type",""),       row.get("tipo",         row.get("type",      "product")))
        unit  = row.get(m.get("unit",""),       row.get("unidade",      row.get("unit",      "un")))
        stock = row.get(m.get("stock_qty",""),  row.get("estoque",      row.get("stock_qty", row.get("Estoque", "0"))))
        s_min = row.get(m.get("stock_min",""),  row.get("estoque_min",  row.get("stock_min", row.get("Estoque Mínimo", "0"))))
        desc  = row.get(m.get("description",""),row.get("descricao",    row.get("description","")))
        p_type = _resolve_type_produto(type_v, "generico")
    else:
        mp     = SYSTEM_MAPS[sistema]["produtos"]
        name   = _get_val(row, mp["name"])
        sku    = _get_val(row, mp.get("sku",   ["sku"]))
        price  = _get_val(row, mp["price"])
        cost   = _get_val(row, mp["cost"])
        cat    = _get_val(row, mp.get("category", ["categoria","Categoria"]))
        type_v = _get_val(row, mp["type"])
        unit   = _get_val(row, mp["unit"])
        stock  = _get_val(row, mp.get("stock_qty", ["stock_qty"]))
        s_min  = _get_val(row, mp.get("stock_min", ["stock_min"]))
        desc   = ""
        p_type = _resolve_type_produto(type_v, sistema)

    return {
        "name":              str(name).strip(),
        "sku":               str(sku).strip() or None,
        "price":             _parse_float(price),
        "cost":              _parse_float(cost),
        "category":          str(cat).strip(),
        "type":              p_type,
        "unit":              str(unit).strip() or "un",
        "stock_qty_initial": _parse_float(stock),
        "stock_min":         _parse_float(s_min),
        "description":       str(desc).strip(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: PREVIEW (não salva nada)
# ─────────────────────────────────────────────────────────────────────────────

@import_bp.route("/import/preview", methods=["POST"])
@jwt_required()
def preview_import():
    user = _get_user(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get("csv_text"):
        return jsonify({"error": "csv_text é obrigatório"}), 400

    csv_text = data["csv_text"]
    entity   = _normalize_entity(data.get("entity", "transacoes"))
    sistema  = data.get("sistema", "generico")
    col_map  = data.get("col_map", {})

    headers, rows = _read_csv(csv_text)
    if not rows:
        return jsonify({"error": "CSV vazio ou sem dados"}), 400

    preview  = []
    warnings = []

    for i, row in enumerate(rows[:5]):
        try:
            if entity == "clientes":
                obj = _row_to_client(row, sistema, col_map)
                dup = _already_exists_client(user, obj["name"], obj["document"])
                obj["_duplicate"]      = dup.id   if dup else None
                obj["_duplicate_name"] = dup.name if dup else None
            elif entity == "transacoes":
                obj = _row_to_transaction(row, sistema, col_map)
                obj["_duplicate"] = None
            elif entity == "produtos":
                obj = _row_to_product(row, sistema, col_map)
                dup = _already_exists_product(user, obj["name"], obj.get("sku"))
                obj["_duplicate"]      = dup.id   if dup else None
                obj["_duplicate_name"] = dup.name if dup else None
            else:
                obj = dict(row)
                obj["_duplicate"] = None
            preview.append(obj)
        except Exception as e:
            warnings.append(f"Linha {i+2}: {str(e)}")

    return jsonify({
        "headers":    headers,
        "total_rows": len(rows),
        "preview":    preview,
        "warnings":   warnings,
        "sistema":    sistema,
        "entity":     entity,
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: CONFIRMAR IMPORTAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

@import_bp.route("/import/confirm", methods=["POST"])
@jwt_required()
def confirm_import():
    user = _get_user(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get("csv_text"):
        return jsonify({"error": "csv_text é obrigatório"}), 400

    csv_text   = data["csv_text"]
    entity     = _normalize_entity(data.get("entity", "transacoes"))
    sistema    = data.get("sistema", "generico")
    col_map    = data.get("col_map", {})
    dup_action = data.get("duplicate_action", "skip")

    _, rows = _read_csv(csv_text)
    if not rows:
        return jsonify({"error": "CSV vazio"}), 400

    created = 0; updated = 0; skipped = 0
    errors  = []
    duplicates_notified = []

    for i, row in enumerate(rows):
        try:
            # ── CLIENTES ──────────────────────────────────────────────────
            if entity == "clientes":
                obj = _row_to_client(row, sistema, col_map)
                if not obj["name"]:
                    skipped += 1; continue

                dup = _already_exists_client(user, obj["name"], obj["document"])
                if dup:
                    if dup_action == "skip":
                        skipped += 1; continue
                    elif dup_action == "update":
                        changed = False
                        if obj["email"]   and obj["email"]   != dup.email:   dup.email   = obj["email"];   changed = True
                        if obj["phone"]   and obj["phone"]   != dup.phone:   dup.phone   = obj["phone"];   changed = True
                        if obj["address"] and obj["address"] != dup.address: dup.address = obj["address"]; changed = True
                        if obj["notes"]   and obj["notes"]   != dup.notes:   dup.notes   = obj["notes"];   changed = True
                        if changed:
                            duplicates_notified.append({"name": dup.name, "row": i+2, "message": "Dados atualizados"})
                        updated += 1; continue
                    # create_anyway — continua e cria novo

                c = Client(
                    name       = obj["name"],
                    document   = obj["document"] or None,
                    email      = obj["email"]    or None,
                    phone      = obj["phone"]    or None,
                    address    = obj["address"]  or None,
                    notes      = obj["notes"]    or None,
                    user_id    = user.id,
                    company_id = user.company_id,
                    created_at = str(date.today()),
                )
                db.session.add(c)
                created += 1

            # ── TRANSAÇÕES ────────────────────────────────────────────────
            elif entity == "transacoes":
                obj = _row_to_transaction(row, sistema, col_map)
                if not obj["description"] or obj["amount"] == 0:
                    skipped += 1; continue

                t = Transaction(
                    description = obj["description"],
                    amount      = obj["amount"],
                    type        = obj["type"],
                    category    = obj["category"] or None,
                    date        = obj["date"],
                    source      = "import",
                    user_id     = user.id,
                    company_id  = user.company_id,
                )
                db.session.add(t)
                created += 1

            # ── PRODUTOS ──────────────────────────────────────────────────
            elif entity == "produtos":
                obj = _row_to_product(row, sistema, col_map)
                if not obj["name"]:
                    skipped += 1; continue

                dup = _already_exists_product(user, obj["name"], obj.get("sku"))
                if dup:
                    if dup_action == "skip":
                        skipped += 1; continue
                    elif dup_action == "update":
                        if obj["price"]:    dup.price    = obj["price"]
                        if obj["cost"]:     dup.cost     = obj["cost"]
                        if obj["category"]: dup.category = obj["category"]
                        if obj["description"]: dup.description = obj["description"]
                        duplicates_notified.append({
                            "name": dup.name, "sku": dup.sku,
                            "row": i+2, "message": "Preço/custo atualizados"
                        })
                        updated += 1; continue

                p = Product(
                    name        = obj["name"],
                    sku         = obj["sku"],
                    price       = obj["price"],
                    cost        = obj["cost"],
                    category    = obj["category"] or None,
                    type        = obj["type"],
                    unit        = obj["unit"],
                    stock_qty   = obj["stock_qty_initial"],
                    stock_min   = obj["stock_min"],
                    description = obj["description"] or None,
                    active      = True,
                    user_id     = user.id,
                    company_id  = user.company_id,
                )
                db.session.add(p)
                db.session.flush()

                # movimento de estoque inicial
                if p.type == "product" and obj["stock_qty_initial"] > 0:
                    db.session.add(StockMovement(
                        type       = "in",
                        qty        = obj["stock_qty_initial"],
                        cost       = obj["cost"] or None,
                        reason     = "Importação CSV",
                        date       = str(date.today()),
                        product_id = p.id,
                        user_id    = user.id,
                        company_id = user.company_id,
                    ))
                created += 1

            else:
                # entity não reconhecida
                skipped += 1

        except Exception as e:
            errors.append(f"Linha {i+2}: {str(e)}")
            if len(errors) > 20: break

    # ── Commit ────────────────────────────────────────────────────────────
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao salvar: {str(e)}"}), 500

    # ── Log da importação ─────────────────────────────────────────────────
    try:
        log = ImportLog(
            type       = "import",
            entity     = entity,
            sistema    = sistema,
            filename   = data.get("filename", "arquivo.csv"),
            total      = len(rows),
            created    = created,
            updated    = updated,
            skipped    = skipped,
            errors     = len(errors),
            errors_log = json.dumps(errors[:50]) if errors else None,
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_id    = user.id,
            company_id = user.company_id,
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass

    return jsonify({
        "created":              created,
        "updated":              updated,
        "skipped":              skipped,
        "errors":               errors,
        "total":                len(rows),
        "duplicates_notified":  duplicates_notified,
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: DETECTAR SISTEMA PELO CABEÇALHO
# ─────────────────────────────────────────────────────────────────────────────

@import_bp.route("/import/detect", methods=["POST"])
@jwt_required()
def detect_system():
    data     = request.get_json()
    csv_text = data.get("csv_text", "")
    headers, _ = _read_csv(csv_text)
    hl = [h.lower() for h in headers]

    def has(*keys): return all(k in hl for k in keys)

    if has("cpf/cnpj","ativo"):
        entity = "clientes" if "nome" in hl else "transacoes" if "tipo" in hl else "produtos"
        return jsonify({"sistema":"conta_azul","entity":entity,"confidence":0.9})
    if has("preco de venda","estoque atual"):
        return jsonify({"sistema":"conta_azul","entity":"produtos","confidence":0.95})
    if has("razao_social","cnpj_cpf"):
        return jsonify({"sistema":"omie","entity":"clientes","confidence":0.95})
    if has("data_lancamento","tipo") and "valor" in hl:
        return jsonify({"sistema":"omie","entity":"transacoes","confidence":0.9})
    if has("codigo_produto","preco_unitario"):
        return jsonify({"sistema":"omie","entity":"produtos","confidence":0.95})
    if "razaosocial" in hl or "codigoproduto" in hl:
        entity = "clientes" if "razaosocial" in hl else "produtos"
        return jsonify({"sistema":"linx","entity":entity,"confidence":0.9})
    if has("tipotransacao","data"):
        return jsonify({"sistema":"nibo","entity":"transacoes","confidence":0.9})

    return jsonify({"sistema":"generico","entity":"transacoes","confidence":0.5})


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: HISTÓRICO
# ─────────────────────────────────────────────────────────────────────────────

@import_bp.route("/import/history", methods=["GET"])
@jwt_required()
def get_history():
    user  = _get_user(get_jwt_identity())
    limit = int(request.args.get("limit", 50))
    type_ = request.args.get("type")

    q = ImportLog.query
    if user.company_id:
        q = q.filter_by(company_id=user.company_id)
    else:
        q = q.filter_by(user_id=user.id)
    if type_:
        q = q.filter_by(type=type_)

    logs = q.order_by(ImportLog.id.desc()).limit(limit).all()

    SISTEMA_LABELS = {
        "generico":"CSV Genérico","conta_azul":"Conta Azul",
        "omie":"Omie","nibo":"Nibo","linx":"Linx",
    }
    ENTITY_LABELS = {
        "clientes":"Clientes","transacoes":"Transações",
        "produtos":"Produtos","contas":"Contas","equipe":"Equipe",
    }

    return jsonify([{
        "id":            l.id,
        "type":          l.type,
        "type_label":    "📥 Importação" if l.type == "import" else "📤 Exportação",
        "entity":        l.entity,
        "entity_label":  ENTITY_LABELS.get(l.entity, l.entity),
        "sistema":       l.sistema,
        "sistema_label": SISTEMA_LABELS.get(l.sistema or "", l.sistema or "—"),
        "filename":      l.filename or "—",
        "total":         l.total,
        "created":       l.created,
        "updated":       l.updated,
        "skipped":       l.skipped,
        "errors":        l.errors,
        "errors_log":    json.loads(l.errors_log) if l.errors_log else [],
        "created_at":    l.created_at,
        "status":        "success" if l.errors == 0 else ("warning" if l.created > 0 else "error"),
    } for l in logs]), 200


@import_bp.route("/import/history/<int:log_id>", methods=["DELETE"])
@jwt_required()
def delete_log(log_id):
    user = _get_user(get_jwt_identity())
    q = ImportLog.query.filter_by(id=log_id)
    if user.company_id:
        q = q.filter_by(company_id=user.company_id)
    else:
        q = q.filter_by(user_id=user.id)
    log = q.first()
    if not log:
        return jsonify({"error": "Log não encontrado"}), 404
    db.session.delete(log)
    db.session.commit()
    return jsonify({"msg": "Log removido"}), 200
