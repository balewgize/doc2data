# Doc2Data

**Documents in. Clean data out.**

Doc2Data turns supplier catalogs, invoices, shipment notes and healthcare claims into
validated, structured records — then exports an import-ready CSV. One shared extraction
engine, multiple industry configurations.

Built on [fastapi-nextjs-starter](https://github.com/balewgize/fastapi-nextjs-starter):
FastAPI + Next.js, Dockerized, Vercel-ready.

This is a portfolio project: an end-to-end workflow demo, not a production service.

![Doc2Data review screen](docs/screenshot.png)

---

## The problem

Every operations team has someone retyping data from PDFs, spreadsheets and emails into
Shopify, an ERP, a ledger or a warehouse system. It is slow, error-prone and expensive.
Generic "chat with your PDF" tools do not solve it because the hard part is not reading
the document — it is **getting a clean, validated record into the system of record**.

Doc2Data is the workflow layer:

1. Upload a document (PDF, XLSX, CSV, TXT, MD, JSON).
2. Pick the industry schema.
3. Extract structured fields with an LLM (or the offline mock).
4. Normalize units, currencies, prices and dimensions.
5. Validate required fields, duplicates, totals and cross-field rules.
6. Review the exceptions in a human-in-the-loop screen.
7. Export Shopify CSV or a generic industry CSV.

The core pipeline is shared. Adding an industry means adding a schema, a prompt and an
export mapping — not a new app.

## Verticals

| Industry | Status | Output |
|---|---|---|
| E-commerce catalog | **Live** | Shopify product import CSV |
| Finance documents | **Live** | Generic invoice CSV |
| Logistics documents | **Live** | Generic shipment CSV |
| Healthcare claims | **Live** | Generic claim-line CSV (administrative only) |

All four verticals share the same extraction, normalization, validation and export
pipeline. E-commerce is the reference implementation.

## Demo flow

1. Start the app.
2. Click **Try the sample**.
3. See 3 records, a duplicate warning and a missing-price error.
4. Download the Shopify CSV.
5. Switch verticals and click **Try public invoice / BOL / claim** (or **catalog**) to
   load a bundled result from a real public document.

The default provider is `mock`, a deterministic parser for the synthetic samples. The
public-sample buttons also work offline by loading bundled demo results from
`sample_data/real_results/`. Set `LLM_PROVIDER=openai` or `LLM_PROVIDER=ollama` to run
the original documents live.

## Real documents for demos and evals

See [docs/REAL_DOCS.md](docs/REAL_DOCS.md) for public samples, open datasets, and
licensing notes for each vertical.

```bash
./scripts/fetch_demo_docs.sh   # downloads a small public pack into demo_docs/ (gitignored)
```

Use **public templates or synthetic data** for the demo. Keep customer documents in
`demo_docs/private/` and never commit them.

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

The bundled public samples are a Shopify catalog, AWS invoice, VICS BOL and CMS-1500
claim. The invoice and BOL were verified with `gemma3:1b` locally; a frontier model
will handle messier documents better.

If `LLM_PROVIDER` is unset, the app uses OpenAI when `OPENAI_API_KEY` exists, otherwise
the mock.

---

## Architecture

```
Next.js UI
   │  multipart upload
   ▼
FastAPI  /api/doc2data
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
| `backend/app/doc2data/verticals.py` | Industry configs + dynamic Pydantic schemas |
| `backend/app/doc2data/extract.py` | Read, chunk, call provider, normalize, validate, dedupe |
| `backend/app/doc2data/normalize.py` | Money, weight, dimensions and currency parsing |
| `backend/app/doc2data/validate.py` | Cross-field business rules and review notes |
| `backend/app/doc2data/export.py` | Shopify CSV + generic industry CSV |
| `backend/app/doc2data/llm.py` | Mock, OpenAI and Ollama providers |
| `backend/app/doc2data/storage.py` | SQLite run history |
| `backend/app/routers/doc2data.py` | API routes |

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/doc2data/verticals` | Available industry schemas |
| POST | `/api/doc2data/extract` | Upload a document (`file`, `vertical`) |
| POST | `/api/doc2data/extract/sample?vertical=ecommerce` | Run bundled sample |
| GET | `/api/doc2data/runs` | Recent runs |
| GET | `/api/doc2data/runs/{id}` | Full run + records + warnings |
| GET | `/api/doc2data/runs/{id}/export.csv` | Download CSV |
| GET | `/api/doc2data/health` | Provider, verticals, database |

## Adding an industry

Add one `VerticalConfig` in `backend/app/doc2data/verticals.py`:

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
make test        # backend: 47 tests
make check       # backend tests + frontend production build
```

## Current limitations

- Scanned PDFs need OCR before upload; the app reads embedded text only.
- E-commerce models one record per SKU; variant axes are not split yet.
- Shopify export creates draft products; images are referenced, not uploaded.
- Prompts are tuned on the bundled public samples; accuracy on arbitrary documents
  still depends on the model.
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
