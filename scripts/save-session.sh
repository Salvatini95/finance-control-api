#!/bin/bash
# scripts/save-session.sh — SV Finance
# Executar AO ENCERRAR toda sessão Claude Code.
# Uso: ./scripts/save-session.sh
# O Claude Code deve ter atualizado org-ia/05_estado.md antes deste script.

set -e

echo "=================================================="
echo "  SV Finance — Salvando sessão (sv-protocol v1.0)"
echo "=================================================="
echo ""

# Verificar se há mudanças para commitar
STATUS=$(git status --short)
if [ -z "$STATUS" ]; then
  echo "ℹ️  Nenhuma mudança pendente. Nada a salvar."
  exit 0
fi

echo "📋 Mudanças desta sessão:"
git status --short
echo ""

# Commitar org-ia/ (estado, backlog, blueprint)
ORGDIFF=$(git diff --name-only org-ia/ 2>/dev/null)
if [ -n "$ORGDIFF" ]; then
  git add org-ia/
  git commit -S -m "docs(org-ia): atualiza estado da sessão $(date '+%Y-%m-%d')"
  echo "✅ org-ia/ salvo."
fi

# Se houver código pendente não commitado, avisar
CODEDIFF=$(git diff --name-only --cached 2>/dev/null)
UNTRACKED=$(git status --short | grep "^??" | grep -v "org-ia/" | head -5)
if [ -n "$UNTRACKED" ]; then
  echo ""
  echo "⚠️  Código não commitado detectado:"
  echo "$UNTRACKED"
  echo "   Commite o código antes de encerrar:"
  echo "   git add . && git commit -S -m 'feat(escopo): descrição'"
fi

# Push
git push origin main
echo ""
echo "✅ Sessão salva e sincronizada com GitHub."
echo ""
echo "Na próxima sessão:"
echo "  cd $(pwd)"
echo "  ./scripts/health-check.sh"
echo "  claude"
echo "=================================================="
