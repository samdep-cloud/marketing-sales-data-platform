# Marketing–Sales Data Platform — Architecture

## 1. Overview

The Marketing–Sales Data Platform is an AWS-based, event-driven data engineering project that integrates CRM, scheduling, video engagement, and advertising spend data into a centralized S3 data lake.

The platform supports lead enrichment, operational notifications, data standardization, and downstream analytics. It combines webhook-driven ingestion with scheduled API extraction and uses PySpark to transform raw source data into structured Parquet datasets.

The implementation uses a Bronze/Silver architecture, with Gold-level reporting and dashboard capabilities planned as subsequent extensions.

## 2. Data Sources

| Source | Data | Ingestion Method |
|---|---|---|
| Close CRM | Lead creation events and CRM attributes | Webhook → API Gateway → Lambda |
| Calendly | Booking and invitee events | Webhook → API Gateway → Lambda |
| Wistia | Video metadata, cumulative engagement statistics, and visitor events | Scheduled AWS Glue Python Shell job |
| Advertising spend | Channel-level advertising expenditure | Scheduled AWS Glue Python Shell job |
| Lead-owner lookup | Lead ownership, email, and funnel attributes | External HTTP lookup during enrichment |

The platform integrates sources with different update frequencies, event structures, and data delivery mechanisms.

## 3. Ingestion and Enrichment

### Close CRM

1. Close sends a lead-creation webhook to Amazon API Gateway.
2. A Lambda function validates the event type and writes the original payload to S3 Bronze.
3. The Lambda publishes a message to Amazon SQS with a 600-second delivery delay.
4. A second Lambda consumes the message and retrieves the original CRM event.
5. The enrichment Lambda requests additional lead-owner and funnel attributes from an external source.
6. The enriched lead is saved to a separate S3 bucket.
7. A Slack webhook sends an operational notification containing lead details.

The delay accommodates the asynchronous availability of external enrichment data. The workflow separates initial event capture from downstream processing.

### Calendly

Calendly booking events are delivered through API Gateway to a Lambda function.

The Lambda processes `invitee.created` events, extracts the invitee identifier, and saves the original JSON payload to S3 Bronze.

### Wistia

A scheduled Glue Python Shell job retrieves video metadata, cumulative engagement statistics, and visitor events from the Wistia API.

The ingestion process uses an API token stored in AWS Secrets Manager for deployed execution. Visitor events are retrieved using an overlapping two-day extraction window to reduce the risk of missing recently available events.

Raw responses are stored in separate Bronze prefixes for media, statistics, and visitors.

### Advertising Spend

A scheduled Glue Python Shell job retrieves a file index from an external source and downloads JSON spend records.

Before downloading each file, the job checks whether the corresponding S3 Bronze object already exists. Existing files are skipped to avoid redundant ingestion.

## 4. Storage and Transformation

### Bronze Layer

Amazon S3 retains source-oriented JSON records, preserving the original payload structure for inspection and reprocessing.

Bronze datasets are organized by source:

```text
bronze/
├── close/
├── calendly/
├── spend/
└── wistia/
    ├── media/
    ├── stats/
    └── visitors/
```

Enriched Close records are stored in a separate S3 bucket and serve as the input to the Close Silver transformation.

### Silver Layer

AWS Glue Spark jobs use PySpark to read Bronze records, standardize fields and types, apply deduplication rules, and write Parquet datasets.

| Dataset | Transformation |
|---|---|
| Close leads | Normalizes CRM and enrichment attributes, removes exact duplicates, and detects conflicting lead records |
| Calendly bookings | Extracts booking attributes, normalizes emails and timestamps, and retains the latest record per invitee |
| Advertising spend | Standardizes dates, channels, and monetary values; removes duplicates and detects conflicting spend amounts |
| Wistia media | Retains the latest metadata record per video |
| Wistia statistics | Retains the latest cumulative snapshot per video rather than summing cumulative values |
| Wistia visitors | Deduplicates overlapping visitor events by media and event identifier |

Silver outputs are written to:

```text
silver/
├── close/leads/
├── calendly/bookings/
├── spend/
└── wistia/
    ├── media/
    ├── stats/
    └── visitors/
```

The current transformations use full-refresh Parquet writes. Where uniqueness assumptions are violated, selected jobs raise explicit errors rather than silently choosing conflicting values.

## 5. Orchestration and CI/CD

The platform combines event-driven and scheduled execution.

- **Event-driven:** API Gateway, Lambda, and SQS support CRM and scheduling workflows.
- **Scheduled:** Glue Python Shell jobs retrieve advertising spend and Wistia data.
- **Transformations:** Glue Spark jobs execute PySpark Silver processing.

The source repository is connected to AWS CodePipeline and CodeBuild.

On deployment, CodeBuild synchronizes Python source files to the S3 `scripts/` prefix. Glue jobs configured to use those script locations can execute the updated code on subsequent runs.

Lambda functions currently use separately deployed code packages. Automated Lambda packaging and `update-function-code` deployment are documented as a future CI/CD enhancement.

The current build process does not provision AWS infrastructure or automatically deploy Lambda packages.

## 6. Security and Configuration

The implementation separates source code from runtime configuration and credentials.

- Lambda environment variables provide bucket, queue, lookup, and notification configuration.
- AWS Secrets Manager stores the deployed Wistia API token.
- AWS IAM roles govern service access to AWS resources.
- Local `.env` files and potentially sensitive source samples are excluded from Git.
- `.env.example` documents configuration placeholders without including actual credentials.

The platform uses external webhook endpoints and source integrations. Production hardening would require reviewing webhook authentication, source-system permissions, secret management, and access controls against the requirements of the deploying organization.

## 7. Design Decisions and Known Limitations

**Event-driven ingestion:** Webhooks reduce the need for polling and allow source events to enter the platform as they occur.

**Delayed enrichment:** SQS separates lead capture from enrichment and introduces a fixed waiting period before processing.

**Source preservation:** Bronze JSON provides a record of ingested source payloads, subject to the current object-naming behavior. Close and Calendly webhook object keys use source identifiers, so repeated events with the same identifier can overwrite existing objects.

**Data quality:** Silver transformations normalize source attributes, remove duplicates, and enforce selected uniqueness assumptions. Conflict detection is used where a reliable record-versioning rule is unavailable.

**Full-refresh processing:** Silver datasets are overwritten on each successful transformation run. Incremental processing and table formats supporting updates could be considered as data volume and operational requirements grow.

**Source-system assumptions:** The current implementation focuses on observed event types and available sample structures. Additional event lifecycle handling, retry behavior, and business-specific reconciliation rules would require validation with source-system owners.

**Attribution:** Cross-source booking attribution depends on reliable identifiers and tracking fields. The current implementation does not assume that every booking can be matched to an advertising channel.

## 8. Planned Extensions

The following capabilities are outside the currently completed implementation:

- Registering and querying Silver datasets through the AWS Glue Data Catalog and Amazon Athena.
- Building Gold-level aggregations for booking activity, acquisition cost, channel performance, and employee meeting load.
- Developing a Streamlit dashboard for business-facing metrics.
- Extending CI/CD to deploy Lambda packages automatically.
- Adding incremental processing, additional validation, and production-oriented monitoring where warranted.

These extensions build on the existing ingestion, enrichment, and Silver transformation foundation.