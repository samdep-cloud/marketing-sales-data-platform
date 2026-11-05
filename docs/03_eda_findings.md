# Source Data Assessment

**Scope:** Close CRM, lead-owner lookup, Calendly, Wistia, and marketing spend data.

**Purpose:** Identify source-data characteristics, integration requirements, and quality considerations that inform ingestion, transformation, and downstream analytical modeling.

## 1. Close CRM & Lead Enrichment

| Finding | Observation | Design Implication |
|---|---|---|
| Lead enrichment relationship | Close CRM events and lead-owner lookup records share `lead_id`. The lookup supplies email, lead owner, and funnel attributes. | Use `lead_id` to associate CRM events with lookup records during delayed enrichment. |
| Overlapping attributes | Both sources contain lead name, creation date, and status. These attributes match in the examined samples. | Use Close CRM as the authoritative source for these fields and the lookup for additional enrichment attributes. |
| Event and lead identifiers | Close events contain distinct event and lead identifiers, along with object type and action. | Filter for relevant lead-creation events. Distinguish event-level identifiers from lead-level identifiers when designing deduplication and storage. |
| Funnel attribution | Close contains a funnel value under an opaque custom-field identifier; the lookup exposes a named `funnel` attribute. | Use the lookup's named field for enrichment and preserve the original custom field in Bronze for traceability. |

## 2. Calendly

| Finding | Observation | Design Implication |
|---|---|---|
| Nested event structure | Webhook payloads contain invitee attributes, scheduled-event details, and employee assignments in nested objects and arrays. | Flatten relevant attributes into a structured bookings dataset for downstream analysis. |
| Booking identifiers and updates | Invitee records include unique identifiers and update timestamps. | Deduplicate by invitee ID, retaining the most recently updated record. |
| Attribution limitations | UTM tracking fields were null in examined payloads. | Avoid assuming campaign attribution from missing tracking values. Validate alternative channel mappings before calculating channel-level performance. |
| Meeting assignment | Scheduled events include employee membership information. | Support scheduled meeting-load reporting by assigned Calendly user; distinguish scheduled bookings from confirmed attendance. |

## 3. Wistia

| Finding | Observation | Design Implication |
|---|---|---|
| Multiple data structures | Wistia provides media metadata, aggregate video statistics, and individual visitor engagement events. | Model media, statistics, and visitors as separate Silver datasets. |
| Cumulative statistics | Video statistics such as plays, loads, and watch time represent cumulative measurements. | Retain the latest snapshot per video rather than summing snapshots across ingestion runs. |
| Overlapping visitor windows | Rolling ingestion windows can retrieve previously collected visitor events. | Deduplicate engagement records using event identifiers to avoid inflated activity counts. |
| Visitor-level attributes | Engagement records include visitor identifiers, timestamps, viewing percentages, and device information. | Preserve useful engagement attributes while excluding unnecessary identifying information from Silver. |

## 4. Marketing Spend

| Finding | Observation | Design Implication |
|---|---|---|
| Reporting granularity | Spend records contain reporting date, marketing channel, and spend amount. | Model spend at the date/channel grain. |
| Overlapping source files | Source files can contain multiple reporting dates, with overlapping periods across ingestion runs. | Deduplicate records using date and channel. |
| Conflicting values | Multiple records could contain different spend amounts for the same date/channel combination. | Validate conflicting values rather than arbitrarily selecting a spend amount. |
| Attribution granularity | Spend data is available at the channel level, without campaign-level identifiers. | Limit cost-per-booking calculations to channels with a defensible booking attribution mapping. |

## 5. Cross-Source Modeling Considerations

The sources represent different stages of the marketing and sales process:

- **Marketing spend:** Acquisition investment by channel and date.
- **Wistia:** Video consumption and visitor engagement.
- **Close CRM:** Lead creation, ownership, and funnel information.
- **Calendly:** Scheduled bookings and employee assignments.

These datasets support marketing funnel analysis, but their identifiers and reporting grains are not universally aligned.

Downstream models should preserve source-specific identifiers, distinguish observed relationships from inferred attribution, and avoid implying individual-level conversion paths where reliable joins are unavailable.

## Summary

The assessment informed several implementation decisions:

- Event-driven ingestion and delayed enrichment for Close CRM.
- Flattening and deduplication of Calendly booking records.
- Snapshot handling and visitor-event deduplication for Wistia.
- Date/channel deduplication and conflict validation for marketing spend.
- Explicit treatment of attribution limitations in downstream reporting.

These decisions are reflected in the Bronze and Silver processing workflows.