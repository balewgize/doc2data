# Real documents for demos and evals

Two different jobs:

1. **Demo** — 3–5 documents per vertical that look believable in a screen recording.
2. **Eval** — 20+ documents with known answers so you can report field accuracy.

Do not use real customer documents in the public demo. Use **public templates, public datasets, or synthetic data with realistic layouts**. Keep private documents in a gitignored folder.

---

## E-commerce catalog

| Source | What it is | Use | Notes |
|---|---|---|---|
| [Shopify product CSVs](https://github.com/shopifypartners/product-csvs) | Dummy apparel, home & garden, jewellery catalogs with images | Demo import + export format | Dummy data; great for testing Shopify column mapping |
| [Open Food Facts data](https://world.openfoodfacts.org/data) | Real product names, brands, ingredients, nutrition, images | Eval / normalization | ODbL — attribution required |
| [MAVE](https://github.com/google-research-datasets/mave) | 2.2M product profiles with attribute-value annotations | Eval | Research dataset; check license |
| [Uline catalog (archive.org)](https://archive.org/details/uline-catalog-spring-summer-us-2021) | Real 2021 industrial supplier catalog PDF | Demo PDF layout | Check archive.org terms; use a few pages |
| [GSA Global Supply catalog](https://cmls.gsa.gov/s/publication-details/a12SJ000002RoPNYA0/ca0028251) | Public-sector supply catalog PDF | Demo PDF tables | Public catalog |

**Best demo pack:** one Shopify CSV, one 6–10 page supplier catalog PDF, and one product-data API export.

---

## Finance documents

| Source | What it is | Use | Notes |
|---|---|---|---|
| [invoice2data test invoices](https://github.com/invoice-x/invoice2data/tree/master/tests/compare) | Real invoice PDFs (Amazon, Flipkart, Coolblue, etc.) with expected JSON | **Best eval set** | MIT repo; check test-data provenance before redistributing |
| [DocILE benchmark](https://docile.rossum.ai/) | Invoices, receipts, purchase orders, orders; annotations | Eval | Free token required; dataset terms apply |
| [UK spend over £25k](https://www.gov.uk/government/collections/spend-over-25-000) | Public-sector invoice PDFs | Real layouts | Check each department's redaction; avoid personal data |
| [invoice-generator.com](https://www.invoice-generator.com/) | Generate sample invoices | Demo (synthetic) | Not real transactions |
| [Kaggle invoice datasets](https://www.kaggle.com/datasets/osamahosamabdellatif/high-quality-invoice-images-for-ocr) | Scanned invoice images | OCR/eval | Check each dataset license |

**Best demo pack:** two invoice2data PDFs + one multi-page invoice you generate with a realistic template.

---

## Logistics documents

| Source | What it is | Use | Notes |
|---|---|---|---|
| [VICS Bill of Lading template](https://my.yrc.com/national/pdf/vics-stand.pdf) | Standard blank BOL | Demo template | Fill with synthetic shipment data |
| [CBP Form 7501](https://www.cbp.gov/sites/default/files/assets/documents/2018-Feb/CBP%20Form%207501.pdf) | US customs entry summary | Demo PDF layout | Public government form |
| [invoice2data BOL sample](https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/files/camelot-bol100649863.pdf) | Real-style bill of lading | Demo/eval | MIT repo; check provenance |
| [CORD receipts](https://github.com/clovaai/cord) | Receipt images + annotations | OCR/eval | Research dataset |
| [SROIE receipts](https://github.com/zzzDavid/ICDAR-2019-SROIE) | Scanned receipts + key fields | OCR/eval | Research dataset |

**Best demo pack:** VICS BOL filled with synthetic data + CBP 7501 + one packing list.

---

## Healthcare claims

> Use **synthetic data only**. Never put real PHI in a demo repo, screenshot, or LLM prompt.

| Source | What it is | Use | Notes |
|---|---|---|---|
| [CMS-1500 form](https://www.cms.gov/medicare/cms-forms/cms-forms/downloads/cms1500.pdf) | Professional claim form | Demo template | Public form; fill with synthetic values |
| [CMS SynPUF](https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files) | Synthetic Medicare claims data | Eval | Public synthetic data |
| [Synthea](https://github.com/synthetichealth/synthea) | Synthetic patient generator (CSV/FHIR) | Eval / synthetic records | Apache 2.0 |
| [Sample CMS-1500 + UB-04 forms](https://www.xipere.com/siteassets/hcp/pdf/xipere-sample-claim-forms.pdf) | Filled sample claim forms | Demo layout | Vendor sample; check usage terms |

**Best demo pack:** CMS-1500 filled with synthetic member/claim data + a synthetic EOB generated from the same data.

---

## Cross-vertical document datasets

| Dataset | Documents | Use |
|---|---|---|
| [FUNSD](https://guillaumejaume.github.io/FUNSD/) | Scanned forms | Form understanding / OCR |
| [VRDU](https://github.com/google-research-datasets/VRDU) | Registration forms, vehicle titles, invoices | Structured extraction |
| [Kleister NDA](https://github.com/applicaai/kleister-nda) | NDAs | Contract clause extraction |
| [RVL-CDIP](https://www.cs.cmu.edu/~aharley/rvl-cdip/) | 400k scanned business documents | Classification |

---

## Suggested workflow

```bash
# Public demo pack (gitignored)
./scripts/fetch_demo_docs.sh

# Put private customer docs here, never commit:
demo_docs/private/
```

Then:

1. **Demo** with 3–5 docs per vertical. Use `LLM_PROVIDER=openai` or `ollama` for real extraction.
2. **Eval** with 20+ labeled docs. Store expected JSON next to each document in a private `eval/` folder.
3. **Report** field-level precision/recall, missing-field rate, and cost/latency per document.

## Rules

- **Never commit** customer documents, contracts, invoices, claims, or PII.
- **Redact** names, emails, phone numbers, account numbers, and addresses in screenshots.
- **Check licenses**: ODbL (attribution), MIT, CC BY, research-only datasets.
- **Scanned PDFs need OCR**; Paperlane currently reads embedded text only.
- **Government forms are public**, but filled examples may contain real data. Use blank templates and synthetic values.
