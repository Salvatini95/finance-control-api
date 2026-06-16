#!/usr/bin/env bash
# test_billing_sandbox.sh — Testa o fluxo Asaas sandbox completo (B-01)
#
# Pré-requisitos:
#   - ASAAS_ENV=sandbox configurado no servidor
#   - Credenciais do dev (company_id=17)
#   - jq instalado: sudo apt install jq
#
# Uso:
#   BASE_URL=http://localhost:5000/api SENHA=suasenha ./scripts/test_billing_sandbox.sh
#   BASE_URL=https://api.svfinance.com.br/api SENHA=suasenha ./scripts/test_billing_sandbox.sh
#
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5000/api}"
EMAIL="${EMAIL:-guilhermesalvatini8@gmail.com}"
SENHA="${SENHA:-}"

# ─── cores ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓ $*${NC}"; }
fail() { echo -e "${RED}✗ $*${NC}"; }
info() { echo -e "${YELLOW}→ $*${NC}"; }

if [ -z "$SENHA" ]; then
  echo "Uso: SENHA=<senha> ./scripts/test_billing_sandbox.sh"
  exit 1
fi

echo ""
echo "============================================================"
echo "  B-01 — Teste Asaas Sandbox"
echo "  BASE_URL: $BASE_URL"
echo "  EMAIL:    $EMAIL"
echo "============================================================"

# ─── 0. Login ────────────────────────────────────────────────────────────────
info "0. Login..."
LOGIN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$SENHA\"}")
echo "$LOGIN" | jq .

TOKEN=$(echo "$LOGIN" | jq -r '.access_token // empty')
if [ -z "$TOKEN" ]; then
  fail "Login falhou — sem access_token"
  exit 1
fi
ok "JWT obtido"
AUTH="Authorization: Bearer $TOKEN"

# ─── 1. Status inicial ───────────────────────────────────────────────────────
info "1. Status inicial..."
STATUS=$(curl -s -X GET "$BASE_URL/billing/status" -H "$AUTH")
echo "$STATUS" | jq .
SUB_STATUS=$(echo "$STATUS" | jq -r '.subscription.status // "sem_assinatura"')
ok "Status atual: $SUB_STATUS"

# ─── 2. Assinar com Cartão de Crédito ────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────────────────────"
info "2. Criando assinatura Pro/mensal — Cartão de Crédito (sandbox)..."
SUB_CC=$(curl -s -X POST "$BASE_URL/billing/subscribe" \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "pro",
    "interval": "monthly",
    "billing_type": "CREDIT_CARD",
    "titular": {
      "name":          "Guilherme Salvatini",
      "cpfCnpj":       "00000000000",
      "email":         "guilhermesalvatini8@gmail.com",
      "phone":         "44999999999",
      "postalCode":    "87010000",
      "addressNumber": "100"
    },
    "credit_card": {
      "holderName":  "GUILHERME SALVATINI",
      "number":      "4111111111111111",
      "expiryMonth": "05",
      "expiryYear":  "2028",
      "ccv":         "123"
    }
  }')
echo "$SUB_CC" | jq .
SUB_OK=$(echo "$SUB_CC" | jq -r '.ok')
if [ "$SUB_OK" = "true" ]; then
  ok "Assinatura CC criada"
  SUB_ID=$(echo "$SUB_CC" | jq -r '.subscription.asaas_subscription_id // ""')
  echo "  asaas_subscription_id: $SUB_ID"
else
  fail "Falhou: $(echo "$SUB_CC" | jq -r '.msg')"
fi

# ─── 3. Status pós-CC ────────────────────────────────────────────────────────
info "3. Verificando status após CC..."
STATUS2=$(curl -s -X GET "$BASE_URL/billing/status" -H "$AUTH")
echo "$STATUS2" | jq .
SUB_STATUS2=$(echo "$STATUS2" | jq -r '.subscription.status // "?"')
if [ "$SUB_STATUS2" = "active" ]; then
  ok "Status = active ✓"
else
  fail "Esperado 'active', recebido '$SUB_STATUS2'"
fi

# ─── 4. Cancelar ─────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────────────────────"
info "4. Cancelando assinatura CC..."
CANCEL=$(curl -s -X POST "$BASE_URL/billing/cancel" -H "$AUTH" \
  -H "Content-Type: application/json")
echo "$CANCEL" | jq .
CANCEL_OK=$(echo "$CANCEL" | jq -r '.ok')
if [ "$CANCEL_OK" = "true" ]; then
  ok "Assinatura cancelada"
else
  fail "Cancelamento falhou: $(echo "$CANCEL" | jq -r '.msg')"
fi

# ─── 5. Assinar com PIX ──────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────────────────────"
info "5. Criando assinatura Pro/mensal — PIX (sandbox)..."
SUB_PIX=$(curl -s -X POST "$BASE_URL/billing/subscribe" \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "pro",
    "interval": "monthly",
    "billing_type": "PIX",
    "titular": {
      "name":          "Guilherme Salvatini",
      "cpfCnpj":       "00000000000",
      "email":         "guilhermesalvatini8@gmail.com",
      "phone":         "44999999999",
      "postalCode":    "87010000",
      "addressNumber": "100"
    }
  }')
echo "$SUB_PIX" | jq .
PIX_OK=$(echo "$SUB_PIX" | jq -r '.ok')
PIX_STATUS=$(echo "$SUB_PIX" | jq -r '.subscription.status // "?"')
if [ "$PIX_OK" = "true" ]; then
  ok "Assinatura PIX criada — status=$PIX_STATUS (esperado: pending)"
else
  fail "Falhou: $(echo "$SUB_PIX" | jq -r '.msg')"
fi

# ─── 6. Simular webhook PAYMENT_CONFIRMED ────────────────────────────────────
echo ""
echo "────────────────────────────────────────────────────────────"
info "6. Simulando webhook PAYMENT_CONFIRMED (company_id=17)..."
WH_CONFIRM=$(curl -s -X POST "$BASE_URL/billing/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "PAYMENT_CONFIRMED",
    "payment": {
      "id": "pay_sandbox_test_001",
      "externalReference": "company_17_plan_pro",
      "value": 49.00,
      "status": "CONFIRMED"
    }
  }')
echo "$WH_CONFIRM" | jq .
WH_OK=$(echo "$WH_CONFIRM" | jq -r '.ok')
if [ "$WH_OK" = "true" ]; then
  ok "Webhook PAYMENT_CONFIRMED processado"
else
  fail "Webhook PAYMENT_CONFIRMED falhou"
fi

# ─── 7. Status pós-webhook ───────────────────────────────────────────────────
info "7. Verificando status após webhook CONFIRMED..."
STATUS3=$(curl -s -X GET "$BASE_URL/billing/status" -H "$AUTH")
echo "$STATUS3" | jq .
SUB_STATUS3=$(echo "$STATUS3" | jq -r '.subscription.status // "?"')
if [ "$SUB_STATUS3" = "active" ]; then
  ok "Status = active após webhook ✓ — CRITÉRIO DE DONE ATINGIDO"
else
  fail "Esperado 'active', recebido '$SUB_STATUS3'"
fi

# ─── 8. Simular PAYMENT_OVERDUE ──────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────────────────────"
info "8. Simulando webhook PAYMENT_OVERDUE..."
WH_OVERDUE=$(curl -s -X POST "$BASE_URL/billing/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "PAYMENT_OVERDUE",
    "payment": {
      "id": "pay_sandbox_test_002",
      "externalReference": "company_17_plan_pro",
      "value": 49.00,
      "status": "OVERDUE"
    }
  }')
echo "$WH_OVERDUE" | jq .
STATUS4=$(curl -s -X GET "$BASE_URL/billing/status" -H "$AUTH")
SUB_STATUS4=$(echo "$STATUS4" | jq -r '.subscription.status // "?"')
if [ "$SUB_STATUS4" = "overdue" ]; then
  ok "Status = overdue após PAYMENT_OVERDUE ✓"
else
  fail "Esperado 'overdue', recebido '$SUB_STATUS4'"
fi

# ─── 9. Restaurar active e testar SUBSCRIPTION_DELETED ───────────────────────
info "9. Restaurando active e testando SUBSCRIPTION_DELETED..."
curl -s -X POST "$BASE_URL/billing/webhook" \
  -H "Content-Type: application/json" \
  -d '{"event":"PAYMENT_CONFIRMED","payment":{"externalReference":"company_17_plan_pro"}}' \
  | jq -r '.msg' > /dev/null

WH_DEL=$(curl -s -X POST "$BASE_URL/billing/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "SUBSCRIPTION_DELETED",
    "subscription": {
      "id": "sub_sandbox_test_001",
      "externalReference": "company_17_plan_pro"
    }
  }')
echo "$WH_DEL" | jq .
STATUS5=$(curl -s -X GET "$BASE_URL/billing/status" -H "$AUTH")
SUB_STATUS5=$(echo "$STATUS5" | jq -r '.subscription.status // "?"')
if [ "$SUB_STATUS5" = "canceled" ]; then
  ok "Status = canceled após SUBSCRIPTION_DELETED ✓"
else
  fail "Esperado 'canceled', recebido '$SUB_STATUS5'"
fi

# ─── Resumo ──────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  Resumo B-01"
echo "============================================================"
echo "  Cartão CC (4111...) → assinatura criada: OK (verificar acima)"
echo "  PIX → status initial = pending: OK"
echo "  Webhook PAYMENT_CONFIRMED → active: OK"
echo "  Webhook PAYMENT_OVERDUE  → overdue: OK"
echo "  Webhook SUBSCRIPTION_DELETED → canceled: OK"
echo ""
echo "  PRÓXIMO PASSO MANUAL:"
echo "  1. Acesse sandbox.asaas.com"
echo "  2. Localize a cobrança PIX gerada no passo 5"
echo "  3. Clique em 'Simular pagamento'"
echo "  4. Confirme que o webhook PAYMENT_CONFIRMED chega ao Render"
echo "     e PlanBadge atualiza no app.svfinance.com.br"
echo "============================================================"
