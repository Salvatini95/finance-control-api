# CLAUDE.md — svfinance-api
> Schema operacional sv-protocol v1.0. Regras transversais vivem em `~/.claude/CLAUDE.md` global.
> Este arquivo cobre APENAS o que é específico do backend Flask compartilhado.

---

## Projeto

- **Nome:** svfinance-api
- **Descrição:** Backend Flask compartilhado por todos os produtos SV Finance.
  Serve `app.svfinance.com.br` (SaaS genérico), `restauraglass.svfinance.com.br`
  (Restaura Glass) e futuros tenants SV Soluções. Multi-tenant por `company_id`.
- **sv-protocol:** v1.0
- **Repo:** github.com/Svfinance/svfinance-api
- **Branch principal:** `main`

---

## Atores

| Ator | Papel | Alias |
|---|---|---|
| Guilherme (Operador) | Owner · único commiter atual | `salvatiniguilherme@gmail.com` |
| Opus | Arquitetura, decisões, org-ia/ | `opus@svfinance.com.br` |
| Son Coder SV | Código, migrations, scripts (Fase 2) | `son-coder@svfinance.com.br` |

---

## Stack

- **Runtime:** Python 3.13 + Flask 3.x
- **ORM:** SQLAlchemy 2.x com Flask-SQLAlchemy
- **Migrations:** Flask-Migrate (Alembic) — arquivo único `models.py`
- **Auth:** Flask-JWT-Extended · JWT 30 dias · identity pode ser dict ou int
- **Banco:** PostgreSQL via Supabase · pooler porta 6543 · região sa-east-1
- **Email:** Resend (`noreply@svfinance.com.br`)
- **Servidor:** Gunicorn em produção
- **Criptografia:** Fernet (cryptography) para credenciais Wi-Fi
- **HTTP:** `requests>=2.31.0` — NUNCA fixar versão (conflito com resend)

**Decisões arquiteturais — não reabrir:**
- Multi-tenancy por `company_id` (nunca schemas separados)
- `models.py` único para todos os models (Alembic funciona bem assim)
- Flask sobre FastAPI/Django (custo de migração não justifica agora)
- Render sobre Railway (Railway deletado por billing — não voltar)
- Focus NF-e para NF-e de produto (PED-), eNotas/Nuvem Fiscal para NFS-e (OS-) — decisão firmada

---

## Topologia operacional

| Ambiente | URL | Observação |
|---|---|---|
| Produção | `https://api.svfinance.com.br/api` | Render Free · hiberna após 15min |
| Dev local | `http://localhost:5000/api` | PyCharm ou `flask run` |

**Render:**
- Start command: `flask db upgrade && gunicorn "app:create_app()" --bind 0.0.0.0:$PORT`
- UptimeRobot fazendo ping a cada 5min para evitar cold start
- Banco: Supabase Transaction Pooler (porta 6543)

**Variáveis de ambiente no Render (nomes — sem valores aqui):**
```
DATABASE_URL          # Supabase pooler URL
JWT_SECRET_KEY
SECRET_KEY
RESEND_API_KEY
DEV_MODE              # False em produção
APP_URL               # https://app.svfinance.com.br
FOCUS_ENV             # homologacao | producao
ASAAS_API_KEY
ASAAS_ENV             # sandbox | producao
ANTHROPIC_API_KEY     # Brand Studio
REMOVE_BG_API_KEY     # Brand Studio
```

**Consultar `org-ia/topologia.md` antes de qualquer ação em ambiente.**

---

## Estrutura do repositório

```
app/
  __init__.py           # create_app() — registra todos os blueprints
  extensions.py         # instâncias únicas: db, jwt, migrate
  crypto.py             # Fernet encrypt/decrypt (Wi-Fi)
  models.py             # TODOS os models — arquivo único (não separar)
  routes/               # SÓ HTTP — zero lógica de negócio aqui
    auth_routes.py
    client_routes.py
    order_routes.py
    checkin_routes.py
    quote_routes.py
    product_routes.py
    transaction_routes.py
    team_routes.py
    pin_routes.py
    import_routes.py
    limpeza_routes.py   # /api/limpeza — exclusivo Restaura Glass
    nfse_routes.py      # /api/nfse — Focus NF-e
    billing_routes.py   # /api/billing — Asaas
    bill_routes.py
    company_routes.py
    goal_routes.py
    dre_routes.py
    cashflow_routes.py
    sales_report_routes.py
    stock_routes.py
    commission_routes.py
    nfe_routes.py
    brand_routes.py
    dev_routes.py
  services/             # LÓGICA DE NEGÓCIO — classes POO
    checkin_service.py  ✅ POO
    nfse_service.py     ✅ POO
    asaas_service.py    ✅ POO
    pin_service.py      ✅ POO
    wifi_service.py     ⬜ pendente
migrations/
  versions/             # Alembic migrations
    # HEAD atual: billing_01
    # Cadeia: ... → nfse_order_fields_01 → client_fields_v2_01 → billing_01
scripts/
  health-check.sh       # retomada de sessão
  new-session.sh        # inicia nova sessão com contexto
org-ia/                 # documentação formal (fonte absoluta)
  00_blueprint.md
  04_backlog.md
  05_estado.md
  topologia.md
  stack.md
  policies/
    gitflow.md
    migration.md
    secrets.md
```

---

## Modelo de dados (alto nível)

**Multi-tenancy:** `company_id` em TODA tabela. Toda query filtra por `company_id`. Nunca schemas separados.

**Models principais:**

| Model | Tabela | Observação |
|---|---|---|
| Company | companies | Tenant. `plan`, `asaas_customer_id`, `trial_ends_at`, `token_focusnfe` |
| User | users | Roles: admin/seller/financial/stock/viewer/encarregado |
| Client | clients | GPS lat/lng, multi-contato JSON, `pin_cliente` (4 dígitos permanente) |
| Product | products | NCM, CFOP, CST, SKU, estoque |
| Order | orders | PED/OS prefixo automático. `nfe_ref`, `nfe_chave`, `nfe_status` |
| Quote | quotes | Orçamento → conversão para Order |
| Transaction | transactions | Entrada/saída financeira |
| Bill | bills | Contas a pagar/receber |
| StockMovement | stock_movements | Movimentação de estoque |
| ServiceCheckin | service_checkins | Check-in QR + GPS Haversine 300m. `local_id` idempotência offline |
| CheckinPin | checkin_pins | PIN 6 dígitos temporário (5min) para check-in sem GPS |
| LimpezaServiceCard | limpeza_service_cards | Cartão mensal — exclusivo Restaura Glass |
| LimpezaOccurrence | limpeza_occurrences | 4 tipos: fechou/remarcou/nao_compareceu/mudou_ponto |
| Subscription | subscriptions | Asaas. Status: trial/active/overdue/canceled. `founder=True` trava preço |
| Goal | goals | Metas financeiras |
| ImportLog | import_logs | Histórico de importações CSV |
| CommissionRule | commission_rules | 3 modos: % total, % lucro, valor fixo |
| BrandProject | brand_projects | Brand Studio |
| BrandAsset | brand_assets | Assets do Brand Studio |

**Migration HEAD atual:** `billing_01`

---

## Padrões de código

**Padrão de service (POO obrigatório para código novo):**
```python
class ExemploService:
    @staticmethod
    def fazer_algo(user: User, dados: dict) -> dict:
        """Docstring obrigatória."""
        # lógica de negócio aqui
        return {"ok": True, "msg": "...", "code": 200}
```

**Padrão de route:**
```python
@bp.route("/rota", methods=["POST"])
@jwt_required()
def endpoint():
    user   = User.query.get(int(get_jwt_identity()))
    data   = request.get_json() or {}
    result = ExemploService.fazer_algo(user=user, dados=data)
    code   = result.pop("code", 200)
    return jsonify(result), code
```

**Retorno padrão:** `{"ok": bool, "msg": str, "code": int, ...dados_extras}`
**Try/except:** sempre na route, nunca no service.
**Logging:** não implementado formalmente — não introduzir sem decisão arquitetural.

**Padrão de migration:**
```python
revision      = "nome_01"
down_revision = "billing_01"   # SEMPRE verificar HEAD antes: flask db heads
```

---

## Armadilhas conhecidas (não repetir)

```python
# SEMPRE server_default em coluna NOT NULL nova
Column(String, nullable=False, server_default="valor_default")

# NUNCA fixar versão do requests
requests>=2.31.0  # correto — nunca requests==2.x.x

# NUNCA backref com múltiplos FKs — usar back_populates
client_rel = db.relationship("Client", back_populates="checkins", foreign_keys=[client_id])

# SEMPRE filtrar company_id
Model.query.filter_by(company_id=user.company_id)

# ANTES de commitar migration: verificar heads
flask db heads   # deve retornar apenas 1 head
flask db history # confirmar cadeia correta
```

**Migrations problemáticas já resolvidas (histórico):**
- `nfse_order_fields_01`: `down_revision` errado, corrigido manualmente
- `billing_01`: apontava para head errado, corrigido via find-and-replace no PyCharm

---

## Clientes ativos

| Cliente | company_id | Login | Subdomínio |
|---|---|---|---|
| Restaura Glass | 20 | blindex_limp@hotmail.com | restauraglass.svfinance.com.br |
| SV Dev (testes) | 17 | guilhermesalvatini8@gmail.com | app.svfinance.com.br |

**Focus NF-e (Restaura Glass — sandbox):**
```
CNPJ: 11245238000101
IBGE Maringá: 4115200
Regime: 1 (Simples Nacional)
Codes NFS-e: 1407 (limpeza), 1405 (restauração)
Token: não commitar — manter apenas no banco via SQL ou env
SQL: UPDATE companies SET token_focusnfe='TOKEN' WHERE id=20;
```

---

## Ordem de leitura na retomada de sessão

1. `./scripts/health-check.sh`
2. `org-ia/05_estado.md` — sessão corrente
3. `org-ia/04_backlog.md` — tarefa ativa
4. `git log --oneline -5` + `git diff --stat`
5. `org-ia/topologia.md` — antes de qualquer ação em ambiente

---

## Boundaries com outros projetos

- **svfinance-app:** consome este backend via `https://api.svfinance.com.br/api`
- **svfinance-rg:** consome o mesmo backend — diferenciado por `company_id` no banco e hostname no frontend
- **svfinance-landing:** HTML estático — não consome o backend diretamente
- **Frontends:** sem compartilhamento de código entre si (não é monorepo)
- **Banco:** único PostgreSQL Supabase — todos os tenants no mesmo schema, isolados por `company_id`

**Fora do escopo deste repo:**
- Qualquer código de UI ou frontend
- Lógica de tema/theming (é responsabilidade dos frontends)
- App mobile React Native (adiado sem data)
- FastAPI / Django (descartados — não reabrir)
