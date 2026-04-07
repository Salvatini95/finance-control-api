# 💰 SV Finance Control — API

Backend do sistema de gestão financeira empresarial desenvolvido com Flask e PostgreSQL.

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791?logo=postgresql)
![JWT](https://img.shields.io/badge/Auth-JWT-orange)
![Supabase](https://img.shields.io/badge/Hosted-Supabase-3ECF8E?logo=supabase)

> 🔗 Frontend: [finance-control-web](https://github.com/Salvatini95/finance-control-web)

---

## ✨ Funcionalidades

- 🔐 Autenticação JWT com expiração de 8h
- 🏢 Multi-tenant — registro cria Company e User admin simultaneamente
- 👥 Gestão de usuários por empresa com roles
- 📊 Transações com origem (manual, venda, conta)
- 📄 Contas a pagar e receber
- 🧾 Orçamentos com fluxo completo de status
- 🛒 Vendas com conclusão automática: lança transação, baixa estoque e registra serviços
- 📦 Produtos e serviços com controle de estoque e estoque inicial automático
- 👤 Clientes com histórico
- 📈 Analytics financeiro

---

## 🛠️ Stack

| Tecnologia | Uso |
|---|---|
| Python + Flask | API REST |
| SQLAlchemy | ORM |
| Flask-Migrate | Migrações de banco |
| Flask-JWT-Extended | Autenticação com token |
| Flask-CORS | Liberação de origens |
| Werkzeug | Hash seguro de senhas |
| PostgreSQL via Supabase | Banco de dados |

---

## 📁 Estrutura
```
controle_financeiro/
├── .env
├── run.py
└── app/
├── init.py
├── extensions.py
├── models.py
└── routes/
├── auth_routes.py
├── company_routes.py
├── transaction_routes.py
├── bill_routes.py
├── product_routes.py
├── client_routes.py
├── order_routes.py
├── quote_routes.py
└── stock_routes.py
```
---

## 🚀 Como rodar localmente

### Pré-requisitos
- Python 3.10+
- PostgreSQL ou conta no Supabase

### Instalação
git clone https://github.com/Salvatini95/controle_financeiro.git
cd controle_financeiro
python -m venv .venv
Windows
.venv\Scripts\activate
pip install -r requirements.txt

### Configuração

Crie um arquivo .env na raiz:
DATABASE_URL=postgresql://usuario:senha@host:5432/postgres
JWT_SECRET_KEY=sua_chave_jwt_secreta
SECRET_KEY=sua_chave_secreta

### Execução
flask db upgrade
python run.py

API disponível em: http://127.0.0.1:5000

---

## 🔌 Principais Endpoints

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| POST | /api/register | Cria empresa e admin | ❌ |
| POST | /api/login | Login | ❌ |
| GET | /api/transactions | Listar transações | ✅ |
| POST | /api/transactions | Criar transação | ✅ |
| GET | /api/quotes | Listar orçamentos | ✅ |
| POST | /api/orders/from-quote/id | Criar venda de orçamento | ✅ |
| POST | /api/orders/id/complete | Concluir venda | ✅ |
| GET | /api/products | Listar produtos | ✅ |
| GET | /api/company/users | Listar usuários da empresa | ✅ Admin |
| POST | /api/company/users | Criar usuário na empresa | ✅ Admin |

---

## 🔒 Segurança

- Senhas com hash via Werkzeug
- Rotas protegidas com JWT
- Token com expiração de 8h
- Isolamento total de dados por company_id
- CORS configurado por origem

---

## 🗺️ Próximos passos

- [ ] Dashboard por role com dados filtrados por usuário
- [ ] Analytics por vendedor
- [ ] Sistema de planos (Free, Pro, Business)
- [ ] Deploy em produção (Railway)

---

## 👨‍💻 Autor

Desenvolvido por **Guilherme Salvatini**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-blue?logo=linkedin)](https://www.linkedin.com/in/guilherme-salvatini-623326361/)
[![GitHub](https://img.shields.io/badge/GitHub-black?logo=github)](https://github.com/Salvatini95)