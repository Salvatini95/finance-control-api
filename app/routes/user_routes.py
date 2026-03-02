from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

user_bp = Blueprint("users", __name__, url_prefix="/users")


@user_bp.route("/perfil", methods=["GET"])
@jwt_required()
def perfil():
    usuario = get_jwt_identity()

    return jsonify({
        "usuario_logado": usuario,
        "msg": "Perfil carregado com sucesso"
    }), 200