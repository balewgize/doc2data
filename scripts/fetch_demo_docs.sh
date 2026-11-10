#!/usr/bin/env bash
# Download a small pack of public demo documents.
#
# These are public samples/templates, not customer data. The folder is
# gitignored. Check each source's license before redistributing.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${ROOT}/demo_docs"
mkdir -p "${DEST}/ecommerce" "${DEST}/finance" "${DEST}/logistics" "${DEST}/healthcare"

fetch() {
  local url="$1"
  local out="$2"
  echo "→ ${out#${ROOT}/}"
  curl -L --fail --silent --show-error "$url" -o "$out"
}

# E-commerce: Shopify's public dummy catalog CSV.
fetch \
  "https://raw.githubusercontent.com/shopifypartners/product-csvs/master/home-and-garden.csv" \
  "${DEST}/ecommerce/shopify-home-and-garden.csv"

# Finance: real invoice PDFs + expected JSON from the invoice2data test suite.
fetch \
  "https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/AmazonWebServices.pdf" \
  "${DEST}/finance/AmazonWebServices.pdf"
fetch \
  "https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/AmazonWebServices.json" \
  "${DEST}/finance/AmazonWebServices.json"
fetch \
  "https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/FlipkartInvoice.pdf" \
  "${DEST}/finance/FlipkartInvoice.pdf"
fetch \
  "https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/FlipkartInvoice.json" \
  "${DEST}/finance/FlipkartInvoice.json"

# Logistics: standard VICS bill of lading, CBP entry summary, and a BOL sample.
fetch \
  "https://my.yrc.com/national/pdf/vics-stand.pdf" \
  "${DEST}/logistics/vics-bill-of-lading.pdf"
fetch \
  "https://www.cbp.gov/sites/default/files/assets/documents/2018-Feb/CBP%20Form%207501.pdf" \
  "${DEST}/logistics/cbp-form-7501.pdf"
fetch \
  "https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/files/camelot-bol100649863.pdf" \
  "${DEST}/logistics/bill-of-lading-sample.pdf"

# Healthcare: blank CMS-1500 form. Fill it with synthetic values for demos.
fetch \
  "https://www.cms.gov/medicare/cms-forms/cms-forms/downloads/cms1500.pdf" \
  "${DEST}/healthcare/cms-1500.pdf"

echo
echo "Downloaded to ${DEST}"
echo "Next: fill the templates with synthetic data, then run Paperlane with LLM_PROVIDER=openai or ollama."
