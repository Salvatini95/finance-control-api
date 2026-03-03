# 💰 Finance Control API

API REST desenvolvida com Flask para controle financeiro pessoal de usuários, com autenticação JWT e gerenciamento de transações.

---

## 📌 Objetivo do Projeto

Este projeto foi desenvolvido com o objetivo de praticar conceitos fundamentais de desenvolvimento backend, incluindo:

- Arquitetura modular
- Autenticação com JWT
- Organização por camadas
- Boas práticas com Flask
- ORM com SQLAlchemy
- Serialização com Marshmallow

A API permite que usuários autenticados gerenciem suas próprias transações financeiras (receitas e despesas).

---

## 🚀 Tecnologias Utilizadas

- Python 3.13
- Flask
- Flask-JWT-Extended
- Flask-SQLAlchemy
- Marshmallow
- SQLite

---

## 🔐 Autenticação

A API utiliza autenticação baseada em **JWT (JSON Web Token)**.

### 🔄 Fluxo de autenticação:

1. Usuário se registra
2. Realiza login
3. Recebe um token JWT
4. Envia o token no header:


Authorization: Bearer <seu_token>


5. Acessa rotas protegidas

---

## 📡 Principais Endpoints

### 🔑 Autenticação

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | /auth/register | Registrar novo usuário |
| POST | /auth/login | Login e geração de token |

---

### 💳 Transações

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | /transactions | Criar nova transação |
| GET | /transactions | Listar transações do usuário autenticado |

---

## 🗂 Estrutura do Projeto

```
controle_financeiro/
│
├── app/
│   ├── routes/
│   │   ├── auth_routes.py
│   │   ├── transaction_routes.py
│   │   └── user_routes.py
│   │
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   └── __init__.py
│
├── instance/
├── run.py
├── requirements.txt
└── README.md
```
---

## ▶️ Como Rodar o Projeto

### 1️⃣ Clonar repositório

```bash
git clone https://github.com/Salvatini95/finance-control-api.git
cd controle_financeiro
2️⃣ Criar ambiente virtual
python -m venv .venv
3️⃣ Ativar ambiente virtual

Windows:

.venv\Scripts\activate

Mac/Linux:

source .venv/bin/activate
4️⃣ Instalar dependências
pip install -r requirements.txt
5️⃣ Rodar servidor
python run.py

Servidor disponível em:

http://127.0.0.1:5000
🧠 Conceitos Aplicados

Arquitetura modular

Separação de responsabilidades

Proteção de rotas

Autenticação stateless

Modelagem de banco com SQLAlchemy

Serialização e validação com Marshmallow

Organização por Blueprints

🔮 Próximas Melhorias

Atualizar e deletar transações

Deploy em produção (Render ou Railway)

Frontend em React consumindo a API

Documentação Swagger

Testes automatizados

👨‍💻 Autor

Desenvolvido por Guilherme Salvatini

🔗 GitHub: https://github.com/Salvatini95