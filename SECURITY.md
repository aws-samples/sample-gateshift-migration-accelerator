# Security

## Disclaimer

This project is sample/educational code and is not intended for production use without additional security hardening and review. See the production hardening recommendations throughout this document (notably the **Accepted Risks and Justifications** section).

---

## Reporting Vulnerabilities

If you discover a potential security issue in this project, please notify AWS/Amazon Security via the
[vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Do **not** create a
public GitHub issue.

---

## Authentication and Authorization

- Every API endpoint (except the CORS preflight `OPTIONS`) requires a valid **Amazon Cognito ID token** in the `Authorization` header.
- API Gateway uses a **Cognito User Pool authorizer** to validate the token before any Lambda is invoked. Invalid or missing tokens return `401`.
- **Self-service sign-up is disabled** (`AllowAdminCreateUserOnly: true`) — accounts are created by an administrator. This prevents anyone who discovers the public app client ID from registering and consuming Bedrock capacity.
- **Password policy:** minimum 12 characters with uppercase, lowercase, number, and symbol. **MFA** is optional (software token). Advanced security mode is set to `AUDIT`.
- **Per-resource ownership:** handlers derive the caller identity from the Cognito `sub` claim and only return or act on the caller's own migrations. Reading another user's resource returns `404` (not `403`) so existence cannot be probed.
- **Scoped uploads:** presigned upload keys are namespaced under `input/{sub}/…`, and Create Migration validates that the supplied `configS3Key` belongs to the caller's own prefix.

## Network Security

- The stack is fully serverless with **no VPC**; Lambdas reach only AWS-managed services over IAM-authenticated HTTPS.
- The public app client has **no client secret** (`GenerateSecret: false`), so nothing sensitive is embedded in the browser.
- **CORS origin is explicit** — the `AllowedOrigin` parameter is required and pinned on both API Gateway and the S3 bucket CORS rule (no wildcard).
- API Gateway enforces **request throttling** (rate 20 req/s, burst 50) at the stage level.
- Auth-failure responses (`401`/`403`) still carry CORS headers so the browser surfaces a useful error instead of an opaque network failure.

## Encryption

| Resource | Encryption | Notes |
|----------|-----------|-------|
| S3 Artifacts bucket | At rest (SSE-S3 / AES256) | Bucket key enabled; TLS-only bucket policy denies non-HTTPS access |
| S3 Access Logs bucket | At rest (SSE-S3 / AES256) | TLS-only bucket policy |
| DynamoDB `migrations` table | At rest (SSE) | Point-in-time recovery enabled |
| CloudWatch Logs (API access, Step Functions) | At rest (AWS-managed) | — |
| All data in transit | HTTPS / TLS | Enforced end-to-end; S3 bucket policy denies `aws:SecureTransport=false` |

## IAM and Least Privilege

Each function has its own dedicated role with only the permissions it needs:

- **Presign Upload:** `s3:PutObject` on `input/*` only.
- **Create Migration:** DynamoDB CRUD on the table + `states:StartExecution` on the migration state machine.
- **List / Get Migration:** DynamoDB read only.
- **Get Report / Get Artifact / Presign Download:** DynamoDB read + `s3:GetObject` on `migrations/*`.
- **Parser:** DynamoDB CRUD + `s3:GetObject` on `input/*` + `s3:PutObject` on `migrations/*`.
- **Analyzer:** DynamoDB CRUD + S3 get/put on `migrations/*` + `bedrock:InvokeModel` scoped to foundation-model and inference-profile ARNs (not wildcard).
- **Generator / Validator:** DynamoDB CRUD + S3 get/put on `migrations/*`.
- **Step Functions:** `lambda:InvokeFunction` limited to the four pipeline functions + CloudWatch Logs for execution logging.

## Data Lifecycle

- **S3 Artifacts:** versioning enabled; noncurrent versions expire after 30 days; incomplete multipart uploads aborted after 7 days.
- **S3 Access Logs:** expire after 90 days.
- **DynamoDB:** point-in-time recovery enabled; records are retained (no TTL) so migration history persists.
- **Retention on delete:** the artifacts bucket, access-logs bucket, and DynamoDB table use `DeletionPolicy: Retain` — a stack delete never silently destroys migration data.

## Failure Handling

- Every pipeline stage wraps its work so that an exception marks the migration `FAILED` in DynamoDB (via a shared `mark_failed` helper) instead of leaving a record stuck "in progress."
- The Step Functions definition catches stage errors and routes to a terminal `MigrationFailed` state; the Analyze stage retries on transient throttling with exponential backoff.

## Secret Management

- No API keys, passwords, or secrets are stored in code or configuration.
- Backend access is IAM/SigV4-based; frontend access is Cognito token-based.
- Frontend configuration (API URL, Cognito IDs) is loaded from environment variables (`.env`, gitignored). Cognito **User Pool and Client IDs are public identifiers**, safe for client-side use.

## Monitoring and Observability

- **API Gateway access logs** are written to CloudWatch (structured JSON including request ID, caller `sub`, method, path, status, latency).
- **Step Functions** execution logs stream to a dedicated CloudWatch log group.
- **AWS X-Ray** tracing is enabled on API Gateway, all Lambda functions, and the state machine.
- API Gateway stage metrics are enabled.

## Accepted Risks and Justifications

| Item | Decision | Rationale |
|------|----------|-----------|
| No VPC for Lambda | Accepted | Functions call only AWS-managed services via IAM-authenticated HTTPS. A VPC would add latency and NAT cost with no security benefit. |
| No AWS WAF | Accepted (dev) | Cognito authorizer plus stage throttling provide adequate protection for this workload. WAF is recommended before a public production deployment. |
| No API keys on methods | Accepted | Authentication uses the Cognito JWT authorizer, which is stronger than API keys. Throttling is handled by stage settings. |
| No custom domain / mutual TLS | Accepted | Served on the default `execute-api` domain; TLS is enforced by default. Browser clients cannot present client certificates. |
| S3 Access Logs bucket has no logging of its own | Not applicable | It is the logging destination; logging to itself would create recursion. Standard AWS pattern. |
| `PresignDownloadFunction` deployed but unused by the UI | Accepted | Superseded by the authenticated `GetArtifact` route; retained for compatibility and large-artifact use. |

---

## Security Checklist

- [x] Cognito authentication on all API endpoints
- [x] Cognito authorizer validates tokens before any Lambda runs
- [x] Admin-only user creation (no open sign-up)
- [x] Per-caller ownership enforcement on every read/action
- [x] Least-privilege IAM role per function
- [x] `bedrock:InvokeModel` scoped to specific model/inference-profile ARNs
- [x] Data encrypted at rest (S3 SSE, DynamoDB SSE) and in transit (TLS)
- [x] TLS-only S3 bucket policies
- [x] CORS restricted to an explicit origin (no wildcard)
- [x] API request throttling at the stage
- [x] No hardcoded secrets; frontend config via gitignored `.env`
- [x] Access logging (API Gateway, Step Functions) and X-Ray tracing enabled
- [x] Graceful failure marking so migrations never hang
- [x] Retain policies protect S3 and DynamoDB data on stack deletion
