from flask_marshmallow import Marshmallow
from marshmallow import fields, validate

ma = Marshmallow()


class ClienteSchema(ma.Schema):
    id = fields.Integer(dump_only=True)

    nome = fields.String(
        required=True,
        validate=validate.Length(min=3, error="Nome deve ter pelo menos 3 caracteres")
    )

    telefone = fields.String(
        required=True,
        validate=validate.Length(min=8, error="Telefone inválido")
    )


cliente_schema = ClienteSchema()
clientes_schema = ClienteSchema(many=True)
