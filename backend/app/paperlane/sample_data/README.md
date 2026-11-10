# Bundled sample documents

These files power the **Try the sample** and **Try real invoice / BOL** buttons.

| File | Type | Source / notes |
|---|---|---|
| `sample_supplier_catalog.pdf` / `.txt` | Synthetic | Fictional coffee catalog. Works with the offline mock. |
| `sample_invoice.txt` | Synthetic | Fictional invoices. Works with the offline mock. |
| `sample_shipment.txt` | Synthetic | Fictional shipments. Works with the offline mock. |
| `sample_claim.txt` | Synthetic | Fictional claim lines. Works with the offline mock. |
| `sample_catalog_public.csv` | Public dummy data | [Shopify product CSVs](https://github.com/shopifypartners/product-csvs) home-and-garden sample. No real customer data. |
| `sample_invoice_public.pdf` | Public + synthetic | AWS invoice from the [invoice2data test fixtures](https://github.com/invoice-x/invoice2data/tree/master/tests/compare). Account number and bill-to fields were redacted and replaced with synthetic values. No customer data is included. |
| `sample_bol_public.pdf` | Public template + synthetic data | [VICS Bill of Lading template](https://my.yrc.com/national/pdf/vics-stand.pdf) filled with a fictional shipment. Page 1 is a machine-readable shipment summary; page 2 is the filled VICS form. |
| `sample_claim_public.pdf` | Public form + synthetic data | [CMS-1500 form](https://www.cms.gov/medicare/cms-forms/cms-forms/downloads/cms1500.pdf) with a synthetic administrative claim summary. No PHI. |

No customer or patient data is included. The public invoice/BOL samples are for
layout and extraction demos only. Check the upstream licenses before redistributing.
