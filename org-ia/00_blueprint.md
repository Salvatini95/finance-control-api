# 00_blueprint.md — SV Finance
> Fonte absoluta de identidade e modelo de negócio do ecossistema SV.
> Atualizado por Opus apenas.

---

## Identidade

**Nome:** SV Finance Control
**Tagline:** ERP acessível para MEIs e pequenas empresas brasileiras
**Owner:** Guilherme Salvatini (CEO + Dev solo)
**Co-fundadora:** Jackeline Afonso (marca e marketing)

## Problema resolvido

MEIs e pequenas empresas dependem de planilhas ou ERPs caros (Conta Azul R$89+/mês, Omie R$99+/mês) e complexos. O SV Finance oferece gestão financeira e operacional moderna, acessível e customizável por nicho.

## Ecossistema de produtos

```
SV Finance (ecossistema)
│
├── Produto 1: SV App (SaaS self-service)
│   URL: app.svfinance.com.br
│   Repo: svfinance-app
│   ICP: MEIs e pequenas empresas que contratam por conta própria
│   Modelo: Free Trial 7 dias → Pro R$49/mês → Business R$99/mês
│
├── Produto 2: SV Soluções (implementação customizada)
│   URL: solucoes.svfinance.com.br
│   Repo: svfinance-rg (template base de implementação)
│   ICP: Empresas que precisam de ERP customizado com manutenção
│   Modelo: Implementação R$800–R$8.000 + recorrência Business ativa
│   │
│   └── Instância piloto: Restaura Glass
│       URL: restauraglass.svfinance.com.br
│       company_id: 20
│       Nicho: limpeza e restauração de vidros
│
├── Vitrine: SV Landing
│   URL: svfinance.com.br e www.svfinance.com.br
│   Repo: svfinance-landing
│   Função: entrada para os dois produtos acima
│
└── Backend compartilhado
    URL: api.svfinance.com.br
    Repo: svfinance-api
    Serve: todos os frontends, diferenciado por company_id
```

## Modelo de negócio

| Plano | Preço mensal | Preço anual | Público |
|---|---|---|---|
| Free Trial | R$0 · 7 dias | — | Aquisição |
| Pro Fundador | R$49/mês | R$39/mês (R$468/ano) | MEIs e pequenas empresas |
| Business Fundador | R$99/mês | R$79/mês (R$948/ano) | Empresas com equipe |
| SV Soluções | R$800–R$8.000 implementação | + recorrência Business | Clientes sob contrato |

Preços "Fundador" são travados (`founder=True` no Subscription) — garantia de preço vitalício para primeiros clientes.

## Estágio

Beta gratuito em produção. Primeiro cliente pagante em negociação (Restaura Glass). Sistema de cobrança Asaas integrado no backend, frontend Plans.jsx em deploy.

## Stack base (todos os produtos)

- Backend: Python 3.13 + Flask 3.x + PostgreSQL (Supabase)
- Frontend: React 19 + Vite (sem Tailwind — estilos inline)
- Infra: Render (backend) + Vercel (frontends) + Cloudflare (DNS) + Supabase (banco)
- Domínio: svfinance.com.br via Registro.br (expira 02/04/2027)
