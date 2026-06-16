# 05_estado.md — SV Finance
> Estado da sessão corrente. Atualizado por Opus no início e fim de cada sessão.
> Son Coder não toca este arquivo.

---

## Sessão atual

**Data:** 2026-06-16
**Repo foco:** svfinance-api
**Tarefa ativa:** B-01 — Testar fluxo Asaas sandbox
**Modelo/effort:** SonCoder/medium

---

## Estado no início desta sessão

**Migration HEAD:** `pin_cliente_add_01`
**Branch:** `main`
**Último commit:** `8110982 docs(org-ia): corrige migration HEAD para pin_cliente_add_01`

**O que estava em andamento:**
- B-01 — Asaas sandbox: código pronto, aguardava execução de testes

**O que estava bloqueado:**
- NFS-e frontend (`NfseButton.jsx`) — backend pronto, aguarda priorização
- Wi-Fi credentials — design aprovado, implementação pendente
- Logo Restaura Glass sem fundo (remove.bg) — aguarda asset

---

## Progresso desta sessão

| # | Ação | Status |
|---|---|---|
| 1 | Fix: PIX `status_inicial = "pending"` em `criar_assinatura` (era "active") | ✅ |
| 2 | Fix: `cancelar_assinatura` usa `_delete` (era `_post /cancel` — endpoint errado) | ✅ |
| 3 | Adiciona método `_delete` em `AsaasService` | ✅ |
| 4 | Cria `scripts/test_billing_sandbox.sh` — cobre CC, PIX, 3 webhooks, cancel | ✅ |
| 5 | Executar script contra Render (aguarda SENHA do operador) | ⬜ |
| 6 | Simular Pix via sandbox.asaas.com → confirmar webhook chega ao Render | ⬜ |
| 7 | Verificar PlanBadge atualiza em app.svfinance.com.br | ⬜ |

---

## Estado ao fim desta sessão

**Migration HEAD:** `pin_cliente_add_01` (sem nova migration)
**Último commit:** _(preencher ao commitar)_
**O que ficou pendente:**
- Executar `test_billing_sandbox.sh` contra Render (requer SENHA do operador)
- Passo manual: simular Pix no sandbox.asaas.com
- Verificar PlanBadge no frontend
**Próxima tarefa recomendada:** B-01 (completar execução) → B-02 (NfseButton)

---

## Decisões tomadas nesta sessão

| Decisão | Alternativa descartada | Motivo |
|---|---|---|
| PIX status inicial = "pending" | "active" imediato | Pix não é sincrônico — webhook PAYMENT_CONFIRMED deve setar "active" |
| Cancelamento via DELETE /subscriptions/{id} | POST /subscriptions/{id}/cancel | Asaas v3 usa REST DELETE para remoção de recurso |
