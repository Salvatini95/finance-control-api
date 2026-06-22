from app.extensions import db
from app.models import Order, StockMovement, ServiceRecord, ServiceCheckin, Transaction


class OrderService:

    @staticmethod
    def delete(order: Order) -> dict:
        """Remove order se não houver registros vinculados com FK sem cascade.

        Verifica StockMovement, ServiceRecord e ServiceCheckin.
        Transaction é deletada junto (já tratada pelo próprio código de exclusão).
        Retorna 400 com lista de vínculos se existirem, para evitar IntegrityError.
        """
        vinculos = []

        mov = StockMovement.query.filter_by(order_id=order.id).count()
        if mov:
            vinculos.append(f"{mov} movimentação(ões) de estoque")

        rec = ServiceRecord.query.filter_by(order_id=order.id).count()
        if rec:
            vinculos.append(f"{rec} registro(s) de atendimento")

        chk = ServiceCheckin.query.filter_by(order_id=order.id).count()
        if chk:
            vinculos.append(f"{chk} check-in(s)")

        if vinculos:
            return {
                "ok":      False,
                "msg":     (
                    f"Não é possível excluir: ordem possui "
                    f"{', '.join(vinculos)} vinculado(s). "
                    "Remova os vínculos antes de excluir."
                ),
                "vinculos": vinculos,
                "code":    400,
            }

        # nulla o FK antes de deletar a transaction (FK fk_order_transaction aponta de orders→transactions)
        if order.transaction_id:
            t = Transaction.query.get(order.transaction_id)
            order.transaction_id = None
            db.session.flush()
            if t:
                db.session.delete(t)

        db.session.delete(order)
        db.session.commit()
        return {"ok": True, "msg": "Venda removida com sucesso", "code": 200}
