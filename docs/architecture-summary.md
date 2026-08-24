# GateShift — Architecture Summary

This document accompanies `architecture.drawio` and describes the deployed
architecture of the GateShift Kong→API Gateway migration accelerator. It is
derived from repository evidence — primarily `backend/template.yaml` (AWS SAM),
`backend/statemachine/pipeline.asl.json`, the Lambda handlers under
`backend/src/`, and the frontend under `frontend/`.

> Open `architecture.drawio` at https://app.diagrams.net or in the draw.io VS Code
> extension. It uses the latest official AWS (aws4) icon set.

---

## Major AWS Services (confirmed from `template.yaml`)

| Category | Service | Role |
|---|---|---|
| Identity | Amazon Cognito User Pool + App Client | Authenticates users; issues ID tokens used as API bearer tokens |
| Edge / API | Amazon API Gateway (REST, stage `dev`) | Public entry point; Cognito authorizer on every route; throttling, access logging, X-Ray |
| Compute (API) | AWS Lambda ×7 | One handler per route (presign upload, create, list, get, report, artifact, presign download) |
| Orchestration | AWS Step Functions (Standard) | Runs the four-stage migration pipeline |
| Compute (pipeline) | AWS Lambda ×4 | Parser → Analyzer → Generator → Validator |
| AI | Amazon Bedrock (Claude Sonnet inference profile) | Feature-mapping / migration analysis, called by the Analyzer |
| Database | Amazon DynamoDB (`migrations` + `owner-index` GSI) | Migration state, ownership, results; SSE + PITR enabled |
| Storage | Amazon S3 (artifacts bucket) | `input/` uploads, `migrations/` intermediates, `output/` artifacts |
| Storage | Amazon S3 (access-logs bucket) | S3 server access logs for the artifacts bucket |
| Security | AWS IAM roles | Per-function least-privilege execution roles; API Gateway CloudWatch role |
| Monitoring | Amazon CloudWatch (Logs + Metrics) | API access logs, Lambda logs, Step Functions execution logs |
| Monitoring | AWS X-Ray | Tracing enabled on Lambdas, API Gateway, and the state machine |

The frontend (React + Vite + TypeScript) is **run locally** per the README and is
**not** deployed to AWS in this repository. It calls Cognito directly (InitiateAuth)
and the API Gateway endpoint.

---

> The numbered request flow is shown directly on the architecture diagram
> (`architecture.drawio`), so it is not duplicated here.

## Networking

There is **no VPC** in this architecture — it is fully serverless with
AWS-managed, regional endpoints. All components run in a single region
(`us-east-1` by default, `BedrockRegion` parameter). Transport is HTTPS/TLS
end-to-end; the artifacts bucket policy explicitly denies non-TLS access.
Accordingly, the diagram intentionally omits VPC/subnet/NAT/IGW constructs.

## Data Flow

- **Uploads**: browser → S3 `input/` (presigned PUT, direct, not through Lambda).
- **Pipeline artifacts**: pipeline Lambdas read/write `s3://…/migrations/**` and `output/**`.
- **State**: all handlers and pipeline stages read/write the DynamoDB `migrations` table; listing uses the `owner-index` GSI.
- **Results retrieval**: GetReport / GetArtifact return content **through the authenticated API** (no raw S3 URLs to the browser).

## Security Components

- **Authentication**: Cognito User Pool (admin-create only, MFA optional, strong password policy); public app client with no secret.
- **Authorization**: API Gateway Cognito authorizer on all routes; handlers additionally enforce per-user ownership via `owner_sub` from token claims, and scope S3 keys to `input/{userSub}/…`.
- **IAM**: least-privilege per-function policies (e.g., PresignUpload can only `s3:PutObject` under `input/*`; Analyzer’s `bedrock:InvokeModel` is scoped to foundation-model/inference-profile ARNs).
- **Data protection**: S3 SSE (AES256) + public access block + versioning + TLS-only bucket policy; DynamoDB SSE + point-in-time recovery.
- **Edge controls**: API Gateway throttling (rate 20 / burst 50) and CORS pinned to a single configured origin.

## Event-Driven / Async Workflows

- Step Functions Standard workflow is the async backbone (see pipeline above).
- **Not present**: no SQS, SNS, EventBridge, Kinesis, or S3 event notifications are defined in the repo. The pipeline is invoked synchronously via `StartExecution` from the CreateMigration Lambda, not via an event bus.

## Monitoring

- CloudWatch: API Gateway access log group, Step Functions execution log group, and default Lambda log groups; API Gateway metrics enabled.
- X-Ray: tracing enabled on all Lambdas (`Tracing: Active`), API Gateway (`TracingEnabled`), and the state machine.

---

## Confirmed vs Inferred

**Confirmed (present in `template.yaml` / code):**
Cognito User Pool + client, API Gateway REST API with Cognito authorizer, 7 API
Lambdas, 4 pipeline Lambdas, Step Functions Standard state machine, Bedrock
InvokeModel, DynamoDB table + GSI, two S3 buckets + policies, IAM roles,
CloudWatch log groups + metrics, X-Ray tracing.

**Inferred (reasonable interpretation, not explicit):**
- The **direct browser→S3 presigned PUT** for uploads is inferred from `presign_upload.py` returning a presigned `put_object` URL plus the frontend upload flow; the template does not model the browser as a resource.
- Cognito `InitiateAuth` from the browser is inferred from the frontend auth code (`frontend/src/api/auth.ts`), not from backend infra.
- The **frontend runs locally** (not hosted on AWS) — stated in the README; there is no CloudFront/S3 website/Amplify hosting resource in the repo.
- Icon color categories are cosmetic and chosen to match AWS conventions.

## Assumptions

1. Production == the single environment defined by this SAM template; there are no separate dev/staging/prod stacks in the repo (only a `dev` API stage name).
2. Bedrock runs in the same region as the stack (`BedrockRegion` default `us-east-1`).
3. "7 API Lambdas" reflects the current template including `GetArtifactFunction`.

## Unresolved Ambiguities / Missing Definitions

- **Frontend hosting is undefined in IaC.** If GateShift is later hosted on AWS (e.g., CloudFront + S3, or Amplify), that edge tier is not represented because no such resource exists in the repo today.
- **No WAF / Shield / ACM / custom domain** is defined; the API is served on the default execute-api domain. Add these if a public production posture is required.
- **`PresignDownloadFunction` is deployed but unused by the current UI** (the UI now uses `GetArtifact`). It remains in the template; the diagram shows it under API handlers for completeness but no active browser edge is drawn to it.
- **CloudTrail / AWS Config** are not defined in the repo and are therefore omitted.
