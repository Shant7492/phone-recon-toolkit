# numscope

Offline-first phone number reconnaissance and metadata analysis for OSINT
and security research. Zero cost, no mandatory API keys, no scraping.

> **Read the [Legal & Ethical Disclaimer](#legal--ethical-disclaimer) before use.**

## What it does

| Module | Network? | What you get |
|---|---|---|
| **Offline metadata** (`core/analyzer.py`) | No | E.164 / international / national / RFC 3966 formats, validity, possibility (with reason), line type, *original* carrier, region, country, time zones |
| **Dork generator** (`modules/dorks.py`) | No | Ready-to-run queries plus clickable Google / DuckDuckGo / Bing URLs across 9 categories |
| **Risk heuristics** (`modules/risk.py`) | No | 0-100 score where every point maps to a named, explained factor |
| **Providers** (`modules/providers/`) | Optional | Pluggable free-tier APIs. Numverify ships built in. Silently skipped when no key is set |

The tool never fetches search-engine results pages. It only builds queries;
you decide which ones to open.

## Installation

Requires Python 3.9+.

```bash
git clone https://github.com/<you>/numscope.git
cd numscope
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Optional API keys:

```bash
cp .env.example .env             # then edit .env
```

## Usage

```bash
python cli.py "+1 415 555 2671"
python cli.py 02083661177 --region GB
python cli.py "+442083661177" --offline --format json -o result.json
python cli.py -f targets.txt --categories paste,documents --engines google,bing
```

Always prefer international format (`+<country code>...`). National-format
numbers need `--region`.

### Flags

| Flag | Description |
|---|---|
| `NUMBER ...` | One or more numbers |
| `-f, --file PATH` | File with one number per line (`#` comments allowed) |
| `-r, --region CC` | ISO country code used to parse national-format numbers and as the "home" region for the international-origin check |
| `--offline` | Guarantees zero network calls (disables all providers) |
| `--provider NAME` | Limit to a provider (repeatable). Currently: `numverify` |
| `--no-dorks` | Skip query generation |
| `--no-risk` | Skip risk scoring |
| `--categories LIST` | Comma list: `general, documents, paste, code, directories, social, messaging, classifieds, reputation` |
| `--engines LIST` | Comma list: `google, duckduckgo, bing` (default all) |
| `--format {table,plain,json}` | Output format (default `table`) |
| `-o, --output PATH` | Write to file (`table` falls back to `plain`) |
| `--env-file PATH` | Load a specific `.env` |
| `--no-banner` | Hide the usage notice (printed to stderr) |
| `-v, --verbose` | Debug logging and provider-skip info |
| `--version` | Print version |

Banner, warnings and logs go to **stderr**, so `--format json` on stdout is
always clean and pipeable.

## Optional providers

Copy `.env.example` to `.env`:

```dotenv
NUMVERIFY_API_KEY=your_key_here
NUMVERIFY_ALLOW_HTTP=false
HTTP_TIMEOUT=10
```

- No key means the provider is skipped. Nothing breaks.
- Numverify free plans have historically been HTTP-only. numverify.py uses
  HTTPS and **never silently downgrades**. If the API answers with error 105,
  the tool tells you how to opt in with `NUMVERIFY_ALLOW_HTTP=true`, at the
  cost of sending the key unencrypted.
- API keys are scrubbed from error messages.
- Providers are only called for numbers that pass the offline "possible" check,
  to save your quota.
- **Privacy:** when a provider runs, the number is sent to that third party.
  Use `--offline` when that is not acceptable.
- Verify the provider's current free-tier limits and terms yourself; they change.

### Adding a provider

1. Create `modules/providers/yourservice.py` subclassing `BaseProvider`
   (`name`, `is_configured()`, `lookup(meta) -> ProviderResult`).
2. Add config fields in `core/config.py`.
3. Add the class to `_CLASSES` in `modules/providers/__init__.py`.

`lookup` must return a `ProviderResult` for expected failures. The CLI also
catches unexpected exceptions so a plugin can never crash a scan.

## Web app & deployment

The same engine is available as a small FastAPI web app (`web/`): enter a
number, get metadata, risk heuristics and search links. Vanilla JS front end,
strict CSP, no cookies, no database.

### Run locally

```bash
pip install -r requirements-web.txt
uvicorn web.app:app --reload --port 8000     # http://localhost:8000
```

### Deploy with Docker

```bash
docker build -t numscope .
docker run --rm -p 8000:8000 -e TRUST_PROXY_HOPS=0 numscope
```

### Deploy on Render (free tier, no card at time of writing)

1. Push the repo to GitHub.
2. Render dashboard: **New > Blueprint**, select the repo. `render.yaml` does the rest.
3. Open the generated `https://<name>.onrender.com` URL.

Free instances sleep after inactivity, so the first request can be slow.
Check Render's current free-tier terms before relying on them. Any Docker host
works too (Fly.io, Railway, Hugging Face Spaces Docker SDK: set `PORT=7860`
there). `TRUST_PROXY_HOPS` must match the number of proxies in front of you,
or per-IP rate limiting will be wrong or spoofable.

### Web configuration

| Variable | Default | Purpose |
|---|---|---|
| `WEB_RATE_LIMIT` / `WEB_RATE_WINDOW` | 10 / 60 | Requests per IP per window (seconds) |
| `WEB_GLOBAL_LIMIT` | 120 | Requests per window across all users |
| `WEB_ENABLE_PROVIDERS` | false | Let the public site call Numverify |
| `WEB_DAILY_PROVIDER_CAP` | 50 | Max provider calls per UTC day |
| `TRUST_PROXY_HOPS` | 0 | Reverse-proxy hops (1 on most PaaS) |

### Operator responsibilities

- Rate limits are in-memory and per process. Run one worker, or add Redis.
- The app keeps no number logs and uvicorn runs with `--no-access-log`.
  If your host or CDN logs request bodies, that is outside this app's control.
- Running a public lookup service makes you the operator of a data-processing
  tool. Review the privacy law of your jurisdiction and add your own
  contact/abuse address to the footer in `web/static/index.html`.
- Keep `WEB_ENABLE_PROVIDERS=false` unless you have read Numverify's terms:
  every visitor's number would be forwarded to them using your key.

## Risk scoring

Score = sum of factor points, capped at 100. Levels: `LOW` <20,
`MEDIUM` 20-44, `HIGH` 45-69, `CRITICAL` 70+. Weights live at the top of
`modules/risk.py`.

| Factor | Points |
|---|---|
| Unparseable (malformed) / impossible length / unallocated range | 45 / 40 / 30 |
| Line type: premium-rate / VoIP / voicemail / shared-cost / personal / toll-free / UAN / pager / unknown | 35 / 25 / 15 / 15 / 12 / 10 / 10 / 8 / 8 |
| Non-geographic country code (+800, +882...) | 15 |
| International origin relative to `--region` | 5 |
| Caribbean NANP callback-scam area code / callback-scam country code | 10 / 8 |
| Too few digits (<7) / too many (>15), unparseable input only | 20 / 25 |
| Repeated, sequential or 1-2-digit patterns | 12 |
| Provider says invalid while offline says valid | 5 |

### Known limitations (read these)

- **The score is a heuristic, not ground truth.** It has not been validated
  against labelled fraud data. Vanity and "golden" numbers can trigger the
  pattern factor.
- **VoIP detection is only as good as the numbering plan.** libphonenumber
  marks VoIP ranges in some countries (e.g. UK `056`) but classifies all `+1`
  numbers as `FIXED_LINE_OR_MOBILE`. For US/Canada numbers, VoIP cannot be
  detected offline and the tool says so.
- **Carrier = original allocation.** Number porting is invisible offline, and
  carrier data is mostly published for mobile ranges only.
- **Missing country code is not penalised.** If you omit `+CC` and `--region`,
  validity, line-type and origin checks are skipped, and the report says so.
- The callback-scam lists are illustrative and editable. Treat them as weak signals.

## Dork categories

`general`, `documents`, `paste`, `code`, `directories` (region-aware),
`social`, `messaging` (public WhatsApp click-to-chat links), `classifieds`,
`reputation` (spam/scam report sites and keywords).

Search engines are inconsistent about punctuation, so queries OR together
several formats of the same number. Absence of results proves nothing:
engines index only a slice of the web, and most social platforms do not
expose phone numbers to crawlers.

## Project layout

```
numscope/
├── cli.py                      # argparse entry point
├── core/
│   ├── pipeline.py             # shared scan pipeline (CLI + web)
│   ├── analyzer.py             # offline phonenumbers engine
│   ├── config.py               # .env / environment loading
│   ├── models.py               # dataclasses
│   └── report.py               # rich / plain / JSON renderers
├── modules/
│   ├── dorks.py                # query generation
│   ├── risk.py                 # heuristic scoring
│   └── providers/
│       ├── base.py             # provider interface
│       └── numverify.py        # optional free-tier API
├── web/                        # FastAPI app, rate limiter, static front end
│   ├── app.py  ratelimit.py  settings.py
│   └── static/  index.html  app.js  style.css
├── tests/                      # offline tests (core + web)
├── Dockerfile  .dockerignore  render.yaml
├── .env.example
├── requirements.txt
├── requirements-web.txt
└── requirements-dev.txt
```

## Development

```bash
pip install -r requirements-dev.txt
pytest
flake8 --max-line-length=88 .
```

## Legal & Ethical Disclaimer

numscope is provided for **lawful, authorised** purposes such as security
research, fraud and spam triage, verifying your own or your organisation's
numbers, and journalism or academic work that complies with applicable law
and ethics rules.

- **Do not** use this tool to stalk, harass, threaten, dox, or profile
  private individuals, or to gather data for any unlawful purpose.
- The tool does not scrape private endpoints, bypass authentication or
  platform security, or use leaked credentials. Contributions adding such
  capabilities will be rejected.
- Phone numbers are personal data in many jurisdictions (e.g. GDPR, UK GDPR,
  CCPA/CPRA, India's DPDP Act). Having a lawful basis, minimising retention,
  and securing any saved reports is **your** responsibility.
- Output is probabilistic. Do not treat risk scores or search hits as proof of
  identity, ownership or wrongdoing, and do not take action against a person
  based solely on this tool.
- Third-party services (search engines, Numverify) have their own terms.
  Follow them.
- The software is provided "as is" without warranty. The authors accept no
  liability for misuse or for any damages arising from its use.

## License

MIT. See `LICENSE`.
