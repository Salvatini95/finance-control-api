# topologia.md — SV Finance
> Consultar ANTES de qualquer ação em ambiente (regra anti-miopia global).
> Atualizado por Opus apenas.

---

## Ambientes

| Produto | Frontend | Backend | Banco |
|---|---|---|---|
| app.svfinance.com.br | Vercel (svfinance-app) | api.svfinance.com.br (Render) | Supabase sa-east-1 |
| restauraglass.svfinance.com.br | Vercel (svfinance-rg) | api.svfinance.com.br (Render) | Supabase sa-east-1 |
| svfinance.com.br | Vercel (svfinance-landing) | — (HTML estático) | — |
| localhost:5173 | Vite dev server | localhost:5000 | Supabase (pooler) |

**Não existe ambiente de staging.** Dev local → produção direto.

---

## Nó A — Máquina local (dev)

- **OS:** Windows 11 + WSL2 Ubuntu
- **Ferramentas:** Claude Code (WSL2), PyCharm (Windows), VS Code (Windows)
- **Git:** GitHub Desktop (Windows) ou terminal WSL2
- **Frontend dev:** `npm run dev` → `localhost:5173`
- **Backend dev:** `flask run` ou PyCharm → `localhost:5000`
- **Variável:** `DEV_MODE=True` localmente

## Nó B — Render (produção backend)

- **Serviço:** Web Service · Free tier
- **Start command:** `flask db upgrade && gunicorn "app:create_app()" --bind 0.0.0.0:$PORT`
- **Cold start:** hiberna após 15min de inatividade (~50s para retomar)
- **Mitigação:** UptimeRobot fazendo ping a cada 5min
- **Deploy:** automático via push na `main` do svfinance-api
- **Migração planejada:** Render Free → Hostinger KVM1 VPS (Gunicorn + Nginx) — não iniciada

---

## Banco de dados — Supabase

- **Região:** sa-east-1 (São Paulo)
- **Conexão:** Transaction Pooler · porta 6543
- **Schema:** único — multi-tenancy por `company_id`
- **Senha:** sem caracteres especiais (conflito histórico com URL encoding)
- **Migration HEAD:** `pin_cliente_add_01`

**Cadeia de migrations (mais recentes):**
```
... → nfse_order_fields_01 → client_fields_v2_01 → pin_cliente_add_01 (HEAD)
```

**Verificar antes de nova migration:**
```bash
flask db heads    # deve retornar apenas 1 head
flask db history  # confirmar cadeia
flask db upgrade  # aplicar
```

---

## DNS — Cloudflare

- **Nameservers:** amber.ns.cloudflare.com + chase.ns.cloudflare.com
- **Domínio:** svfinance.com.br (Registro.br · expira 02/04/2027)

**Records ativos:**

| Nome | Tipo | Destino | Proxy |
|---|---|---|---|
| svfinance.com.br | CNAME | cname.vercel-dns.com | ✅ |
| www | CNAME | cname.vercel-dns.com | ✅ |
| app | CNAME | cname.vercel-dns.com | ✅ |
| restauraglass | CNAME | cname.vercel-dns.com | ✅ |
| api | CNAME | [render-url].onrender.com | ❌ (DNS only) |

---

## Vercel — frontends

| Projeto Vercel | Repo GitHub | Domínio |
|---|---|---|
| svfinance-landing | Svfinance/svfinance-landing | svfinance.com.br · www.svfinance.com.br |
| svfinance-app | Svfinance/svfinance-app | app.svfinance.com.br |
| svfinance-rg | Svfinance/svfinance-rg | restauraglass.svfinance.com.br |

**Deploy:** automático via push na `main` de cada repo.
**Framework:** Vite (svfinance-app e svfinance-rg) · Other/static (svfinance-landing)

---

## Serviços externos

| Serviço | Função | Env var | Ambiente atual |
|---|---|---|---|
| Resend | Email transacional | `RESEND_API_KEY` | Produção · `noreply@svfinance.com.br` |
| Asaas | Cobrança SaaS (PIX + cartão) | `ASAAS_API_KEY` + `ASAAS_ENV` | Sandbox (`sandbox.asaas.com`) |
| Focus NF-e | NF-e produto (PED-) + NFS-e serviço (OS-) | `FOCUS_ENV` + token no banco | Sandbox (`homologacao`) |
| Anthropic Claude | Brand Studio | `ANTHROPIC_API_KEY` | Produção |
| Remove.bg | Remoção de fundo (Brand Studio) | `REMOVE_BG_API_KEY` | Produção |
| UptimeRobot | Ping anti-cold-start | — | Monitorando api.svfinance.com.br |

---

## Deploy workflow (atual)

```
Código → GitHub Desktop (push) → Render/Vercel (deploy automático)
```

**Backend:**
1. Editar código localmente (PyCharm ou VS Code)
2. Commitar via GitHub Desktop ou terminal WSL2
3. Push → Render detecta e faz deploy automático
4. `flask db upgrade` roda automaticamente no start command

**Frontend:**
1. Editar código localmente (VS Code)
2. `npm run build` para testar build localmente (opcional)
3. Commitar e push → Vercel detecta e faz deploy automático

**Sem CI/CD adicional.** Sem staging. Sem pipeline de testes automatizados (planejado para escala).

---

## Migração de infraestrutura planejada (não iniciada)

| Atual | Planejado | Prioridade |
|---|---|---|
| Render Free | Hostinger KVM1 VPS + Gunicorn + Nginx | 🟡 Fase 3 |
| Supabase Free | PostgreSQL self-hosted no mesmo VPS | 🟡 Fase 3 |
| Salvatini95 GitHub | Svfinance org | 🔴 Em andamento |

**Manter Vercel e Cloudflare** após migração de infra.

---

## Comandos canônicos

```bash
# Backend — desenvolvimento local
cd finance-control-api  # ou svfinance-api após migração
source venv/bin/activate
flask run

# Migration — sempre verificar heads antes
flask db heads
flask db migrate -m "descricao_01"
flask db upgrade

# Frontend — desenvolvimento local
cd svfinance-app  # ou svfinance-rg
npm run dev

# Build de produção (testar antes do push)
npm run build
npm run preview
```
