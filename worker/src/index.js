/**
 * A2A agent host — one Cloudflare Worker serving every agent in agents.json.
 *
 * Routes:
 *   GET  /                                   directory of agents
 *   GET  /<slug>/.well-known/agent-card.json the agent card  (public)
 *   GET  /<slug>/.well-known/agent.json      legacy card path (public)
 *   GET  /<slug>/health                      liveness         (public)
 *   POST /<slug>/                            JSON-RPC message/send  (gated)
 *
 * Cards stay public because that is what Gravitee's catalog discovery reads.
 * message/send is gated on a shared secret, because a public unauthenticated
 * endpoint that spends your model budget is precisely the failure the demo
 * warns about — see AGENT_SHARED_SECRET below.
 */
import AGENTS from "../agents.json";

const CARD_PATHS = ["/.well-known/agent-card.json", "/.well-known/agent.json"];

const json = (body, status = 200, extra = {}) =>
  new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": "*",
      "cache-control": "no-store",
      ...extra,
    },
  });

const rpcError = (id, code, message) =>
  json({ jsonrpc: "2.0", id: id ?? null, error: { code, message } });

const agentMessage = (text) => ({
  role: "agent",
  parts: [{ kind: "text", text }],
  messageId: crypto.randomUUID(),
  kind: "message",
});

/** Pull the user text out of an A2A message object. */
function extractText(message) {
  return (message?.parts ?? [])
    .filter((p) => (p.kind ?? "text") === "text")
    .map((p) => p.text ?? "")
    .join("\n")
    .trim();
}

async function callAnthropic(env, model, system, prompt) {
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model,
      max_tokens: 2000,
      system,
      // Thinking is on by default on Opus 5; low effort keeps a demo responsive.
      output_config: { effort: "low" },
      messages: [{ role: "user", content: prompt }],
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`anthropic ${res.status}: ${JSON.stringify(data).slice(0, 300)}`);
  if (data.stop_reason === "refusal") throw new Error("model declined the request");
  const text = (data.content ?? [])
    .filter((b) => b.type === "text")
    .map((b) => b.text)
    .join("")
    .trim();
  if (!text) throw new Error("empty response");
  return text;
}

async function callGemini(env, model, system, prompt) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "x-goog-api-key": env.GEMINI_API_KEY, "content-type": "application/json" },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      systemInstruction: { parts: [{ text: system }] },
      generationConfig: { thinkingConfig: { thinkingLevel: "low" } },
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`gemini ${res.status}: ${JSON.stringify(data).slice(0, 300)}`);
  const text = (data.candidates?.[0]?.content?.parts ?? [])
    .map((p) => p.text ?? "")
    .join("")
    .trim();
  if (!text) throw new Error("gemini returned an empty response");
  return text;
}

function directory(origin) {
  const rows = Object.entries(AGENTS)
    .map(
      ([slug, a]) =>
        `<tr><td><b>${a.card.name}</b><div class=d>${a.card.description}</div></td>` +
        `<td>${a.vendor}<div class=d>${a.model}</div></td>` +
        `<td>${a.card.skills.length}</td>` +
        `<td><a href="/${slug}/.well-known/agent-card.json"><code>${slug}</code></a></td></tr>`
    )
    .join("\n");
  return `<!doctype html><meta charset=utf-8><title>A2A Agents</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>:root{color-scheme:light dark}body{font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:900px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:24px;margin:0 0 4px;letter-spacing:-.02em}p.s{color:#667;margin:0 0 26px}
table{border-collapse:collapse;width:100%;font-size:14px}th{text-align:left;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#889;border-bottom:1px solid #8884;padding:0 12px 8px 0}
td{border-bottom:1px solid #8882;padding:11px 12px 11px 0;vertical-align:top}.d{color:#778;font-size:12.5px;margin-top:2px}
code{font:12px ui-monospace,Menlo,monospace}</style>
<h1>A2A Agents</h1><p class=s>${Object.keys(AGENTS).length} live agents at <code>${origin}</code>.
Cards are public; <code>message/send</code> requires the shared secret.</p>
<table><tr><th>Agent</th><th>Backed by</th><th>Skills</th><th>Card</th></tr>${rows}</table>`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "access-control-allow-origin": "*",
          "access-control-allow-methods": "GET, POST, OPTIONS",
          "access-control-allow-headers": "*",
        },
      });
    }

    if (path === "/" || path === "/index.html") {
      return new Response(directory(url.origin), {
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }

    const slug = path.split("/").filter(Boolean)[0];
    const agent = AGENTS[slug];
    if (!agent) return json({ error: "unknown agent", agents: Object.keys(AGENTS) }, 404);

    const rest = path.slice(slug.length + 1) || "/";

    if (request.method === "GET") {
      if (CARD_PATHS.includes(rest)) return json(agent.card);
      if (rest === "/health" || rest === "/healthz")
        return json({ status: "ok", agent: agent.card.name, model: agent.model });
      return json({ error: "not found", cardPaths: CARD_PATHS }, 404);
    }

    if (request.method !== "POST") return json({ error: "method not allowed" }, 405);

    // Gate the expensive path. Cards above stay open so discovery still works.
    if (env.AGENT_SHARED_SECRET) {
      const supplied =
        request.headers.get("x-agent-secret") ||
        (request.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
      if (supplied !== env.AGENT_SHARED_SECRET)
        return json({ error: "unauthorized", detail: "missing or bad X-Agent-Secret" }, 401);
    }

    let rpc;
    try {
      rpc = await request.json();
    } catch {
      return rpcError(null, -32700, "Parse error");
    }

    const { id = null, method, params = {} } = rpc;
    if (method !== "message/send" && method !== "message/stream")
      return rpcError(id, -32601, `Method not found: ${method}`);

    const prompt = extractText(params.message);
    if (!prompt) return rpcError(id, -32602, "No text part found in message");

    try {
      const reply =
        agent.vendor === "Google"
          ? await callGemini(env, agent.model, agent.system, prompt)
          : await callAnthropic(env, agent.model, agent.system, prompt);
      return json({ jsonrpc: "2.0", id, result: agentMessage(reply) });
    } catch (err) {
      return rpcError(id, -32603, String(err.message ?? err).slice(0, 400));
    }
  },
};
