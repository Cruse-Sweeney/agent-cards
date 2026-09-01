#!/usr/bin/env python3
"""Generate A2A agent cards for the Gravitee Agent Catalog.

These are catalog fixtures: real, spec-valid A2A agent cards served as static
files so Gravitee can discover them at a stable public URL. The agents behind
them are not running -- the catalog reads cards, it does not invoke agents.

    python3 build.py          # writes ./<slug>/.well-known/agent-card.json + index.html
"""
import json
import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://cruse-sweeney.github.io/agent-cards"

# A deliberately sprawling estate: four domains, four vendors, seven owning
# teams. That spread is the point -- a catalog of three agents makes no
# argument, a catalog that shows nobody knew there were eleven of them does.
AGENTS = [
    # ---- Claims ---------------------------------------------------------
    dict(slug="claim-intake", name="Claim Intake Agent", domain="Claims",
         vendor="Anthropic", model="claude-opus-5", team="Claims Platform",
         desc="Extracts structured claim facts from an unstructured customer message.",
         skills=[
             dict(id="extract-claim-facts", name="Extract claim facts",
                  desc="Turns a free-text claim report into a validated JSON claim record.",
                  tags=["insurance", "extraction", "claims"],
                  examples=["Hi, my basement flooded last Tuesday, policy HO-4471, estimate is $18,000"],
                  inn=["text/plain"], out=["application/json"]),
         ]),
    dict(slug="policy-coverage", name="Policy Coverage Agent", domain="Claims",
         vendor="Google", model="gemini-3.5-flash-lite", team="Claims Platform",
         desc="Checks a structured claim against the policy book and returns a coverage opinion.",
         skills=[
             dict(id="check-coverage", name="Check policy coverage",
                  desc="Given a claim record, returns coverage status, deductible and any exclusion that applies.",
                  tags=["insurance", "coverage", "policy"],
                  examples=['{"policy_id":"HO-4471","incident_type":"water_damage"}'],
                  inn=["application/json"], out=["application/json"]),
             dict(id="lookup-policy", name="Look up a policy",
                  desc="Returns the policy record for a policy number, including limits and exclusions.",
                  tags=["insurance", "policy", "lookup"],
                  examples=["HO-4471"],
                  inn=["text/plain"], out=["application/json"]),
         ]),
    dict(slug="claim-adjudicator", name="Claim Adjudicator", domain="Claims",
         vendor="Anthropic", model="claude-opus-5", team="Claims Platform",
         desc="Orchestrates claim intake and policy coverage agents, then issues an approve/deny/refer decision.",
         skills=[
             dict(id="adjudicate-claim", name="Adjudicate a claim",
                  desc="Takes a raw customer claim message and returns a decision with rationale and next steps.",
                  tags=["insurance", "orchestration", "claims", "multi-agent"],
                  examples=["My basement flooded last Tuesday, policy HO-4471, estimate is $18,000"],
                  inn=["text/plain"], out=["text/plain"]),
         ]),
    dict(slug="fraud-signal", name="Fraud Signal Agent", domain="Claims",
         vendor="Self-hosted", model="llama-3.3-70b", team="Special Investigations",
         desc="Scores a claim for fraud indicators and explains which signals fired.",
         skills=[
             dict(id="score-fraud-risk", name="Score fraud risk",
                  desc="Returns a 0-100 fraud risk score for a claim record with contributing signals.",
                  tags=["insurance", "fraud", "risk", "scoring"],
                  examples=['{"policy_id":"AU-9920","incident_type":"theft","estimated_amount_usd":41000}'],
                  inn=["application/json"], out=["application/json"]),
             dict(id="explain-risk-factors", name="Explain risk factors",
                  desc="Plain-language explanation of why a claim scored the way it did, for an investigator.",
                  tags=["insurance", "fraud", "explainability"],
                  examples=["Explain the score for claim CLM-2026-0442"],
                  inn=["text/plain"], out=["text/plain"]),
         ]),
    dict(slug="damage-estimator", name="Damage Estimator", domain="Claims",
         vendor="Anthropic", model="claude-sonnet-5", team="Claims Platform",
         desc="Parses contractor quotes and estimates repair cost ranges from a loss description.",
         skills=[
             dict(id="parse-contractor-quote", name="Parse a contractor quote",
                  desc="Extracts line items, labour, materials and totals from an uploaded quote.",
                  tags=["insurance", "extraction", "estimating"],
                  examples=["Parse the attached restoration estimate"],
                  inn=["application/pdf", "text/plain"], out=["application/json"]),
             dict(id="estimate-repair-cost", name="Estimate repair cost",
                  desc="Returns a cost range for a described loss, with regional adjustment.",
                  tags=["insurance", "estimating"],
                  examples=["Buckled hardwood and sagging ceiling drywall, approx 400 sq ft, Denver CO"],
                  inn=["text/plain"], out=["application/json"]),
         ]),

    # ---- Underwriting ---------------------------------------------------
    dict(slug="risk-scoring", name="Underwriting Risk Scorer", domain="Underwriting",
         vendor="OpenAI", model="gpt-5", team="Underwriting Data Science",
         desc="Scores a new-business applicant and proposes a premium band.",
         skills=[
             dict(id="score-applicant", name="Score an applicant",
                  desc="Returns a risk tier and the factors driving it for a submitted application.",
                  tags=["insurance", "underwriting", "risk"],
                  examples=['{"applicant":"...","property_year_built":1961}'],
                  inn=["application/json"], out=["application/json"]),
             dict(id="price-premium", name="Propose a premium",
                  desc="Suggests a premium band for a scored applicant against the current rate table.",
                  tags=["insurance", "underwriting", "pricing"],
                  examples=["Price a HO-3 for risk tier B in ZIP 80206"],
                  inn=["text/plain"], out=["application/json"]),
         ]),
    dict(slug="property-inspection", name="Property Inspection Agent", domain="Underwriting",
         vendor="Google", model="gemini-3.5-pro", team="Underwriting Data Science",
         desc="Reads inspection photographs and flags condition issues relevant to underwriting.",
         skills=[
             dict(id="analyze-inspection-photos", name="Analyse inspection photos",
                  desc="Identifies roof, siding and structural condition issues from photographs.",
                  tags=["insurance", "underwriting", "vision"],
                  examples=["Assess roof condition from these four photos"],
                  inn=["image/jpeg", "image/png"], out=["application/json"]),
         ]),

    # ---- Servicing ------------------------------------------------------
    dict(slug="customer-comms", name="Customer Communications Agent", domain="Servicing",
         vendor="Anthropic", model="claude-haiku-4-5", team="Customer Experience",
         desc="Drafts claimant-facing correspondence in plain language at a set reading level.",
         skills=[
             dict(id="draft-claimant-letter", name="Draft a claimant letter",
                  desc="Writes an approval, denial or information-request letter from a decision record.",
                  tags=["insurance", "communications", "drafting"],
                  examples=["Draft a denial letter for claim CLM-2026-0451"],
                  inn=["application/json"], out=["text/plain"]),
             dict(id="summarize-for-customer", name="Summarise for a customer",
                  desc="Rewrites an internal decision into language a claimant can act on.",
                  tags=["insurance", "communications", "summarisation"],
                  examples=["Explain this adjudication to the policyholder"],
                  inn=["text/plain"], out=["text/plain"]),
         ]),
    dict(slug="document-ocr", name="Document Intake Agent", domain="Servicing",
         vendor="Self-hosted", model="docling-v2", team="Shared Services",
         desc="Classifies and extracts text from inbound documents before routing them.",
         skills=[
             dict(id="classify-document", name="Classify a document",
                  desc="Labels an inbound document as claim form, estimate, police report, invoice or other.",
                  tags=["ocr", "classification", "intake"],
                  examples=["Classify this uploaded PDF"],
                  inn=["application/pdf", "image/jpeg"], out=["application/json"]),
             dict(id="extract-document-text", name="Extract document text",
                  desc="Returns structured text and tables from a scanned document.",
                  tags=["ocr", "extraction"],
                  examples=["Extract the text and tables from this scan"],
                  inn=["application/pdf", "image/jpeg"], out=["application/json"]),
         ]),

    # ---- Platform / IT --------------------------------------------------
    dict(slug="incident-triage", name="Incident Triage Agent", domain="Platform",
         vendor="Anthropic", model="claude-sonnet-5", team="SRE",
         desc="Classifies production alerts and proposes the matching runbook step.",
         skills=[
             dict(id="classify-alert", name="Classify an alert",
                  desc="Assigns severity and owning team to an inbound monitoring alert.",
                  tags=["sre", "incident", "classification"],
                  examples=["PagerDuty: claims-api p99 latency 4.2s for 10m"],
                  inn=["application/json"], out=["application/json"]),
             dict(id="suggest-runbook", name="Suggest a runbook",
                  desc="Returns the most relevant runbook and the first three steps for an incident.",
                  tags=["sre", "incident", "runbook"],
                  examples=["Elevated 5xx on the policy service"],
                  inn=["text/plain"], out=["text/plain"]),
         ]),
    dict(slug="data-quality", name="Data Quality Agent", domain="Platform",
         vendor="Self-hosted", model="mistral-large", team="Data Engineering",
         desc="Profiles pipeline output and reports drift and schema violations.",
         skills=[
             dict(id="profile-dataset", name="Profile a dataset",
                  desc="Returns null rates, cardinality and distribution shifts for a named table.",
                  tags=["data", "quality", "profiling"],
                  examples=["Profile claims.fact_claim for the last 7 days"],
                  inn=["text/plain"], out=["application/json"]),
         ]),
]


def card(a):
    """A spec-valid A2A 0.3.0 agent card."""
    return {
        "protocolVersion": "0.3.0",
        "name": a["name"],
        "description": a["desc"],
        "url": "%s/%s/" % (SITE, a["slug"]),
        "preferredTransport": "JSONRPC",
        "version": "1.0.0",
        "provider": {
            "organization": "%s — %s" % (a["team"], a["domain"]),
            "url": SITE,
        },
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": s["id"],
                "name": s["name"],
                "description": s["desc"],
                "tags": s["tags"] + [a["vendor"].lower(), a["domain"].lower()],
                "examples": s["examples"],
                "inputModes": s["inn"],
                "outputModes": s["out"],
            }
            for s in a["skills"]
        ],
    }


def main():
    for a in AGENTS:
        d = os.path.join(BASE, a["slug"], ".well-known")
        if os.path.isdir(os.path.join(BASE, a["slug"])):
            shutil.rmtree(os.path.join(BASE, a["slug"]))
        os.makedirs(d)
        for fname in ("agent-card.json", "agent.json"):  # current + legacy path
            with open(os.path.join(d, fname), "w") as fh:
                json.dump(card(a), fh, indent=2)
                fh.write("\n")

    # GitHub Pages runs Jekyll by default, which drops directories beginning
    # with a dot -- including .well-known. This disables it.
    open(os.path.join(BASE, ".nojekyll"), "w").close()

    rows = "\n".join(
        '<tr><td><b>{name}</b><div class="d">{desc}</div></td>'
        '<td>{domain}</td><td>{team}</td><td>{vendor}<div class="d">{model}</div></td>'
        '<td>{nskill}</td>'
        '<td><a href="{slug}/.well-known/agent-card.json"><code>{slug}</code></a></td></tr>'.format(
            name=a["name"], desc=a["desc"], domain=a["domain"], team=a["team"],
            vendor=a["vendor"], model=a["model"], nskill=len(a["skills"]), slug=a["slug"])
        for a in AGENTS
    )
    urls = "\n".join("%s/%s/.well-known/agent-card.json" % (SITE, a["slug"]) for a in AGENTS)
    total_skills = sum(len(a["skills"]) for a in AGENTS)

    html = """<!doctype html>
<meta charset="utf-8">
<title>Agent Cards</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
 :root{{color-scheme:light dark}}
 body{{font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      max-width:1040px;margin:0 auto;padding:40px 24px 80px}}
 h1{{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}}
 p.sub{{color:#667;margin:0 0 28px}}
 table{{border-collapse:collapse;width:100%;font-size:14px}}
 th{{text-align:left;font-size:11px;letter-spacing:.08em;text-transform:uppercase;
     color:#889;border-bottom:1px solid #8884;padding:0 12px 8px 0}}
 td{{border-bottom:1px solid #8882;padding:11px 12px 11px 0;vertical-align:top}}
 .d{{color:#778;font-size:12.5px;margin-top:2px}}
 code{{font:12px ui-monospace,SFMono-Regular,Menlo,monospace}}
 pre{{background:#8881;padding:14px 16px;border-radius:8px;overflow-x:auto;
     font:12px/1.7 ui-monospace,SFMono-Regular,Menlo,monospace}}
 h2{{font-size:15px;margin:38px 0 10px}}
</style>
<h1>Agent Cards</h1>
<p class="sub">{n} A2A agent cards &middot; {s} skills &middot; static fixtures for the Gravitee Agent Catalog.
These are spec-valid cards at stable URLs; the agents behind them are not running.</p>
<table>
<tr><th>Agent</th><th>Domain</th><th>Owner</th><th>Vendor</th><th>Skills</th><th>Card</th></tr>
{rows}
</table>
<h2>Well-known URLs</h2>
<pre>{urls}</pre>
""".format(n=len(AGENTS), s=total_skills, rows=rows, urls=urls)

    with open(os.path.join(BASE, "index.html"), "w") as fh:
        fh.write(html)

    print("%d agents, %d skills" % (len(AGENTS), total_skills))
    for a in AGENTS:
        print("  %-22s %-13s %-24s %d skill(s)" % (a["slug"], a["domain"], a["team"], len(a["skills"])))


if __name__ == "__main__":
    main()
