# SV Finance Control — Backend

> API REST para o SaaS de controle financeiro SV Finance Control.  
> Desenvolvido com Flask + SQLAlchemy + PostgreSQL, hospedado no Railway.

---

## 🚀 Stack

- **Python 3.13** + Flask
- **SQLAlchemy** + Flask-Migrate — ORM e migrações
- **Flask-JWT-Extended** — autenticação com JWT
- **psycopg2** — driver PostgreSQL
- **Resend** — envio de emails transacionais
- **Gunicorn** — servidor WSGI em produção
- **Railway** — deploy automático via GitHub
- **Supabase** — PostgreSQL hospedado (região São Paulo)

---

## 🌐 URLs

| Ambiente | URL                                                       |
|----------|-----------------------------------------------------------|
| Produção | https://finance-control-api-production.up.railway.app/api |
| Banco    | Supabase PostgreSQL — região São Paulo                    |

---

## 📁 Estrutura do Projeto
```
controle_financeiro/
├── app/
│   ├── init.py           # Factory pattern + registro de blueprints
│   ├── extensions.py         # db, jwt, migrate
│   ├── models.py             # Todos os models SQLAlchemy
│   ├── email_service.py      # Integração Resend (verificação + reset)
│   └── routes/
│       ├── auth_routes.py        # Login, cadastro, verificação, reset senha
│       ├── transaction_routes.py # CRUD transações
│       ├── bill_routes.py        # CRUD contas a pagar/receber
│       ├── product_routes.py     # CRUD produtos + SKU + estoque inicial
│       ├── quote_routes.py       # CRUD orçamentos
│       ├── order_routes.py       # CRUD vendas (PED/OS automático)
│       ├── stock_routes.py       # Movimentações de estoque
│       ├── client_routes.py      # CRUD clientes
│       ├── goal_routes.py        # CRUD metas financeiras
│       └── company_routes.py     # Dados da empresa + equipe
├── migrations/               # Flask-Migrate (Alembic)
│   └── versions/
├── .env                      # Variáveis de ambiente (não commitar)
├── requirements.txt
├── Procfile                  # Comando de start no Railway
└── wsgi.py
```
---

## 🗄️ Models Principais

| Model         | Descrição                                      |
|---------------|------------------------------------------------|
| Company       | Empresa (multi-tenant)                         |
| User          | Usuário com roles e verificação de email       |
| Transaction   | Receitas e despesas                            |
| Bill          | Contas a pagar e a receber                     |
| Product       | Produtos e serviços com SKU e estoque          |
| Quote         | Orçamentos com itens em JSON                   |
| Order         | Vendas (PED/OS) com baixa automática de estoque|
| StockMovement | Histórico de movimentações de estoque          |
| ServiceRecord | Registro de serviços prestados                 |
| Goal          | Metas financeiras (conta pessoal)              |

---

## 🔐 Autenticação

- JWT com expiração de **8 horas**
- Verificação de email obrigatória no cadastro
- Recuperação de senha via link temporário
- Emails enviados via **Resend**

---

## ⚙️ Variáveis de Ambiente

```env
SECRET_KEY=sua_secret_key
JWT_SECRET_KEY=sua_jwt_secret_key
DATABASE_URL=postgresql://user:password@host:port/database
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
FROM_EMAIL=onboarding@resend.dev
APP_URL=https://finance-control-web-five.vercel.app
```

---

## 🛠️ Rodando Localmente

```bash
# Criar e ativar ambiente virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Instalar dependências
pip install -r requirements.txt

# Rodar servidor
flask run --host=0.0.0.0 --port=5000
```

---

## 🗃️ Migrações

```bash
# Criar nova migração
flask db migrate -m "descrição"

# ⚠️ IMPORTANTE: verificar colunas NOT NULL sem server_default antes de aplicar

# Aplicar migração
flask db upgrade
```

> **Atenção:** Flask-Migrate gera migrações com `NOT NULL` sem `server_default`.  
> Sempre verifique e corrija manualmente antes de rodar `flask db upgrade`.

---

## 🚀 Deploy (Railway)

**Start Command:**
flask db upgrade && gunicorn "app:create_app()" --bind 0.0.0.0:$PORT

O deploy é automático via **GitHub + Railway**.  
Qualquer push na branch `main` dispara um novo deploy com migração automática.

---

## 📡 Principais Endpoints

### Auth
| Método | Rota                    | Descrição                    |
|--------|-------------------------|------------------------------|
| POST   | /api/register           | Cadastro empresarial (PJ)    |
| POST   | /api/register/personal  | Cadastro pessoal (PF)        |
| POST   | /api/login              | Login com JWT                |
| GET    | /api/verify-email       | Verificar email              |
| POST   | /api/forgot-password    | Solicitar reset de senha     |
| POST   | /api/reset-password     | Redefinir senha              |
| GET    | /api/me                 | Perfil do usuário logado     |

### Financeiro
| Método        | Rota                          | Descrição               |
|---------------|-------------------------------|-------------------------|
| GET/POST      | /api/transactions             | Transações              |
| GET/POST      | /api/bills                    | Contas                  |
| GET/POST      | /api/goals                    | Metas financeiras       |
| PATCH         | /api/goals/:id/deposit        | Depositar na meta       |

### Empresa
| Método        | Rota                          | Descrição               |
|---------------|-------------------------------|-------------------------|
| GET/POST      | /api/products                 | Produtos e serviços     |
| GET/POST      | /api/clients                  | Clientes                |
| GET/POST      | /api/quotes                   | Orçamentos              |
| GET/POST      | /api/orders                   | Vendas                  |
| POST          | /api/orders/:id/complete      | Concluir venda          |
| POST          | /api/orders/from-quote/:id    | Venda a partir de ORC   |
| GET/POST      | /api/stock/:id/movements      | Movimentações estoque   |

---

## 📦 Funcionalidades Principais

- ✅ Multi-tenant com isolamento por `company_id`
- ✅ Roles: admin, financial, stock, seller, viewer
- ✅ Verificação de email + reset de senha (Resend)
- ✅ Prefixo automático PED vs OS nas vendas
- ✅ Baixa automática de estoque ao concluir venda
- ✅ Custo médio ponderado no estoque
- ✅ Registro automático de serviços prestados
- ✅ Metas financeiras com depósito e auto-conclusão
- ✅ Migrações versionadas com Alembic

---

## 👨‍💻 Desenvolvido por

**Guilherme Salvatini**  
[github.com/Salvatini95](https://github.com/Salvatini95)
