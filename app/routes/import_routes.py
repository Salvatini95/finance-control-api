"""
import_routes.py — Importação de dados no SV Finance
Suporta:
  - CSV genérico com mapeamento customizado de colunas (Fase 2)
  - Templates pré-mapeados: Conta Azul, Omie, Nibo (Fase 3)
  - Preview antes de confirmar
  - Detecção e tratamento de duplicatas
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import User, Client, Product, Transaction, StockMovement
from datetime import date, datetime
import csv, io, re

import_bp = Blueprint("import", __name__)


def _get_user(uid): return User.query.get(int(uid))

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE NORMALIZAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def _parse_float(v):
    if not v: return 0.0
    return float(re.sub(r"[^\d,\.]", "", str(v)).replace(",", ".") or 0)

def _parse_date(v):
    """Aceita DD/MM/YYYY, YYYY-MM-DD ou MM/DD/YYYY."""
    if not v: return str(date.today())
    v = str(v).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
        try: return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
        except: continue
    return str(date.today())

def _clean_doc(v):
    """Remove formatação de CPF/CNPJ."""
    return re.sub(r"\D", "", str(v or ""))

def _parse_bool(v, true_values=("sim","true","1","ativo","yes","s")):
    return str(v).strip().lower() in true_values

def _already_exists_client(user, name, document):
    """Verifica duplicata por nome OU documento."""
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
    """Lê CSV em texto e retorna (headers, rows)."""
    reader = csv.DictReader(io.StringIO(text))
    rows   = list(reader)
    return reader.fieldnames or [], rows


# ─────────────────────────────────────────────────────────────────────────────
# MAPEAMENTOS DE SISTEMAS ESPECÍFICOS
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_MAPS = {
    # ── CONTA AZUL ──────────────────────────────────────────────────────────
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
            "type":        ["Tipo"],       # Receita→income, Despesa→expense
            "category":    ["Categoria"],
        },
        "produtos": {
            "name":      ["Nome"],
            "sku":       ["Codigo"],
            "price":     ["Preco de Venda"],
            "cost":      ["Custo"],
            "category":  ["Categoria"],
            "type":      ["Tipo"],         # Produto→product, Serviço→service
            "unit":      ["Unidade"],
            "stock_qty": ["Estoque Atual"],
            "stock_min": ["Estoque Minimo"],
        }
    },
    # ── OMIE ────────────────────────────────────────────────────────────────
    "omie": {
        "clientes": {
            "name":     ["razao_social", "nome_fantasia"],
            "document": ["cnpj_cpf"],
            "email":    ["email"],
            "phone":    ["telefone1_numero"],
            "active":   ["inativo"],       # 0=ativo, 1=inativo
        },
        "transacoes": {
            "date":        ["data_lancamento"],
            "description": ["descricao"],
            "amount":      ["valor"],
            "type":        ["tipo"],       # R→income, D→expense
            "category":    ["categoria"],
        },
        "produtos": {
            "name":      ["descricao"],
            "sku":       ["codigo_produto"],
            "price":     ["preco_unitario"],
            "cost":      ["valor_unitario_compra"],
            "type":      ["tipo"],         # P→product, S→service
            "unit":      ["unidade"],
        }
    },
    # ── NIBO ────────────────────────────────────────────────────────────────
    "nibo": {
        "clientes": {
            "name":     ["Nome"],
            "document": ["Documento"],
            "email":    ["Email"],
            "phone":    ["Celular", "Telefone"],
            "active":   ["Ativo"],         # true/false
        },
        "transacoes": {
            "date":        ["Data"],
            "description": ["Descricao"],
            "amount":      ["Valor"],
            "type":        ["TipoTransacao"],  # Recebimento→income, Pagamento→expense
            "category":    ["Categoria", "SubCategoria"],
        },
        "produtos": {
            "name":      ["Nome"],
            "sku":       ["Codigo"],
            "price":     ["PrecoVenda"],
            "cost":      ["CustoMedio"],
            "type":      ["Tipo"],         # Produto→product, Serviço→service
            "unit":      ["UnidadeMedida"],
            "stock_qty": ["EstoqueAtual"],
            "stock_min": ["EstoqueMinimo"],
        }
    },
}

def _get_val(row, keys):
    """Pega o primeiro campo que existir no row."""
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
    # genérico
    return "income" if v in ("income","receita","entrada","r","recebimento","1") else "expense"

def _resolve_type_produto(v, sistema):
    v = str(v).strip().lower()
    if sistema in ("conta_azul", "nibo"):
        return "product" if "produto" in v else "service"
    if sistema == "omie":
        return "product" if v == "p" else "service"
    return "product" if v in ("product","produto","p","1") else "service"

def _resolve_active_client(v, sistema):
    v = str(v).strip().lower()
    if sistema == "omie":
        return v == "0"   # inativo=0 significa ativo
    return v in ("sim","true","1","ativo","yes","s")

def _build_address_ca(row):
    parts = [row.get("Logradouro",""), row.get("Numero",""),
             row.get("Bairro",""), row.get("Cidade",""), row.get("Estado","")]
    return ", ".join(p for p in parts if p)


# ─────────────────────────────────────────────────────────────────────────────
# CONVERSOR: ROW → OBJETO NORMALIZADO
# ─────────────────────────────────────────────────────────────────────────────

def _row_to_client(row, sistema, col_map=None):
    """Converte linha CSV para dict padronizado de cliente."""
    if sistema == "generico":
        m = col_map or {}
        name     = row.get(m.get("name",""),     row.get("nome", row.get("name", "")))
        document = row.get(m.get("document",""), row.get("cpf_cnpj", row.get("document", "")))
        email    = row.get(m.get("email",""),    row.get("email", ""))
        phone    = row.get(m.get("phone",""),    row.get("telefone", row.get("phone", "")))
        address  = row.get(m.get("address",""),  row.get("endereco", row.get("address", "")))
        active   = True
    else:
        mp      = SYSTEM_MAPS[sistema]["clientes"]
        name    = _get_val(row, mp["name"])
        document= _get_val(row, mp["document"])
        email   = _get_val(row, mp["email"])
        phone   = _get_val(row, mp["phone"])
        active  = _resolve_active_client(_get_val(row, mp["active"]), sistema)
        address = _build_address_ca(row) if sistema == "conta_azul" else \
                  _get_val(row, ["endereco","address","Logradouro"])

    return {"name": name, "document": _clean_doc(document),
            "email": email, "phone": phone,
            "address": address, "active": active}


def _row_to_transaction(row, sistema, col_map=None):
    if sistema == "generico":
        m = col_map or {}
        date_v  = row.get(m.get("date",""),        row.get("data", row.get("date", "")))
        desc    = row.get(m.get("description",""),  row.get("descricao", row.get("description", "")))
        amount  = row.get(m.get("amount",""),        row.get("valor", row.get("amount", "0")))
        type_v  = row.get(m.get("type",""),          row.get("tipo", row.get("type", "income")))
        cat     = row.get(m.get("category",""),      row.get("categoria", row.get("category", "")))
        t_type  = _resolve_type_transacao(type_v, "generico")
    else:
        mp     = SYSTEM_MAPS[sistema]["transacoes"]
        date_v = _get_val(row, mp["date"])
        desc   = _get_val(row, mp["description"])
        amount = _get_val(row, mp["amount"])
        type_v = _get_val(row, mp["type"])
        cat    = _get_val(row, mp["category"])
        t_type = _resolve_type_transacao(type_v, sistema)

    return {"date": _parse_date(date_v), "description": desc,
            "amount": _parse_float(amount), "type": t_type,
            "category": cat, "source": "import"}


def _row_to_product(row, sistema, col_map=None):
    if sistema == "generico":
        m = col_map or {}
        name  = row.get(m.get("name",""),      row.get("nome", row.get("name", "")))
        sku   = row.get(m.get("sku",""),        row.get("sku", row.get("codigo", "")))
        price = row.get(m.get("price",""),      row.get("preco", row.get("price", "0")))
        cost  = row.get(m.get("cost",""),       row.get("custo", row.get("cost", "0")))
        cat   = row.get(m.get("category",""),   row.get("categoria", row.get("category", "")))
        type_v= row.get(m.get("type",""),       row.get("tipo", row.get("type", "product")))
        unit  = row.get(m.get("unit",""),       row.get("unidade", row.get("unit", "un")))
        stock = row.get(m.get("stock_qty",""),  row.get("estoque", row.get("stock_qty", "0")))
        s_min = row.get(m.get("stock_min",""),  row.get("estoque_min", row.get("stock_min", "0")))
        p_type = _resolve_type_produto(type_v, "generico")
    else:
        mp     = SYSTEM_MAPS[sistema]["produtos"]
        name   = _get_val(row, mp["name"])
        sku    = _get_val(row, mp.get("sku", ["sku"]))
        price  = _get_val(row, mp["price"])
        cost   = _get_val(row, mp["cost"])
        cat    = _get_val(row, mp.get("category", ["categoria","Categoria"]))
        type_v = _get_val(row, mp["type"])
        unit   = _get_val(row, mp["unit"])
        stock  = _get_val(row, mp.get("stock_qty", ["stock_qty"]))
        s_min  = _get_val(row, mp.get("stock_min", ["stock_min"]))
        p_type = _resolve_type_produto(type_v, sistema)

    return {"name": name, "sku": sku or None,
            "price": _parse_float(price), "cost": _parse_float(cost),
            "category": cat, "type": p_type,
            "unit": unit or "un",
            "stock_qty_initial": _parse_float(stock),
            "stock_min": _parse_float(s_min)}


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: PREVIEW (não salva nada)
# ─────────────────────────────────────────────────────────────────────────────

@import_bp.route("/import/preview", methods=["POST"])
@jwt_required()
def preview_import():
    """
    Recebe CSV em texto + parâmetros, retorna preview sem salvar.
    Body JSON:
      csv_text   : string com conteúdo do arquivo
      entity     : "clientes" | "transacoes" | "produtos"
      sistema    : "generico" | "conta_azul" | "omie" | "nibo"
      col_map    : { campo_sv: coluna_csv } — só para sistema=generico
    """
    user = _get_user(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get("csv_text"):
        return jsonify({"error": "csv_text é obrigatório"}), 400

    csv_text = data["csv_text"]
    entity   = data.get("entity", "transacoes")
    sistema  = data.get("sistema", "generico")
    col_map  = data.get("col_map", {})

    headers, rows = _read_csv(csv_text)
    if not rows:
        return jsonify({"error": "CSV vazio ou sem dados"}), 400

    preview  = []
    warnings = []

    for i, row in enumerate(rows[:5]):   # preview das 5 primeiras linhas
        try:
            if entity == "clientes":
                obj = _row_to_client(row, sistema, col_map)
                dup = _already_exists_client(user, obj["name"], obj["document"])
                obj["_duplicate"] = dup.id if dup else None
                obj["_duplicate_name"] = dup.name if dup else None
            elif entity == "transacoes":
                obj = _row_to_transaction(row, sistema, col_map)
                obj["_duplicate"] = None
            else:
                obj = _row_to_product(row, sistema, col_map)
                dup = _already_exists_product(user, obj["name"], obj.get("sku"))
                obj["_duplicate"] = dup.id if dup else None
                obj["_duplicate_name"] = dup.name if dup else None
            preview.append(obj)
        except Exception as e:
            warnings.append(f"Linha {i+2}: {str(e)}")

    return jsonify({
        "headers":      headers,
        "total_rows":   len(rows),
        "preview":      preview,
        "warnings":     warnings,
        "sistema":      sistema,
        "entity":       entity,
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: CONFIRMAR IMPORTAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

@import_bp.route("/import/confirm", methods=["POST"])
@jwt_required()
def confirm_import():
    """
    Processa e salva todos os registros.
    Body JSON:
      csv_text          : string CSV
      entity            : "clientes" | "transacoes" | "produtos"
      sistema           : "generico" | "conta_azul" | "omie" | "nibo"
      col_map           : { campo_sv: coluna_csv }
      duplicate_action  : "skip" | "update" | "create_anyway"
    """
    user = _get_user(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get("csv_text"):
        return jsonify({"error": "csv_text é obrigatório"}), 400

    csv_text  = data["csv_text"]
    entity    = data.get("entity", "transacoes")
    sistema   = data.get("sistema", "generico")
    col_map   = data.get("col_map", {})
    dup_action= data.get("duplicate_action", "skip")  # skip | update | create_anyway

    _, rows = _read_csv(csv_text)
    if not rows:
        return jsonify({"error": "CSV vazio"}), 400

    created = 0; updated = 0; skipped = 0; errors = []

    for i, row in enumerate(rows):
        try:
            if entity == "clientes":
                obj = _row_to_client(row, sistema, col_map)
                if not obj["name"]:
                    skipped += 1; continue
                dup = _already_exists_client(user, obj["name"], obj["document"])
                if dup:
                    if dup_action == "skip":
                        skipped += 1; continue
                    elif dup_action == "update":
                        if obj["email"]: dup.email   = obj["email"]
                        if obj["phone"]: dup.phone   = obj["phone"]
                        if obj["address"]: dup.address = obj["address"]
                        updated += 1; continue
                    # create_anyway → cria novo
                c = Client(
                    name=obj["name"], document=obj["document"] or None,
                    email=obj["email"] or None, phone=obj["phone"] or None,
                    address=obj["address"] or None, active=obj["active"],
                    user_id=user.id, company_id=user.company_id,
                )
                db.session.add(c); created += 1

            elif entity == "transacoes":
                obj = _row_to_transaction(row, sistema, col_map)
                if not obj["description"] or obj["amount"] == 0:
                    skipped += 1; continue
                t = Transaction(
                    description=obj["description"], amount=obj["amount"],
                    type=obj["type"], category=obj["category"] or None,
                    date=obj["date"], source="import",
                    user_id=user.id, company_id=user.company_id,
                )
                db.session.add(t); created += 1

            elif entity == "produtos":
                obj = _row_to_product(row, sistema, col_map)
                if not obj["name"]:
                    skipped += 1; continue
                dup = _already_exists_product(user, obj["name"], obj.get("sku"))
                if dup:
                    if dup_action == "skip":
                        skipped += 1; continue
                    elif dup_action == "update":
                        dup.price    = obj["price"] or dup.price
                        dup.cost     = obj["cost"]  or dup.cost
                        dup.category = obj["category"] or dup.category
                        updated += 1; continue
                p = Product(
                    name=obj["name"], sku=obj["sku"],
                    price=obj["price"], cost=obj["cost"],
                    category=obj["category"] or None,
                    type=obj["type"], unit=obj["unit"],
                    stock_qty=obj["stock_qty_initial"],
                    stock_min=obj["stock_min"],
                    active=True,
                    user_id=user.id, company_id=user.company_id,
                )
                db.session.add(p)
                db.session.flush()
                if p.type == "product" and obj["stock_qty_initial"] > 0:
                    db.session.add(StockMovement(
                        type="in", qty=obj["stock_qty_initial"],
                        cost=obj["cost"] or None, reason="Importação",
                        date=str(date.today()),
                        product_id=p.id, user_id=user.id, company_id=user.company_id,
                    ))
                created += 1

        except Exception as e:
            errors.append(f"Linha {i+2}: {str(e)}")
            if len(errors) > 20: break   # evita log gigante

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao salvar: {str(e)}"}), 500

    return jsonify({
        "created": created, "updated": updated,
        "skipped": skipped, "errors":  errors,
        "total":   len(rows),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: DETECTAR SISTEMA PELO CABEÇALHO
# ─────────────────────────────────────────────────────────────────────────────

@import_bp.route("/import/detect", methods=["POST"])
@jwt_required()
def detect_system():
    """
    Recebe as primeiras linhas do CSV e tenta identificar o sistema de origem.
    Retorna: { sistema, entity, confidence }
    """
    data     = request.get_json()
    csv_text = data.get("csv_text", "")
    headers, _ = _read_csv(csv_text)
    headers_lower = [h.lower() for h in headers]

    def has(*keys): return all(k in headers_lower for k in keys)

    # Conta Azul
    if has("cpf/cnpj", "ativo"):
        sistema = "conta_azul"
        entity  = "clientes" if "nome" in headers_lower else \
                  "transacoes" if "tipo" in headers_lower else "produtos"
        return jsonify({"sistema": sistema, "entity": entity, "confidence": 0.9})

    if has("preco de venda", "estoque atual"):
        return jsonify({"sistema": "conta_azul", "entity": "produtos", "confidence": 0.95})

    # Omie
    if has("razao_social", "cnpj_cpf"):
        return jsonify({"sistema": "omie", "entity": "clientes", "confidence": 0.95})

    if has("data_lancamento", "tipo") and "valor" in headers_lower:
        return jsonify({"sistema": "omie", "entity": "transacoes", "confidence": 0.9})

    if has("codigo_produto", "preco_unitario"):
        return jsonify({"sistema": "omie", "entity": "produtos", "confidence": 0.95})

    # Nibo
    if has("tipotransacao", "datacimento") or has("tipotransacao","data"):
        return jsonify({"sistema": "nibo", "entity": "transacoes", "confidence": 0.9})

    if has("preçovenda","customedio") or has("precovenda","custo"):
        return jsonify({"sistema": "nibo", "entity": "produtos", "confidence": 0.9})

    if "documento" in headers_lower and "tipoDocumento".lower() in headers_lower:
        return jsonify({"sistema": "nibo", "entity": "clientes", "confidence": 0.85})

    # genérico
    return jsonify({"sistema": "generico", "entity": "transacoes", "confidence": 0.5})