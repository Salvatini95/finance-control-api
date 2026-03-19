# 💰 Controle Financeiro

Sistema fullstack de controle financeiro pessoal desenvolvido com Flask e React.

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![JWT](https://img.shields.io/badge/Auth-JWT-orange)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey?logo=sqlite)

---

## 📸 Telas

> Dashboard, Analytics e tela de Transações

<!-- Adicione prints aqui depois -->

---

## ✨ Funcionalidades

- 🔐 Autenticação JWT (login e cadastro de usuários)
- 📊 Dashboard com gráficos de saldo acumulado, categorias e entradas vs saídas
- 📋 CRUD completo de transações (criar, listar, editar, deletar)
- 👥 Multi usuários com senhas criptografadas (hash bcrypt)
- 📱 Interface responsiva com Tailwind CSS

---

## 🛠️ Stack

### Backend
| Tecnologia | Uso |
|---|---|
| Python + Flask | API REST |
| SQLAlchemy | ORM / banco de dados |
| Flask-JWT-Extended | Autenticação com token |
| Werkzeug | Hash seguro de senhas |
| SQLite | Banco de dados (desenvolvimento) |

### Frontend
| Tecnologia | Uso |
|---|---|
| React 18 | Interface |
| React Router DOM | Navegação entre páginas |
| Recharts | Gráficos interativos |
| Tailwind CSS | Estilização |

---

## 📁 Estrutura do Projeto
```
controle-financeiro/
├── backend/
│   ├── app/
│   │   ├── models.py        # User e Transaction
│   │   ├── extensions.py    # SQLAlchemy, JWT
│   │   └── __init__.py      # Inicialização do Flask
│   ├── routes/
│   │   ├── auth_routes.py   # Login e registro
│   │   ├── transaction_routes.py
│   │   ├── category_routes.py
│   │   └── user_routes.py
│   └── run.py
│
└── frontend/
    └── src/
        ├── components/
        │   ├── charts/      # BalanceChart, CategoryChart, MonthlyChart
        │   ├── layout/      # Sidebar
        │   └── transactions/
        ├── pages/
        │   ├── Dashboard.jsx
        │   ├── Analytics.jsx
        │   └── Login.jsx
        └── services/
            └── api.js
```

---

## 🚀 Como rodar localmente

### Pré-requisitos
- Python 3.10+
- Node.js 18+

### Backend
```bash
# Entre na pasta do backend
cd backend

# Crie o ambiente virtual
python -m venv .venv

# Ative o ambiente virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Instale as dependências
pip install -r requirements.txt

# Rode o servidor
python run.py
```

> API disponível em: `http://127.0.0.1:5000`

### Frontend
```bash
# Entre na pasta do frontend
cd frontend

# Instale as dependências
npm install

# Rode o projeto
npm run dev
```

> Frontend disponível em: `http://localhost:5173`

---

## 🔌 Endpoints da API

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| POST | `/api/register` | Cadastro de usuário | ❌ |
| POST | `/api/login` | Login | ❌ |
| GET | `/api/transactions` | Listar transações | ✅ |
| POST | `/api/transactions` | Criar transação | ✅ |
| PUT | `/api/transactions/<id>` | Atualizar transação | ✅ |
| DELETE | `/api/transactions/<id>` | Deletar transação | ✅ |

---

## 🔒 Segurança

- Senhas armazenadas com hash (Werkzeug/bcrypt)
- Rotas protegidas com JWT
- Token salvo no localStorage com expiração
- Validação de dados no backend

---

## 🗺️ Próximos passos

- [ ] Página de transações estilo planilha
- [ ] Filtros por data e categoria
- [ ] Cadastro de clientes
- [ ] Relatórios em PDF
- [ ] Deploy em produção (Railway + Vercel)
- [ ] Controle de estoque

---

## 👨‍💻 Autor

Desenvolvido por **Guilherme Salvatini**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-blue?logo=linkedin)](https://www.linkedin.com/in/guilherme-salvatini-623326361/)
[![GitHub](https://img.shields.io/badge/GitHub-black?logo=github)](https://github.com/Salvatini95)