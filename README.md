# svfinance-api

> Backend Flask do ecossistema **SV Finance** — serve todos os produtos da plataforma via API REST compartilhada com isolamento multi-tenant por `company_id`.

[![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Deploy](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)](https://render.com)
[![License](https://img.shields.io/badge/License-Proprietary-red)](./LICENSE)

---

## Sobre

O `svfinance-api` é o backend compartilhado do ecossistema SV Finance. Uma única API serve múltiplos produtos e clientes com isolamento completo por `company_id` em todas as queries.

**Produtos servidos por esta API:**

| Produto | URL | Descrição |
|---|---|---|
| SV App | `app.svfinance.com.br` | SaaS self-service para MEIs e pequenas empresas |
| Restaura Glass | `restauraglass.svfinance.com.br` | Implementação piloto SV Soluções |
| SV Soluções | Futuras implementações | ERPs customizados por nicho |

---

## Stack

| Tecnologia | Versão | Uso |
|---|---|---|
| Python | 3.13 | Runtime |
| Flask | 3.x | Framework web |
| SQLAlchemy | 2.x | ORM |
| Flask-Migrate (Alembic) | — | Migrations |
| Flask-JWT-Extended | — | Autenticação JWT (30 dias) |
| PostgreSQL | 16 | Banco de dados (Supabase) |
| Gunicorn | — | Servidor WSGI em produção |
| Resend | — | Email transacional |
| Asaas | — | Pagamentos (PIX + cartão) |
| Focus NF-e | — | Emissão de NF-e e NFS-e |

---

## Estrutura do projeto

```
svfinance-api/
├── app/
│   ├── __init__.py          # Factory: create_app()
│   ├── extensions.py        # Instâncias únicas: db, jwt, migrate
│   ├── models.py            # Todos os models SQLAlchemy
│   ├── crypto.py            # Fernet encrypt/decrypt
│   ├── routes/              # Blueprints HTTP (sem lógica de negócio)
│   │   ├── auth_routes.py
│   │   ├── billing_routes.py
│   │   ├── checkin_routes.py
│   │   ├── client_routes.py
│   │   ├── nfse_routes.py
│   │   └── ...
│   └── services/            # Lógica de negócio em classes POO
│       ├── asaas_service.py
│       ├── checkin_service.py
│       ├── nfse_service.py
│       └── pin_service.py
├── migrations/
│   └── versions/            # Alembic migrations (HEAD: billing_01)
├── org-ia/                  # Documentação operacional (sv-protocol)
│   ├── 00_blueprint.md      # Identidade e modelo de negócio
│   ├── 04_backlog.md        # Backlog priorizado
│   ├── 05_estado.md         # Estado da sessão corrente
│   ├── topologia.md         # Infraestrutura e deploy
│   └── policies/            # Gitflow, migrations, secrets
├── scripts/
│   ├── health-check.sh      # Retomada de sessão Claude Code
│   └── save-session.sh      # Encerramento de sessão Claude Code
├── CLAUDE.md                # Contexto operacional para agentes IA
├── .env.example             # Variáveis de ambiente necessárias
└── requirements.txt
```

---

## Configuração local

### Pré-requisitos

- Python 3.13+
- PostgreSQL (ou conta Supabase)
- pip

### Instalação

```bash
# 1. Clonar o repositório
git clone git@github.com:Svfinance/svfinance-api.git
cd svfinance-api

# 2. Criar e ativar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/macOS/WSL2
# venv\Scripts\activate   # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com seus valores

# 5. Aplicar migrations
flask db upgrade

# 6. Iniciar servidor de desenvolvimento
flask run
```

O servidor estará disponível em `http://localhost:5000`.

---

## Variáveis de ambiente

Crie um arquivo `.env` baseado no `.env.example`:

```env
DATABASE_URL=          # Supabase pooler (porta 6543)
JWT_SECRET_KEY=        # Chave secreta para JWT
SECRET_KEY=            # Chave secreta Flask
RESEND_API_KEY=        # API key do Resend (email)
DEV_MODE=True          # False em produção
APP_URL=               # URL do frontend principal
FOCUS_ENV=homologacao  # homologacao | producao
ASAAS_API_KEY=         # API key do Asaas
ASAAS_ENV=sandbox      # sandbox | producao
ANTHROPIC_API_KEY=     # Claude API (Brand Studio)
REMOVE_BG_API_KEY=     # Remove.bg API (Brand Studio)
```

---

## Migrations

```bash
# Ver migration HEAD atual
flask db heads

# Ver histórico completo
flask db history

# Criar nova migration
flask db migrate -m "descricao_01"

# Aplicar migrations pendentes
flask db upgrade

# Reverter última migration
flask db downgrade
```

**HEAD atual:** `billing_01`

**Regra obrigatória:** toda coluna `NOT NULL` nova deve ter `server_default`. Ver `org-ia/policies/gitflow_migration_secrets.md`.

---

## Padrões de código

### Service (lógica de negócio)

```python
class ExemploService:
    @staticmethod
    def fazer_algo(user: User, dados: dict) -> dict:
        """Docstring obrigatória."""
        return {"ok": True, "msg": "Sucesso.", "code": 200}
```

### Route (HTTP apenas)

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

### Multi-tenancy (obrigatório em toda query)

```python
items = Model.query.filter_by(company_id=user.company_id).all()
```

---

## Deploy

**Produção:** Render Web Service com deploy automático via push na `main`.

```
Start command: flask db upgrade && gunicorn "app:create_app()" --bind 0.0.0.0:$PORT
```

**URL de produção:** `https://api.svfinance.com.br`

---

## Trabalhando com agentes IA (Claude Code)

Este projeto usa o **sv-protocol v1.0** para desenvolvimento assistido por IA.

```bash
# Iniciar sessão
./scripts/health-check.sh
claude

# Encerrar sessão (após Claude Code atualizar 05_estado.md)
./scripts/save-session.sh
```

Ver `CLAUDE.md` para contexto completo e `org-ia/` para documentação operacional.

---

## Contribuindo

Este é um projeto proprietário. Para contribuir:

1. Leia o `CLAUDE.md` e `org-ia/00_blueprint.md`
2. Verifique o backlog em `org-ia/04_backlog.md`
3. Siga o padrão de commits em `org-ia/policies/gitflow_migration_secrets.md`
4. Todo commit deve ser assinado com GPG (`git commit -S`)
5. Conventional Commits obrigatório: `tipo(escopo): descrição em português`

---

## Licença

Proprietário — © 2026 SV Finance. Todos os direitos reservados.
