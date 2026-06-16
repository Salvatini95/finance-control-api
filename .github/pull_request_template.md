# Pull Request

## Tipo de mudança
- [ ] `feat` — nova funcionalidade
- [ ] `fix` — correção de bug
- [ ] `refactor` — refatoração sem mudança de comportamento
- [ ] `migration` — migration Alembic
- [ ] `chore` — configuração, deps
- [ ] `docs` — documentação

## Descrição
<!-- O que foi feito e por quê? -->

## Issue relacionada
<!-- Closes #XX ou Ref #XX -->

## Checklist
- [ ] Commit assinado com GPG (`git commit -S`)
- [ ] Conventional Commit: `tipo(escopo): descrição em português`
- [ ] Se migration: `flask db heads` retorna 1 head, round-trip testado
- [ ] Se coluna NOT NULL nova: tem `server_default`
- [ ] Se feature RG: não vazou para svfinance-app
- [ ] `org-ia/05_estado.md` atualizado
- [ ] `org-ia/04_backlog.md` atualizado (tarefa marcada como concluída)

## Como testar
<!-- Passos para o reviewer testar a mudança -->

## Screenshots (se frontend)
<!-- Print antes/depois -->
