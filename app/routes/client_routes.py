# app/routes/client_routes.py
"""
Rotas de clientes — legado mantido, com suporte aos novos campos:
  - emails_json / phones_json  (múltiplos contatos)
  - recorrencia                (campo independente do tipo de contrato)
  - contrato_modelo            (texto livre)
  - codigo_seq                 (sequencial automático por empresa)

Geração de código: ao criar um cliente sem código manual, o sistema
atribui o próximo codigo_seq disponível para a empresa e formata
o campo codigo como "001", "002", etc. Se o admin já enviou um
codigo manual, pergunta-se no frontend se quer substituir (flag
`confirmar_substituicao_codigo` no payload).
"""
import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Client, User
from datetime import date
from sqlalchemy import func
import requests as http

client_bp = Blueprint("clients", __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user(user_id):
    return User.query.get(int(user_id))


def _find_client(client_id, user):
    if user.company_id:
        return Client.query.filter_by(id=client_id, company_id=user.company_id).first()
    return Client.query.filter_by(id=client_id, user_id=user.id).first()


def _none_if_empty(v):
    """Converte string vazia para None — evita erro em campos numéricos do PostgreSQL."""
    if v is None or v == "" or (isinstance(v, str) and v.strip() == ""):
        return None
    return v


def _proximo_codigo_seq(company_id: int) -> int:
    """
    Retorna o próximo código sequencial disponível para a empresa.
    Busca o maior codigo_seq existente e incrementa 1.
    """
    max_seq = db.session.query(func.max(Client.codigo_seq)).filter_by(
        company_id=company_id
    ).scalar()
    return (max_seq or 0) + 1


def _formatar_codigo(seq: int) -> str:
    """Formata o sequencial como string com 3 dígitos: 1 → '001'."""
    return str(seq).zfill(3)


def _json_lista(valor) -> str:
    """
    Garante que emails/phones sejam salvos como JSON array válido.
    Aceita lista Python ou string JSON. Retorna string JSON.
    """
    if valor is None:
        return "[]"
    if isinstance(valor, list):
        # filtra strings vazias
        return json.dumps([v for v in valor if v and str(v).strip()])
    if isinstance(valor, str):
        try:
            parsed = json.loads(valor)
            if isinstance(parsed, list):
                return json.dumps([v for v in parsed if v and str(v).strip()])
        except (json.JSONDecodeError, ValueError):
            pass
    return "[]"


def _cep_para_coordenadas(cep: str) -> dict:
    cep_limpo = "".join(filter(str.isdigit, cep or ""))
    if len(cep_limpo) != 8:
        return None
    try:
        r = http.get(
            f"https://viacep.com.br/ws/{cep_limpo}/json/",
            timeout=5,
            headers={"User-Agent": "SVFinance/1.0"},
        )
        viacep = r.json()
        if viacep.get("erro"):
            return None
    except Exception:
        return None

    logradouro = viacep.get("logradouro", "")
    bairro     = viacep.get("bairro",     "")
    municipio  = viacep.get("localidade", "")
    uf         = viacep.get("uf",         "")

    try:
        query = f"{logradouro}, {bairro}, {municipio}, {uf}, Brasil"
        r2 = http.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "br"},
            timeout=8,
            headers={"User-Agent": "SVFinance/1.0 (contato@svfinance.com.br)"},
        )
        resultados = r2.json()
        if not resultados:
            r3 = http.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": f"{municipio}, {uf}, Brasil", "format": "json", "limit": 1, "countrycodes": "br"},
                timeout=8,
                headers={"User-Agent": "SVFinance/1.0 (contato@svfinance.com.br)"},
            )
            resultados = r3.json()
        if resultados:
            return {
                "lat": float(resultados[0]["lat"]),
                "lon": float(resultados[0]["lon"]),
                "logradouro": logradouro, "bairro": bairro,
                "municipio": municipio, "uf": uf, "cep": cep_limpo,
            }
    except Exception:
        pass

    return {
        "lat": None, "lon": None,
        "logradouro": logradouro, "bairro": bairro,
        "municipio": municipio, "uf": uf, "cep": cep_limpo,
    }


def _client_to_dict(c: Client, include_relations=False) -> dict:
    data = {
        "id":          c.id,
        "codigo":      c.codigo,
        "codigo_seq":  c.codigo_seq,
        "name":        c.name,
        "email":       c.email,
        "phone":       c.phone,
        "emails":      json.loads(c.emails_json) if c.emails_json else [],
        "phones":      json.loads(c.phones_json) if c.phones_json else [],
        "document":    c.document,
        "cnpj":        c.cnpj,
        "address":     c.address,
        "notes":       c.notes,
        "created_at":  c.created_at,
        "cep":         c.cep,
        "logradouro":  c.logradouro,
        "numero":      c.numero,
        "bairro":      c.bairro,
        "municipio":   c.municipio,
        "uf":          c.uf,
        "latitude":    c.latitude,
        "longitude":   c.longitude,
        "tem_gps":     c.latitude is not None and c.longitude is not None,
        "contrato_tipo":            c.contrato_tipo,
        "contrato_valor":           c.contrato_valor,
        "contrato_forma_pagamento": c.contrato_forma_pagamento,
        "contrato_dia_pagamento":   c.contrato_dia_pagamento,
        "contrato_inicio":          c.contrato_inicio,
        "contrato_fim":             c.contrato_fim,
        "contrato_status":          c.contrato_status,
        "contrato_dias_semana":     c.contrato_dias_semana,
        "contrato_observacoes":     c.contrato_observacoes,
        "contrato_modelo":          c.contrato_modelo,
        "recorrencia":              c.recorrencia,
    }
    if include_relations:
        data["quotes"] = [
            {"id": q.id, "number": q.number, "status": q.status,
             "total": q.total, "created_at": q.created_at}
            for q in c.quotes
        ]
        data["orders"] = [
            {"id": o.id, "number": o.number, "status": o.status,
             "total": o.total, "created_at": o.created_at}
            for o in c.orders
        ]
    return data


# ── Rotas ─────────────────────────────────────────────────────────────────────

@client_bp.route("/clients", methods=["GET"])
@jwt_required()
def get_clients():
    user = _get_user(get_jwt_identity())
    if user.company_id:
        clients = Client.query.filter_by(company_id=user.company_id).order_by(Client.name).all()
    else:
        clients = Client.query.filter_by(user_id=user.id).order_by(Client.name).all()
    return jsonify([_client_to_dict(c) for c in clients]), 200


@client_bp.route("/clients/<int:client_id>", methods=["GET"])
@jwt_required()
def get_client(client_id):
    user = _get_user(get_jwt_identity())
    c    = _find_client(client_id, user)
    if not c:
        return jsonify({"msg": "Cliente não encontrado"}), 404
    return jsonify(_client_to_dict(c, include_relations=True)), 200


@client_bp.route("/clients/proximo-codigo", methods=["GET"])
@jwt_required()
def get_proximo_codigo():
    """
    Retorna o próximo código sequencial disponível para a empresa.
    Usado pelo frontend para pré-preencher o campo antes de criar.
    """
    user = _get_user(get_jwt_identity())
    if not user.company_id:
        return jsonify({"msg": "Empresa não encontrada"}), 400
    seq     = _proximo_codigo_seq(user.company_id)
    codigo  = _formatar_codigo(seq)
    return jsonify({"seq": seq, "codigo": codigo}), 200


@client_bp.route("/clients", methods=["POST"])
@jwt_required()
def create_client():
    user = _get_user(get_jwt_identity())
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    if not name:
        return jsonify({"msg": "Nome é obrigatório"}), 400

    geo = _cep_para_coordenadas(data.get("cep", ""))

    # ── Geração de código sequencial ──────────────────────────────────────────
    codigo_manual = _none_if_empty(data.get("codigo"))
    company_id    = user.company_id

    if company_id:
        seq    = _proximo_codigo_seq(company_id)
        codigo = codigo_manual if codigo_manual else _formatar_codigo(seq)
    else:
        seq    = None
        codigo = codigo_manual

    # ── Emails e telefones múltiplos ──────────────────────────────────────────
    emails_json = _json_lista(data.get("emails", []))
    phones_json = _json_lista(data.get("phones", []))

    # email/phone principal = primeiro da lista (compatibilidade offline/legado)
    emails_lista = json.loads(emails_json)
    phones_lista = json.loads(phones_json)
    email_principal = _none_if_empty(emails_lista[0]) if emails_lista else _none_if_empty(data.get("email"))
    phone_principal = _none_if_empty(phones_lista[0]) if phones_lista else _none_if_empty(data.get("phone"))

    c = Client(
        name        = name,
        codigo      = codigo,
        codigo_seq  = seq,
        email       = email_principal,
        phone       = phone_principal,
        emails_json = emails_json,
        phones_json = phones_json,
        document    = _none_if_empty(data.get("document")),
        cnpj        = _none_if_empty(data.get("cnpj")),
        address     = _none_if_empty(data.get("address")),
        notes       = _none_if_empty(data.get("notes")),
        created_at  = str(date.today()),
        user_id     = user.id,
        company_id  = company_id,
        cep         = geo["cep"]        if geo else _none_if_empty(data.get("cep")),
        logradouro  = geo["logradouro"] if geo else _none_if_empty(data.get("logradouro")),
        bairro      = geo["bairro"]     if geo else _none_if_empty(data.get("bairro")),
        municipio   = geo["municipio"]  if geo else _none_if_empty(data.get("municipio")),
        uf          = geo["uf"]         if geo else _none_if_empty(data.get("uf")),
        numero      = _none_if_empty(data.get("numero")),
        latitude    = geo["lat"] if geo else None,
        longitude   = geo["lon"] if geo else None,
        contrato_tipo            = _none_if_empty(data.get("contrato_tipo"))            or "avulso",
        contrato_valor           = _none_if_empty(data.get("contrato_valor")),
        contrato_forma_pagamento = _none_if_empty(data.get("contrato_forma_pagamento")),
        contrato_dia_pagamento   = _none_if_empty(data.get("contrato_dia_pagamento")),
        contrato_inicio          = _none_if_empty(data.get("contrato_inicio")),
        contrato_fim             = _none_if_empty(data.get("contrato_fim")),
        contrato_status          = _none_if_empty(data.get("contrato_status"))          or "ativo",
        contrato_dias_semana     = _none_if_empty(data.get("contrato_dias_semana")),
        contrato_observacoes     = _none_if_empty(data.get("contrato_observacoes")),
        contrato_modelo          = _none_if_empty(data.get("contrato_modelo")),
        recorrencia              = _none_if_empty(data.get("recorrencia")),
    )
    db.session.add(c)
    db.session.commit()

    return jsonify({
        "msg":     "Cliente criado com sucesso",
        "id":      c.id,
        "name":    c.name,
        "codigo":  c.codigo,
        "tem_gps": c.latitude is not None,
        "geo_msg": (
            "📍 Localização salva automaticamente pelo CEP"
            if (geo and geo.get("lat"))
            else "⚠️ CEP não encontrado — localização não salva"
        ),
    }), 201


@client_bp.route("/clients/<int:client_id>", methods=["PUT"])
@jwt_required()
def update_client(client_id):
    user = _get_user(get_jwt_identity())
    c    = _find_client(client_id, user)
    if not c:
        return jsonify({"msg": "Cliente não encontrado"}), 404

    data = request.get_json() or {}

    c.name     = data.get("name", c.name).strip()
    c.document = _none_if_empty(data.get("document", c.document))
    c.cnpj     = _none_if_empty(data.get("cnpj",     c.cnpj))
    c.address  = _none_if_empty(data.get("address",  c.address))
    c.notes    = _none_if_empty(data.get("notes",    c.notes))
    c.numero   = _none_if_empty(data.get("numero",   c.numero))

    # ── Código: respeita flag de substituição ─────────────────────────────────
    novo_codigo = _none_if_empty(data.get("codigo"))
    if novo_codigo and novo_codigo != c.codigo:
        # frontend envia confirmar_substituicao_codigo=True quando o admin confirmou
        if data.get("confirmar_substituicao_codigo") or not c.codigo:
            c.codigo = novo_codigo
        # se não confirmou, retorna aviso sem alterar (frontend mostrará modal)
        elif c.codigo:
            return jsonify({
                "codigo_conflito": True,
                "codigo_atual":    c.codigo,
                "codigo_novo":     novo_codigo,
                "msg":             f"O cliente já possui o código '{c.codigo}'. Deseja substituir por '{novo_codigo}'?",
            }), 409

    # ── Emails e telefones múltiplos ──────────────────────────────────────────
    if "emails" in data:
        emails_json     = _json_lista(data["emails"])
        c.emails_json   = emails_json
        lista           = json.loads(emails_json)
        c.email         = _none_if_empty(lista[0]) if lista else c.email
    if "phones" in data:
        phones_json     = _json_lista(data["phones"])
        c.phones_json   = phones_json
        lista           = json.loads(phones_json)
        c.phone         = _none_if_empty(lista[0]) if lista else c.phone

    # ── Contrato ──────────────────────────────────────────────────────────────
    c.contrato_tipo            = _none_if_empty(data.get("contrato_tipo",            c.contrato_tipo))   or "avulso"
    c.contrato_valor           = _none_if_empty(data.get("contrato_valor",           c.contrato_valor))
    c.contrato_forma_pagamento = _none_if_empty(data.get("contrato_forma_pagamento", c.contrato_forma_pagamento))
    c.contrato_dia_pagamento   = _none_if_empty(data.get("contrato_dia_pagamento",   c.contrato_dia_pagamento))
    c.contrato_inicio          = _none_if_empty(data.get("contrato_inicio",          c.contrato_inicio))
    c.contrato_fim             = _none_if_empty(data.get("contrato_fim",             c.contrato_fim))
    c.contrato_status          = _none_if_empty(data.get("contrato_status",          c.contrato_status)) or "ativo"
    c.contrato_dias_semana     = _none_if_empty(data.get("contrato_dias_semana",     c.contrato_dias_semana))
    c.contrato_observacoes     = _none_if_empty(data.get("contrato_observacoes",     c.contrato_observacoes))
    c.contrato_modelo          = _none_if_empty(data.get("contrato_modelo",          c.contrato_modelo))
    c.recorrencia              = _none_if_empty(data.get("recorrencia",              c.recorrencia))

    # ── CEP / geolocalização ──────────────────────────────────────────────────
    novo_cep = data.get("cep", "")
    geo_msg  = None
    if novo_cep and novo_cep != c.cep:
        geo = _cep_para_coordenadas(novo_cep)
        if geo:
            c.cep = geo["cep"]; c.logradouro = geo["logradouro"]; c.bairro = geo["bairro"]
            c.municipio = geo["municipio"]; c.uf = geo["uf"]
            c.latitude = geo["lat"]; c.longitude = geo["lon"]
            geo_msg = "📍 Localização atualizada pelo CEP" if geo.get("lat") else "⚠️ CEP não geocodificado"
        else:
            geo_msg = "⚠️ CEP inválido"

    db.session.commit()
    return jsonify({"msg": "Cliente atualizado com sucesso", "geo_msg": geo_msg}), 200


@client_bp.route("/clients/<int:client_id>", methods=["DELETE"])
@jwt_required()
def delete_client(client_id):
    user = _get_user(get_jwt_identity())
    c    = _find_client(client_id, user)
    if not c:
        return jsonify({"msg": "Cliente não encontrado"}), 404
    db.session.delete(c)
    db.session.commit()
    return jsonify({"msg": "Cliente removido com sucesso"}), 200


@client_bp.route("/clients/<int:client_id>/set-location", methods=["POST"])
@jwt_required()
def set_client_location(client_id):
    user = _get_user(get_jwt_identity())
    if user.role not in ("admin", "financial"):
        return jsonify({"msg": "Sem permissão"}), 403
    c = _find_client(client_id, user)
    if not c:
        return jsonify({"msg": "Cliente não encontrado"}), 404
    data = request.get_json() or {}
    lat  = data.get("lat")
    lon  = data.get("lon")
    if lat is None or lon is None:
        return jsonify({"msg": "Latitude e longitude são obrigatórios"}), 400
    c.latitude  = float(lat)
    c.longitude = float(lon)
    db.session.commit()
    return jsonify({
        "msg":       "📍 Localização exata salva com sucesso!",
        "latitude":  c.latitude,
        "longitude": c.longitude,
        "client_id": client_id,
    }), 200


@client_bp.route("/clients/geocode-cep", methods=["POST"])
@jwt_required()
def geocode_cep():
    data = request.get_json() or {}
    geo  = _cep_para_coordenadas(data.get("cep", ""))
    if not geo:
        return jsonify({"msg": "CEP não encontrado"}), 404
    return jsonify({
        "cep":        geo["cep"],
        "logradouro": geo["logradouro"],
        "bairro":     geo["bairro"],
        "municipio":  geo["municipio"],
        "uf":         geo["uf"],
        "latitude":   geo["lat"],
        "longitude":  geo["lon"],
        "tem_gps":    geo["lat"] is not None,
    }), 200