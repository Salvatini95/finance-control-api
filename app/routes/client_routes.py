# app/routes/client_routes.py
"""
Rotas de Clientes — apenas HTTP.
Geocodificação CEP → lat/lon via ViaCEP + Nominatim (gratuito).
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Client, User
from datetime import date
import requests as http

client_bp = Blueprint("clients", __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user(user_id):
    return User.query.get(int(user_id))


def _find_client(client_id, user):
    if user.company_id:
        return Client.query.filter_by(id=client_id, company_id=user.company_id).first()
    return Client.query.filter_by(id=client_id, user_id=user.id).first()


def _cep_para_coordenadas(cep: str) -> dict:
    """
    Converte CEP em lat/lon usando ViaCEP + Nominatim (OpenStreetMap).
    Retorna dict com lat, lon, logradouro, bairro, municipio, uf.
    Retorna None se não encontrar.
    """
    cep_limpo = "".join(filter(str.isdigit, cep or ""))
    if len(cep_limpo) != 8:
        return None

    # 1. ViaCEP — busca endereço textual
    try:
        r = http.get(
            f"https://viacep.com.br/ws/{cep_limpo}/json/",
            timeout=5,
            headers={"User-Agent": "SVFinance/1.0"}
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

    # 2. Nominatim — converte endereço em coordenadas
    try:
        query = f"{logradouro}, {bairro}, {municipio}, {uf}, Brasil"
        r2    = http.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "br"},
            timeout=8,
            headers={"User-Agent": "SVFinance/1.0 (contato@svfinance.com.br)"}
        )
        resultados = r2.json()
        if not resultados:
            # Fallback: busca só pelo município
            r3 = http.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": f"{municipio}, {uf}, Brasil", "format": "json", "limit": 1, "countrycodes": "br"},
                timeout=8,
                headers={"User-Agent": "SVFinance/1.0 (contato@svfinance.com.br)"}
            )
            resultados = r3.json()

        if resultados:
            return {
                "lat":        float(resultados[0]["lat"]),
                "lon":        float(resultados[0]["lon"]),
                "logradouro": logradouro,
                "bairro":     bairro,
                "municipio":  municipio,
                "uf":         uf,
                "cep":        cep_limpo,
            }
    except Exception:
        pass

    # Retorna endereço sem coordenadas se Nominatim falhar
    return {
        "lat":        None,
        "lon":        None,
        "logradouro": logradouro,
        "bairro":     bairro,
        "municipio":  municipio,
        "uf":         uf,
        "cep":        cep_limpo,
    }


def _client_to_dict(c: Client, include_relations=False) -> dict:
    """Serializa Client para dict."""
    data = {
        "id":         c.id,
        "codigo":     c.codigo,
        "name":       c.name,
        "email":      c.email,
        "phone":      c.phone,
        "document":   c.document,
        "cnpj":       c.cnpj,
        "address":    c.address,
        "notes":      c.notes,
        "created_at": c.created_at,
        # Endereço
        "cep":        c.cep,
        "logradouro": c.logradouro,
        "numero":     c.numero,
        "bairro":     c.bairro,
        "municipio":  c.municipio,
        "uf":         c.uf,
        # GPS
        "latitude":   c.latitude,
        "longitude":  c.longitude,
        "tem_gps":    c.latitude is not None and c.longitude is not None,
        # Contrato
        "contrato_tipo":            c.contrato_tipo,
        "contrato_valor":           c.contrato_valor,
        "contrato_forma_pagamento": c.contrato_forma_pagamento,
        "contrato_dia_pagamento":   c.contrato_dia_pagamento,
        "contrato_inicio":          c.contrato_inicio,
        "contrato_fim":             c.contrato_fim,
        "contrato_status":          c.contrato_status,
        "contrato_dias_semana":     c.contrato_dias_semana,
        "contrato_observacoes":     c.contrato_observacoes,
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


@client_bp.route("/clients", methods=["POST"])
@jwt_required()
def create_client():
    user = _get_user(get_jwt_identity())
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    if not name:
        return jsonify({"msg": "Nome é obrigatório"}), 400

    # Geocodificação automática pelo CEP
    geo = _cep_para_coordenadas(data.get("cep", ""))

    c = Client(
        name       = name,
        codigo     = data.get("codigo",   "").strip() or None,
        email      = data.get("email",    "").strip() or None,
        phone      = data.get("phone",    "").strip() or None,
        document   = data.get("document", "").strip() or None,
        cnpj       = data.get("cnpj",     "").strip() or None,
        address    = data.get("address",  "").strip() or None,
        notes      = data.get("notes",    "").strip() or None,
        created_at = str(date.today()),
        user_id    = user.id,
        company_id = user.company_id,
        # Endereço
        cep        = geo["cep"]        if geo else data.get("cep"),
        logradouro = geo["logradouro"] if geo else data.get("logradouro"),
        bairro     = geo["bairro"]     if geo else data.get("bairro"),
        municipio  = geo["municipio"]  if geo else data.get("municipio"),
        uf         = geo["uf"]         if geo else data.get("uf"),
        numero     = data.get("numero"),
        latitude   = geo["lat"] if geo else None,
        longitude  = geo["lon"] if geo else None,
        # Contrato
        contrato_tipo            = data.get("contrato_tipo",            "avulso"),
        contrato_valor           = data.get("contrato_valor"),
        contrato_forma_pagamento = data.get("contrato_forma_pagamento"),
        contrato_dia_pagamento   = data.get("contrato_dia_pagamento"),
        contrato_inicio          = data.get("contrato_inicio"),
        contrato_fim             = data.get("contrato_fim"),
        contrato_status          = data.get("contrato_status",          "ativo"),
        contrato_dias_semana     = data.get("contrato_dias_semana"),
        contrato_observacoes     = data.get("contrato_observacoes"),
    )
    db.session.add(c)
    db.session.commit()

    return jsonify({
        "msg":      "Cliente criado com sucesso",
        "id":       c.id,
        "name":     c.name,
        "tem_gps":  c.latitude is not None,
        "geo_msg":  "📍 Localização salva automaticamente pelo CEP" if (geo and geo.get("lat")) else "⚠️ CEP não encontrado — localização não salva",
    }), 201


@client_bp.route("/clients/<int:client_id>", methods=["PUT"])
@jwt_required()
def update_client(client_id):
    user = _get_user(get_jwt_identity())
    c    = _find_client(client_id, user)
    if not c:
        return jsonify({"msg": "Cliente não encontrado"}), 404

    data = request.get_json() or {}

    c.name     = data.get("name",     c.name).strip()
    c.codigo   = data.get("codigo",   c.codigo)
    c.email    = data.get("email",    c.email)
    c.phone    = data.get("phone",    c.phone)
    c.document = data.get("document", c.document)
    c.cnpj     = data.get("cnpj",     c.cnpj)
    c.address  = data.get("address",  c.address)
    c.notes    = data.get("notes",    c.notes)
    c.numero   = data.get("numero",   c.numero)
    # Contrato
    c.contrato_tipo            = data.get("contrato_tipo",            c.contrato_tipo)
    c.contrato_valor           = data.get("contrato_valor",           c.contrato_valor)
    c.contrato_forma_pagamento = data.get("contrato_forma_pagamento", c.contrato_forma_pagamento)
    c.contrato_dia_pagamento   = data.get("contrato_dia_pagamento",   c.contrato_dia_pagamento)
    c.contrato_inicio          = data.get("contrato_inicio",          c.contrato_inicio)
    c.contrato_fim             = data.get("contrato_fim",             c.contrato_fim)
    c.contrato_status          = data.get("contrato_status",          c.contrato_status)
    c.contrato_dias_semana     = data.get("contrato_dias_semana",     c.contrato_dias_semana)
    c.contrato_observacoes     = data.get("contrato_observacoes",     c.contrato_observacoes)

    # Re-geocodifica se CEP mudou
    novo_cep = data.get("cep", "")
    if novo_cep and novo_cep != c.cep:
        geo = _cep_para_coordenadas(novo_cep)
        if geo:
            c.cep        = geo["cep"]
            c.logradouro = geo["logradouro"]
            c.bairro     = geo["bairro"]
            c.municipio  = geo["municipio"]
            c.uf         = geo["uf"]
            c.latitude   = geo["lat"]
            c.longitude  = geo["lon"]
            geo_msg = "📍 Localização atualizada pelo CEP" if geo.get("lat") else "⚠️ CEP não geocodificado"
        else:
            geo_msg = "⚠️ CEP inválido"
    else:
        geo_msg = None

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
def set_client_location(client_id: int):
    """
    Salva as coordenadas GPS exatas do cliente.
    ADM vai ao local físico e clica 'Usar minha localização' —
    isso salva o GPS real do celular, muito mais preciso que o CEP.
    """
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


# ── Geocodificação manual (frontend pode chamar ao digitar o CEP) ─────────────
@client_bp.route("/clients/geocode-cep", methods=["POST"])
@jwt_required()
def geocode_cep():
    """
    Endpoint auxiliar: recebe um CEP e retorna endereço + coordenadas.
    Usado pelo frontend para preencher o formulário automaticamente.
    """
    data = request.get_json() or {}
    cep  = data.get("cep", "")
    geo  = _cep_para_coordenadas(cep)

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
