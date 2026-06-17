from app.extensions import db
from app.models import Client, CheckinPin


class ClientService:

    @staticmethod
    def delete(client: Client) -> dict:
        """Remove cliente se não houver registros vinculados.

        Verifica Order, Quote, ServiceCheckin, ServiceRecord e CheckinPin.
        Retorna 400 com lista de vínculos caso existam, para evitar IntegrityError
        não tratado na camada de rota.
        """
        vinculos = []
        if client.orders:
            n = len(client.orders)
            vinculos.append(f"{n} pedido(s)/OS")
        if client.quotes:
            n = len(client.quotes)
            vinculos.append(f"{n} orçamento(s)")
        if client.checkins:
            n = len(client.checkins)
            vinculos.append(f"{n} check-in(s)")
        if client.service_records:
            n = len(client.service_records)
            vinculos.append(f"{n} atendimento(s)")

        pins = CheckinPin.query.filter_by(client_id=client.id).count()
        if pins:
            vinculos.append(f"{pins} PIN(s) de check-in")

        if vinculos:
            return {
                "ok":      False,
                "msg":     (
                    f"Não é possível excluir: cliente possui "
                    f"{', '.join(vinculos)} vinculado(s). "
                    "Remova os vínculos antes de excluir."
                ),
                "vinculos": vinculos,
                "code":    400,
            }

        db.session.delete(client)
        db.session.commit()
        return {"ok": True, "msg": "Cliente removido com sucesso", "code": 200}
