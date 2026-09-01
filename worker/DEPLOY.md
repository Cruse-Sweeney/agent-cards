# Deploying the agent host

One Cloudflare Worker serves all eleven agents. Free tier covers 100,000
requests a day, which is far more than a demo needs.

## First time

```bash
cd worker
npx wrangler login          # opens a browser; free Cloudflare account is enough
npx wrangler deploy         # prints the URL, e.g. https://a2a-agents.<you>.workers.dev
```

## Secrets

```bash
npx wrangler secret put ANTHROPIC_API_KEY
npx wrangler secret put GEMINI_API_KEY
npx wrangler secret put AGENT_SHARED_SECRET   # any long random string
```

`AGENT_SHARED_SECRET` gates `message/send` only — agent cards stay public so
Gravitee's catalog discovery can still read them. Without it, anyone who finds
the URL can spend your model budget, which is the exact failure this whole demo
is about. Generate one with:

```bash
openssl rand -hex 32
```

## Point the cards at the live host

The card's `url` field is what A2A clients follow, so it has to be the Worker,
not GitHub Pages:

```bash
cd ..
AGENT_LIVE=https://a2a-agents.<you>.workers.dev python3 build.py
git add -A && git commit -m "point cards at the live worker" && git push
```

## Check it

```bash
W=https://a2a-agents.<you>.workers.dev
curl -s $W/claim-intake/.well-known/agent-card.json | head -5
curl -s $W/claim-intake/health

curl -s -X POST $W/policy-coverage/ \
  -H "X-Agent-Secret: $AGENT_SHARED_SECRET" \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"message/send","params":{"message":
       {"role":"user","parts":[{"kind":"text","text":"Burst pipe under an upstairs sink, policy HO-4471, $18,000"}],
        "messageId":"m1","kind":"message"}}}'
```

## Then wire Gravitee to it

Set each A2A proxy's endpoint target to `https://a2a-agents.<you>.workers.dev/<slug>`
and add the shared secret as a request header on the endpoint. The Cloud data
plane can reach it, so the demo no longer needs the hybrid gateway or your
laptop.
