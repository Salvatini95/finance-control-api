# policies/gitflow.md — sv-protocol v1.0
> Política de commits, branches e versionamento do SV Finance.

---

## Modelo: single-trunk

Commits direto na `main`. Sem gitflow completo por enquanto (solo dev).
Pull Requests apenas quando houver segundo commiter ou feature experimental.

## Conventional Commits

Formato obrigatório:
```
tipo(escopo): descrição curta em português (máx 72 chars)

Corpo opcional: explica o PORQUÊ, não o quê.

Co-Authored-By: opus@svfinance.com.br  # se Opus participou
```

**Tipos:**
- `feat` — nova funcionalidade visível ao usuário
- `fix` — correção de bug
- `chore` — configuração, deps, scripts, sem impacto em runtime
- `docs` — apenas documentação
- `refactor` — refatoração sem mudança de comportamento observável
- `migration` — migration Alembic (sempre acompanha `feat` ou `fix` relacionado)
- `style` — formatação, sem mudança de lógica

**Escopos comuns:**
`api`, `app`, `rg`, `landing`, `billing`, `nfe`, `nfse`, `checkin`, `auth`, `orders`, `clients`, `products`, `infra`, `deps`

**Exemplos válidos:**
```
feat(billing): adiciona webhook Asaas para atualização de status de assinatura
fix(checkin): remove distância da mensagem de erro para evitar gaming
migration(nfe): adiciona campos nfe_ref e nfe_chave em orders
chore(deps): atualiza requests para >=2.31.0
docs(org-ia): atualiza backlog com B-05 Wi-Fi credentials
```

## Assinatura GPG

Todo commit deve ser assinado:
```bash
git commit -S -m "tipo(escopo): descrição"
```

O `-S` usa a chave GPG configurada em `~/.gitconfig`.

## Rebase — nunca merge commit na main

```bash
# Antes de push, se houver commits remotos novos:
git pull --rebase origin main
git push origin main
```

Nunca `git merge` na main. Histórico linear obrigatório.

## SemVer (quando aplicável)

Tags de release: `v0.1.0`, `v0.2.0`, etc.
Patch: `v0.1.1` para fix em produção.
Não é obrigatório por commit — usar quando houver release significativa.

---

# policies/migration.md — Alembic + SQLAlchemy
> Armadilhas conhecidas. Ler antes de criar qualquer migration.

---

## Regras obrigatórias

```python
# 1. SEMPRE server_default em coluna NOT NULL nova
op.add_column('tabela', sa.Column(
    'coluna',
    sa.String(),
    nullable=False,
    server_default='valor_default'
))

# 2. Verificar heads ANTES de criar migration
# flask db heads  → deve retornar apenas 1 linha
# Se retornar 2+, há conflito de heads — resolver antes de prosseguir

# 3. down_revision SEMPRE verificado
revision      = "nova_migration_01"
down_revision = "billing_01"  # ← confirmar com: flask db heads

# 4. Round-trip antes de commitar
flask db upgrade    # aplica
flask db downgrade  # reverte
flask db upgrade    # aplica novamente — se não quebrar, está ok

# 5. NUNCA backref com múltiplos FKs
# Errado:
db.relationship("Client", backref="checkins")
# Correto:
db.relationship("Client", back_populates="checkins", foreign_keys=[client_id])
```

## Histórico de problemas resolvidos

| Migration | Problema | Solução |
|---|---|---|
| `nfse_order_fields_01` | `down_revision` errado | Corrigido manualmente via find-and-replace |
| `billing_01` | Apontava para head errado | Corrigido via `down_revision` correto |
| Múltiplos heads (2025) | Conflito após Railway → Render | `flask db heads` + corrigir `down_revision` manualmente |

---

# policies/secrets.md — Gestão de segredos
> Regras absolutas. Violação = risco de segurança de produção.

---

## Regras

1. **Nunca commitar `.env`** — apenas `.env.example` com nomes sem valores
2. **Nunca logar valor de secret** — logar apenas presença:
   ```python
   # Errado:
   print(f"ASAAS_API_KEY: {os.getenv('ASAAS_API_KEY')}")
   # Correto:
   print(f"ASAAS_API_KEY presente: {bool(os.getenv('ASAAS_API_KEY'))}")
   ```
3. **Nunca `sed -i` ou chain `&&` para manipular secrets** — usar Read + Write separados
4. **Saída de API externa** (Asaas, Focus NF-e) nunca vai crua para log se contiver dados de pagamento ou PII
5. **Token Focus NF-e da Restaura Glass:** manter apenas no banco (`companies.token_focusnfe`) ou env. Nunca em código.
6. **Asaas API Key:** env var `ASAAS_API_KEY`. Nunca hardcoded.
