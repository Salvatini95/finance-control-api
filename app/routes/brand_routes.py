from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import User
import os, json, io, base64, requests as req
from datetime import date

brand_bp = Blueprint("brand", __name__)

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def _user():
    return User.query.get(int(get_jwt_identity()))


# =========================
# AI COPY
# =========================
@brand_bp.route("/brand-studio/ai-copy", methods=["POST"])
@jwt_required()
def ai_copy():
    data   = request.get_json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"msg": "Prompt é obrigatório"}), 400

    if not ANTHROPIC_KEY:
        return jsonify({"msg": "ANTHROPIC_API_KEY não configurada no Railway"}), 500

    try:
        res = req.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model":      "claude-sonnet-4-20250514",
                "max_tokens": 512,
                "system": (
                    "Você é um copywriter especialista em marketing para SaaS financeiro brasileiro. "
                    "Gere textos curtos e impactantes para posts em redes sociais do SV Finance Control, "
                    "um sistema de gestão financeira para MEIs e pequenas empresas. "
                    'Responda APENAS em JSON válido, sem markdown: {"title":"(max 8 palavras)","subtitle":"(max 12 palavras)","cta":"(max 5 palavras)"}'
                ),
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp_data = res.json()
        text      = "".join(b.get("text","") for b in resp_data.get("content",[]))
        clean     = text.replace("```json","").replace("```","").strip()
        parsed    = json.loads(clean)
        return jsonify(parsed), 200
    except json.JSONDecodeError:
        return jsonify({"msg": "IA retornou formato inválido"}), 500
    except Exception as e:
        return jsonify({"msg": f"Erro na API Anthropic: {str(e)}"}), 500


# =========================
# REMOVER FUNDO (rembg)
# =========================
@brand_bp.route("/brand-studio/remove-bg", methods=["POST"])
@jwt_required()
def remove_bg():
    if "image" not in request.files:
        return jsonify({"msg": "Nenhuma imagem enviada"}), 400

    file = request.files["image"]
    img_bytes = file.read()

    try:
        from rembg import remove
        result = remove(img_bytes)
        return send_file(
            io.BytesIO(result),
            mimetype="image/png",
            as_attachment=False,
            download_name="removed_bg.png",
        )
    except ImportError:
        return jsonify({"msg": "rembg não instalado. Adicione 'rembg' ao requirements.txt"}), 500
    except Exception as e:
        return jsonify({"msg": f"Erro ao remover fundo: {str(e)}"}), 500


# =========================
# PROJETOS
# =========================
@brand_bp.route("/brand-studio/projects", methods=["GET"])
@jwt_required()
def list_projects():
    user = _user()
    from app.models import BrandProject
    projects = BrandProject.query.filter_by(company_id=user.company_id).order_by(BrandProject.id.desc()).all()
    return jsonify([{
        "id":          p.id,
        "name":        p.name,
        "format":      p.format,
        "canvas_data": p.canvas_data,
        "created_at":  p.created_at,
    } for p in projects]), 200


@brand_bp.route("/brand-studio/projects", methods=["POST"])
@jwt_required()
def create_project():
    user = _user()
    data = request.get_json()
    from app.models import BrandProject
    proj = BrandProject(
        name        = data.get("name", "Sem nome"),
        canvas_data = data.get("canvas_data", "{}"),
        format      = data.get("format", "insta_post"),
        company_id  = user.company_id,
        user_id     = user.id,
        created_at  = str(date.today()),
    )
    db.session.add(proj)
    db.session.commit()
    return jsonify({"msg": "Projeto salvo!", "id": proj.id}), 201


@brand_bp.route("/brand-studio/projects/<int:pid>", methods=["GET"])
@jwt_required()
def get_project(pid):
    user = _user()
    from app.models import BrandProject
    proj = BrandProject.query.filter_by(id=pid, company_id=user.company_id).first()
    if not proj:
        return jsonify({"msg": "Projeto não encontrado"}), 404
    return jsonify({
        "id":          proj.id,
        "name":        proj.name,
        "format":      proj.format,
        "canvas_data": proj.canvas_data,
        "created_at":  proj.created_at,
    }), 200


@brand_bp.route("/brand-studio/projects/<int:pid>", methods=["DELETE"])
@jwt_required()
def delete_project(pid):
    user = _user()
    from app.models import BrandProject
    proj = BrandProject.query.filter_by(id=pid, company_id=user.company_id).first()
    if not proj:
        return jsonify({"msg": "Projeto não encontrado"}), 404
    db.session.delete(proj)
    db.session.commit()
    return jsonify({"msg": "Projeto removido"}), 200


# =========================
# ASSETS
# =========================
@brand_bp.route("/brand-studio/assets", methods=["GET"])
@jwt_required()
def list_assets():
    user = _user()
    from app.models import BrandAsset
    assets = BrandAsset.query.filter_by(company_id=user.company_id).order_by(BrandAsset.id.desc()).all()
    return jsonify([{
        "id":       a.id,
        "filename": a.filename,
        "url":      a.url,
    } for a in assets]), 200


@brand_bp.route("/brand-studio/assets", methods=["POST"])
@jwt_required()
def upload_asset():
    user = _user()
    if "file" not in request.files:
        return jsonify({"msg": "Nenhum arquivo enviado"}), 400

    file      = request.files["file"]
    img_bytes = file.read()

    # Salva como base64 data URL para simplicidade (sem storage externo)
    mime      = file.mimetype or "image/png"
    b64       = base64.b64encode(img_bytes).decode("utf-8")
    data_url  = f"data:{mime};base64,{b64}"

    from app.models import BrandAsset
    asset = BrandAsset(
        filename   = file.filename,
        url        = data_url,
        company_id = user.company_id,
        user_id    = user.id,
        created_at = str(date.today()),
    )
    db.session.add(asset)
    db.session.commit()
    return jsonify({"msg": "Asset salvo!", "id": asset.id}), 201


@brand_bp.route("/brand-studio/assets/<int:aid>", methods=["DELETE"])
@jwt_required()
def delete_asset(aid):
    user = _user()
    from app.models import BrandAsset
    asset = BrandAsset.query.filter_by(id=aid, company_id=user.company_id).first()
    if not asset:
        return jsonify({"msg": "Asset não encontrado"}), 404
    db.session.delete(asset)
    db.session.commit()
    return jsonify({"msg": "Asset removido"}), 200