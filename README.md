# Agent Cards

Static [A2A](https://a2a-protocol.org) agent cards, served from GitHub Pages as
stable public URLs so the **Gravitee Agent Catalog** can discover them.

Eleven agents across four domains (Claims, Underwriting, Servicing, Platform),
four vendors and seven owning teams — an estate with enough spread that the
catalog has something to say.

**These are catalog fixtures.** The cards are spec-valid and permanently hosted;
the agents behind them are not running. The catalog reads cards, it does not
invoke agents. Three of them (`claim-intake`, `policy-coverage`,
`claim-adjudicator`) mirror agents that *do* run, in the claim-mesh demo.

## Card URLs

Each agent serves its card at both the current and legacy well-known paths:

```
https://cruse-sweeney.github.io/agent-cards/<slug>/.well-known/agent-card.json
https://cruse-sweeney.github.io/agent-cards/<slug>/.well-known/agent.json
```

The index at <https://cruse-sweeney.github.io/agent-cards/> lists every agent
and its URL.

## Editing

Cards are generated — edit `build.py`, not the JSON.

```bash
python3 build.py    # rewrites every <slug>/.well-known/ and index.html
```

`.nojekyll` is required: GitHub Pages runs Jekyll by default, which strips
directories beginning with a dot, including `.well-known`.

## Making them live

The cards above are static. To make the agents actually answer `message/send`,
deploy `worker/` — one Cloudflare Worker serves all eleven, backed by Claude and
Gemini. See [worker/DEPLOY.md](worker/DEPLOY.md).

Cards stay public (catalog discovery needs to read them); `message/send` is
gated on a shared secret, because a public unauthenticated agent endpoint that
spends your model budget is the exact failure this demo exists to warn about.
