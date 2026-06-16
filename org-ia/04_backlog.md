# 04_backlog.md — SV Finance
> Backlog priorizado do ecossistema. Fonte: sessões ativas junho 2026.
> Atualizado por Opus a cada sessão. Son Coder não toca este arquivo.

---

## Legenda de modelo/effort

| Marcador | Executor | Quando usar |
|---|---|---|
| `Opus/high` | Opus (este chat) | Arquitetura, decisão crítica, ADR, prompt |
| `Opus/medium` | Opus (este chat) | Feature com impacto cross-cutting |
| `SonCoder/medium` | Son Coder (Claude Code) | Feature padrão, integração API conhecida |
| `SonCoder/high` | Son Coder (Claude Code) | Feature com escopo maior, não-arquitetural |

---

## 🔴 Alta prioridade

### [B-01] Testar fluxo Asaas sandbox completo
**Modelo/effort:** `SonCoder/medium`
**Repo:** svfinance-app + svfinance-api
**Descrição:** Validar Plans.jsx → CheckoutModal → Asaas sandbox (Pix + cartão).
Verificar webhook `/api/billing/webhook`. Cartão teste: `4111 1111 1111 1111`.
Pix: simular via dashboard sandbox.asaas.com → "Simular pagamento".
**Critério de done:** assinatura Pro criada, status `active` no banco, PlanBadge atualiza.

### [B-02] NFS-e frontend — NfseButton.jsx
**Modelo/effort:** `SonCoder/high`
**Repo:** svfinance-app + svfinance-rg
**Descrição:** Backend `nfse_service.py` e `nfse_routes.py` prontos.
Criar `NfseButton.jsx` e integrar em `Orders.jsx` (tipo OS-).
Ambiente: Focus NF-e sandbox (`FOCUS_ENV=homologacao`).
**Critério de done:** botão aparece em OS, emite NFS-e, retorna chave.

### [B-03] Registro de marca "SV Finance" no INPI
**Modelo/effort:** `Opus/medium`
**Repo:** — (tarefa administrativa)
**Descrição:** Registro de marca no INPI em paralelo com infra.
Classe 42 (SaaS/tecnologia). Verificar disponibilidade antes de protocolar.
Site: busca.inpi.gov.br → protocolar em gov.br/inpi.
**Critério de done:** protocolo gerado e salvo.

---

## 🟠 Média prioridade

### [B-04] Fix cartão físico mobile no Orders.jsx RG
**Modelo/effort:** `SonCoder/medium`
**Repo:** svfinance-rg
**Descrição:** 3 substituições de `display: grid` → `display: flex` no cartão RG
para corrigir layout em telas pequenas.
**Critério de done:** cartão renderiza corretamente em iPhone SE (375px).

### [B-05] Wi-Fi credentials por cliente
**Modelo/effort:** `SonCoder/high`
**Repo:** svfinance-api + svfinance-rg
**Descrição:** Fernet encrypt/decrypt já existe (`crypto.py`).
Adicionar `wifi_ssid` e `wifi_senha_cipher` ao model `Client`.
Migration + `wifi_routes.py` + `wifi_service.py`.
Frontend: componente com display de credencial + botão copiar (não API nativa de Wi-Fi).
**Critério de done:** admin cadastra credencial, cliente visualiza e copia.

---

## 🟡 Baixa prioridade (Fase 3)

### [B-06] Migração infraestrutura Render → Hostinger KVM1 VPS
**Modelo/effort:** `Opus/high`
**Repo:** svfinance-api
**Descrição:** Gunicorn + Nginx no VPS. PostgreSQL self-hosted (abandonar Supabase Free).
Manter Vercel e Cloudflare.
**Critério de done:** api.svfinance.com.br respondendo do VPS, banco migrado.

### [B-07] Consolidação GitHub org Svfinance
**Modelo/effort:** `Opus/medium`
**Repo:** todos
**Descrição:** Transferir 4 repos de Salvatini95 → Svfinance. Renomear conforme padrão.
Reconectar Vercel e Render. Ver `00_GUIA_INSTALACAO.md` Parte 3.
**Critério de done:** 4 repos na org, Vercel e Render apontando para nova org.

### [B-08] Agentes IA — Fase 2
**Modelo/effort:** `Opus/high`
**Repo:** todos
**Descrição:** Configurar Son Coder como sub-agente no Claude Code.
Configurar RevSon como reviewer automático (hook PostToolUse).
Instalar agentmemory (SQLite FTS5).
**Critério de done:** Son Coder executa tarefa do backlog sem intervenção manual.

---

## ✅ Concluídos recentemente

- [x] Sistema billing Asaas — backend completo (`asaas_service.py`, `billing_routes.py`, migration `billing_01`)
- [x] Frontend billing — `Plans.jsx`, `CheckoutModal.jsx`, `PlanBadge.jsx`, rota `/plans`
- [x] Landing page — redesign completo (logo spinning, parallax, dashboard SVG, carrossel IG, founders, toggle anual/mensal)
- [x] NF-e backend — `nfse_service.py`, `nfse_routes.py`, migration `nfse_order_fields_01`
- [x] Check-in QR + GPS — Haversine 300m, offline localStorage, dois PINs (permanente 4d + temporário 6d)
- [x] Histórico de importações — modal concluído e funcionando
- [x] PWA Restaura Glass — VitePWA autoUpdate
- [x] Sidebar RG — grupos Operacional/Financeiro/Relatórios
- [x] isRG por hostname — fix first-load theme failure
