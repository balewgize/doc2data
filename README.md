# DocuBridge

**Documents in. Clean data out.**

DocuBridge turns supplier catalogs, invoices, shipment notes and healthcare claims into
validated, structured records — then exports an import-ready CSV. One shared extraction
engine, multiple industry configurations.

Built on [fastapi-nextjs-starter](https://github.com/balewgize/fastapi-nextjs-starter):
FastAPI + Next.js, Dockerized, Vercel-ready.

![DocuBridge review screen](docs/screenshot.png)

---

## The problem

Every operations team has someone retyping data from PDFs, spreadsheets and emails into
Shopify, an ERP, a ledger or a warehouse system. It is slow, error-prone and expensive.
Generic "chat with your PDF" tools do not solve it because the hard part is not reading
the document — it is **getting a clean, validated record into the system of record**.

DocuBridge is the workflow layer:

1. Upload a document (PDF, XLSX, CSV, TXT, MD, JSON).
2. Pick the industry schema.
3. Extract structured fields with an LLM (or the offline mock).
4. Normalize units, currencies, prices and dimensions.
5. Validate required fields, duplicates, totals and cross-field rules.
6. Review the exceptions in a human-in-the-loop screen.
7. Export Shopify CSV or a generic industry CSV.

The core pipeline is shared. Adding an industry means adding a schema, a prompt and an
export mapping — not a new app.

## Current MVP

| Industry | Status | Output |
|---|---|---|
| E-commerce catalog | **Live** | Shopify product import CSV |
| Finance documents | Beta | Generic invoice CSV |
| Logistics documents | Beta | Generic shipment CSV |
| Healthcare claims | Beta | Generic claim-line CSV (administrative only) |

"Beta" means the config and pipeline work, but the prompts have not been tuned on a large
set of real documents yet. E-commerce is the reference vertical.

## Demo flow

1. Start the app.
2. Click **Try the sample**.
3. See 3 records, a duplicate warning and a missing-price error.
4. Download the Shopify CSV.

The default provider is `mock`, a deterministic parser for the bundled samples. It works
offline with no API key. Real PDFs need OpenAI or Ollama.

---

## Quick start

### Native

```bash
cp .env.example .env

# Terminal 1 - backend
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 - frontend
cd frontend
pnpm install
pnpm dev -p 3000
```

Open <http://localhost:3000> and <http://localhost:8000/docs>.

### Docker

```bash
cp .env.example .env
make up          # dev, hot reload
make prod        # production build
make down
```

### Real extraction

**OpenAI**

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

**Ollama (local)**

```bash
ollama pull llama3.2
```

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.2
```

In Docker, point `OLLAMA_BASE_URL` at `http://host.docker.internal:11434/v1`.

If `LLM_PROVIDER` is unset, the app uses OpenAI when `OPENAI_API_KEY` exists, otherwise
the mock.

---

## Architecture

```
Next.js UI
   │  multipart upload
   ▼
FastAPI  /api/docpipe
   │
   ▼
Extraction pipeline
   read → chunk → LLM → normalize → validate → dedupe
   │
   ├── verticals/ecommerce   schema + prompt + Shopify export
   ├── verticals/finance     schema + prompt + generic CSV
   ├── verticals/logistics   schema + prompt + generic CSV
   └── verticals/healthcare  schema + prompt + generic CSV
   │
   ▼
SQLite run history          →  review screen  →  CSV download
```

Key modules:

| Path | Responsibility |
|---|---|
| `backend/app/docpipe/verticals.py` | Industry configs + dynamic Pydantic schemas |
| `backend/app/docpipe/extract.py` | Read, chunk, call provider, normalize, validate, dedupe |
| `backend/app/docpipe/normalize.py` | Money, weight, dimensions and currency parsing |
| `backend/app/docpipe/validate.py` | Cross-field business rules and review notes |
| `backend/app/docpipe/export.py` | Shopify CSV + generic industry CSV |
| `backend/app/docpipe/llm.py` | Mock, OpenAI and Ollama providers |
| `backend/app/docpipe/storage.py` | SQLite run history |
| `backend/app/routers/docpipe.py` | API routes |

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/docpipe/verticals` | Available industry schemas |
| POST | `/api/docpipe/extract` | Upload a document (`file`, `vertical`) |
| POST | `/api/docpipe/extract/sample?vertical=ecommerce` | Run bundled sample |
| GET | `/api/docpipe/runs` | Recent runs |
| GET | `/api/docpipe/runs/{id}` | Full run + records + warnings |
| GET | `/api/docpipe/runs/{id}/export.csv` | Download CSV |
| GET | `/api/docpipe/health` | Provider, verticals, database |

## Adding an industry

Add one `VerticalConfig` in `backend/app/docpipe/verticals.py`:

```python
INSURANCE = VerticalConfig(
    id="insurance",
    label="Insurance documents",
    description="Claims and policy documents -> structured claim records.",
    record_noun="claim",
    dedupe_key="claim_number",
    sample_file="sample_claim.txt",
    fields=(
        FieldSpec("claim_number", "Claim number", required=True),
        FieldSpec("policy_number", "Policy number"),
        FieldSpec("loss_date", "Loss date"),
        FieldSpec("amount", "Amount", type="decimal", normalizer="price"),
    ),
    system_prompt="Extract insurance claim records. Do not invent values.",
    export_columns=(("Claim Number", "claim_number"), ("Amount", "amount")),
)
```

Register it in `VERTICALS`. The pipeline, API, UI and CSV export pick it up automatically.

## Tests

```bash
make test        # backend: 36 tests
make check       # backend tests + frontend production build
```

## Current limitations

- Scanned PDFs need OCR before upload; the MVP reads embedded text only.
- E-commerce models one record per SKU; variant axes are not split yet.
- Shopify export creates draft products; images are referenced, not uploaded.
- Finance, logistics and healthcare prompts are beta and need real-document tuning.
- SQLite is single-instance. Production needs Postgres/Supabase, object storage and a job queue.
- No auth, workspaces or billing yet.
- LLM output is validated, not guaranteed. The review screen is the control.

## Roadmap

1. Auth + workspaces (the starter's Supabase wiring is already in place).
2. Postgres/Supabase storage + object storage for source files.
3. Background jobs with retries and per-chunk progress.
4. Shopify API sync and image upload.
5. Eval harness: labeled documents per vertical, field accuracy, fix acceptance rate.
6. Correction capture: turn human edits into eval data and prompt improvements.
7. Deploy on Vercel Services + a managed Postgres.

## Commercial shape

- **Productized service:** supplier catalog → Shopify import (`$0.50–2/SKU`), invoice
  extraction, shipment data cleanup.
- **SaaS:** per-document pricing, then per-seat with review workflows.
- **Vertical templates:** the same engine sold as an e-commerce, finance, logistics or
  healthcare data pipeline.

## Credits

- Starter: [balewgize/fastapi-nextjs-starter](https://github.com/balewgize/fastapi-nextjs-starter)
- Extraction seed: community contributions in the LLM Engineering course repo
  (`wk1-day1-datasheet_comparator.ipynb`, `Recipe_Nutrition_Calculator/`,
  `hmnhGeek_day5_streamlit_brochure_web_app/`).
