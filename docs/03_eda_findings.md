# Source Data Assessment

**Scope:** Close CRM webhook events, lead-owner lookup data, and their enrichment relationship.
**Purpose:** Identify source-data considerations that affect event ingestion, delayed lead enrichment, and downstream analytical modeling. Supporting analysis is available in the EDA notebooks.

## Findings

| Finding | Observation | Design Implication |
|---|---|---|
| **001 — Lead Enrichment Relationship** | The Close event and `lead-owner` lookup share `lead_id`. The lookup supplies `lead_email`, `lead_owner`, and `funnel`, which are needed for the enriched lead record. | Use `lead_id` to retrieve and validate the corresponding owner record after the required delay. Preserve the enriched attributes for notifications and downstream analytics. |
| **002 — Overlapping Lead Attributes** | `display_name`, `date_created`, and `status_label` are present in both sources and match in the supplied samples. | Define Close CRM as the source for these notification attributes and use the lead-owner lookup to supply `lead_email`, `lead_owner`, and `funnel`. *Do not rely on overlapping fields always matching - need to account for that. |
| **003 — Overlapping Lead Attributes** | The Close payload contains distinct event.id and event.lead_id identifiers, along with object_type and action. | Filter for lead-creation events. Use event.id for event-level deduplication and lead_id for owner enrichment and lead-level storage. |
| **004 — Funnel Attribution Field** | The Close CRM payload contains DE ACADEMY Direct VSL under an opaque custom-field ID. The lead-owner lookup contains the same value under funnel. | Use the lookup's named funnel attribute for the required enrichment. Preserve the original Close custom field in raw data; confirm its business definition before mapping it into the analytical model. |


