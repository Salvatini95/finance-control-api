#!/bin/bash
# scripts/health-check.sh — SV Finance
# Executar no início de TODA sessão Claude Code.
# Uso: ./scripts/health-check.sh

set -e

echo "=================================================="
echo "  SV Finance — Health Check (sv-protocol v1.0)"
echo "=================================================="
echo ""

# 1. Branch atual
BRANCH=$(git branch --show-current)
echo "📌 Branch: $BRANCH"
if [ "$BRANCH" != "main" ]; then
  echo "⚠️  ATENÇÃO: não está na main!"
fi
echo ""

# 2. Status do repositório
echo "📋 Git status:"
git status --short
echo ""

# 3. Últimos 5 commits
echo "📜 Últimos 5 commits:"
git log --oneline -5
echo ""

# 4. Diff summary
DIFF=$(git diff --stat)
if [ -n "$DIFF" ]; then
  echo "📝 Diff pendente:"
  echo "$DIFF"
  echo ""
fi

# 5. Migration HEAD (apenas no svfinance-api)
if [ -f "app/__init__.py" ]; then
  echo "🗄️  Migration HEAD:"
  if command -v flask &> /dev/null; then
    flask db heads 2>/dev/null || echo "  (ative o venv primeiro: source venv/bin/activate)"
  else
    echo "  (flask não encontrado — ative o venv)"
  fi
  echo ""
fi

# 6. Arquivos org-ia existentes
echo "📁 org-ia/ disponível:"
if [ -d "org-ia" ]; then
  ls org-ia/ 2>/dev/null
else
  echo "  (org-ia/ não encontrada neste repo)"
fi
echo ""

echo "=================================================="
echo "  Próximos passos:"
echo "  1. Ler org-ia/05_estado.md (sessão corrente)"
echo "  2. Ler org-ia/04_backlog.md (tarefa ativa)"
echo "  3. Ler org-ia/topologia.md (antes de ação em ambiente)"
echo "=================================================="
