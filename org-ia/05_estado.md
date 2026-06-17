# 05_estado.md — svfinance-api
> Estado da sessão corrente. Atualizado por Opus no início e fim de cada sessão.
> Son Coder não toca este arquivo.

---

## Sessão atual

**Data:** 17/06/2026
**Repo foco:** svfinance-api
**Tarefa ativa:** Bug DELETE /clients/id RESOLVIDO. Próxima: B-02 (NfseButton.jsx) ou validação webhook real Asaas
**Modelo/effort:** SonCoder/medium (bug de exclusão de cliente — concluído)

---

## Estado no início desta sessão (17/06)

**Migration HEAD:** `pin_cliente_add_01` (sem alteração)
**Branch:** `main`
**Último commit ao iniciar:** `135b6e1` — docs(org-ia): registra conclusao do B-01 e novo bug DELETE clients

---

## O que foi feito nesta sessão — Bug DELETE /clients RESOLVIDO ✅

### Bug DELETE /clients/\<id\> → 500 corrigido

**Causa raiz confirmada:** `DELETE /clients/<id>` não tinha `try/except`. Postgres lançava
`IntegrityError` (FK constraint) ao tentar deletar cliente com registros vinculados — sem
captura, virava 500 genérico.

**5 models com FK → `clients.id` identificados, nenhum com cascade:**

| Model | FK name |
|---|---|
| `Quote` | `fk_quo_client` |
| `Order` | FK linha 349 de models.py |
| `ServiceRecord` | `fk_svcrecord_client` |
| `ServiceCheckin` | `fk_checkin_client` |
| `CheckinPin` | `fk_pin_client` |

**Fix implementado:**

- **`app/services/client_service.py`** — arquivo novo. `ClientService.delete()` verifica
  vínculos em todos os 5 models antes de deletar. Se houver vínculo, retorna
  `{"ok": False, "code": 400, "msg": "...", "vinculos": [...]}`. Se não houver, deleta e
  retorna `{"ok": True, "code": 200}`.
- **`app/routes/client_routes.py`** — só a função `delete_client()` alterada: adicionado
  import de `ClientService` + `try/except` (rollback + 500 amigável em erro inesperado).
  Restante do arquivo legado intocado.

**Estratégia adotada:** bloqueio com 400 (não cascade delete, não soft delete). Preserva
histórico de Orders/Checkins, sem migration, implementação cirúrgica. Soft delete
continua como opção futura se necessário.

**Validação — testes mockados (3 casos):**
- Cliente com orders → 400 ✓
- Cliente com quotes + checkins + PINs → 400 com lista de vínculos ✓
- Cliente sem vínculos → 200, `db.session.delete` e `commit` chamados ✓

**Validação — banco real Supabase (produção):**
- Cliente de teste id=61 com `order=91` + `checkin=36` vinculados → **HTTP 400** ✓
- Mesmos vínculos removidos, DELETE repetido → **HTTP 200**, registro deletado ✓
- Cleanup confirmado: `client=61`, `order=91`, `checkin=36` — todos `None` no banco ✓

**Commit:** `7d2c5fa` — `fix(clients): trata FK constraint ao excluir cliente com vínculos`
**Branch:** `main`, já no GitHub (Svfinance/svfinance-api)

---

## Estado ao fim desta sessão

**Migration HEAD:** `pin_cliente_add_01` (sem alteração)
**Último commit:** `7d2c5fa` — fix(clients): trata FK constraint ao excluir cliente com vínculos
**O que ficou pendente:**
- Validação opcional do webhook real do Asaas (ver histórico abaixo — não bloqueante)
- B-02 (NfseButton.jsx) — próxima tarefa de feature

**Próxima tarefa recomendada:** B-02 (NfseButton.jsx) ou validação webhook real Asaas.

---

## Decisões tomadas nesta sessão

| Decisão | Alternativa descartada | Motivo |
|---|---|---|
| Bloqueio com 400 ao excluir cliente com vínculos | Cascade delete / Soft delete | Preserva histórico de Orders sem migration; soft delete é decisão de schema maior, fica como opção futura |
| `ClientService.delete()` em service novo | Lógica direto na route | Aproveita oportunidade de tirar débito técnico da rota legada, sem reescrever o restante do arquivo |

---

## Histórico — sessão 16/06 (B-01 Asaas billing)

Testado fluxo completo do Asaas sandbox via `scripts/test_billing_sandbox.sh` contra Render
(`ASAAS_ENV=sandbox`). 4 bugs corrigidos: `ASAAS_ENV=PRODUCTION` no Render (errado),
status PIX marcado como `active` antes do webhook (corrigido para `pending`), endpoint de
cancelamento errado (`POST /cancel` → `DELETE /subscriptions/{id}`), CPF/celular inválidos
no script de teste. Commits `652efd0`, `87de7d4`, `1aaac8b`.

**Pendente (não bloqueante):** confirmar no painel `sandbox.asaas.com` que a URL do webhook
`https://api.svfinance.com.br/api/billing/webhook` está cadastrada — testamos só com curl
direto, não com webhook real disparado pelo Asaas.
