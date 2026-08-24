/**
 * GateShift Mock API Server
 * Run with: node mock-server.js
 * Simulates the backend API so you can develop the frontend locally.
 */

const http = require("http");
const { randomUUID } = require("crypto");

const PORT = 3001;

// In-memory store
const migrations = new Map();

// CORS headers
const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Content-Type": "application/json",
};

// Simulate pipeline progression
function progressMigration(migrationId) {
    const statuses = [
        "PARSING",
        "ANALYZING",
        "GENERATING",
        "VALIDATING",
        "COMPLETE",
    ];
    let idx = 0;

    const interval = setInterval(() => {
        const migration = migrations.get(migrationId);
        if (!migration) {
            clearInterval(interval);
            return;
        }

        migration.status = statuses[idx];
        migration.updated_at = new Date().toISOString();

        if (statuses[idx] === "COMPLETE") {
            migration.confidence_score = 87.5;
            migration.target_api_type = "REST";
            migration.summary = {
                direct_count: 5,
                lambda_count: 2,
                alternative_count: 1,
                gap_count: 1,
                estimated_effort_hours: 12,
            };
            clearInterval(interval);
        }

        idx++;
    }, 2000); // Each step takes 2 seconds
}

// Mock validation report
function getMockReport(migrationId) {
    return {
        migration_id: migrationId,
        confidence_score: 87.5,
        target_api_type: "REST",
        target_api_type_reasoning:
            "REST API is recommended because the source config uses rate-limiting, request-validator, and IP restriction — features only available on REST API.",
        route_coverage: { total: 4, covered: 4, percentage: 100, details: [] },
        auth_coverage: { total: 2, covered: 2, percentage: 100, details: [] },
        plugin_coverage: {
            total: 8,
            covered: 7,
            percentage: 87.5,
            details: ["custom-lua-plugin"],
        },
        feature_mappings: [
            {
                source_feature: "Authentication",
                source_plugin_name: "key-auth",
                aws_equivalent: "API Gateway API Keys + Usage Plans",
                mapping_type: "direct",
                implementation_notes:
                    "API Keys for metering. Combine with authorizer for security.",
            },
            {
                source_feature: "Authentication",
                source_plugin_name: "jwt",
                aws_equivalent: "Lambda Authorizer (TOKEN type)",
                mapping_type: "lambda",
                implementation_notes:
                    "Validate JWT claims in Lambda, return IAM policy. Cache for 300s.",
            },
            {
                source_feature: "Rate Limiting",
                source_plugin_name: "rate-limiting",
                aws_equivalent: "Usage Plan Throttling",
                mapping_type: "direct",
                implementation_notes:
                    "Maps to API Gateway rate + burst limits.",
            },
            {
                source_feature: "CORS",
                source_plugin_name: "cors",
                aws_equivalent: "API Gateway CORS Configuration",
                mapping_type: "direct",
                implementation_notes:
                    "Native CORS support on both REST and HTTP APIs.",
            },
            {
                source_feature: "Request Validation",
                source_plugin_name: "request-validator",
                aws_equivalent: "API Gateway Request Validators",
                mapping_type: "direct",
                implementation_notes:
                    "Validates body (JSON Schema), query params, headers.",
            },
            {
                source_feature: "IP Filtering",
                source_plugin_name: "ip-restriction",
                aws_equivalent: "Resource Policy or AWS WAF IP Sets",
                mapping_type: "direct",
                implementation_notes:
                    "Simple allow/deny via Resource Policy. Complex rules via WAF.",
            },
            {
                source_feature: "Transformation",
                source_plugin_name: "request-transformer",
                aws_equivalent: "VTL Mapping Templates or Lambda",
                mapping_type: "lambda",
                implementation_notes:
                    "Simple headers via VTL. Complex body transforms via Lambda.",
            },
            {
                source_feature: "Logging",
                source_plugin_name: "http-log",
                aws_equivalent: "CloudWatch Logs + Kinesis Firehose",
                mapping_type: "alternative",
                implementation_notes:
                    "Forward logs via Firehose to HTTP endpoint.",
            },
            {
                source_feature: "Custom Logic",
                source_plugin_name: "custom-lua-plugin",
                aws_equivalent: "—",
                mapping_type: "gap",
                implementation_notes:
                    "No equivalent. Rewrite Lua logic as Lambda function.",
            },
        ],
        gaps: [
            {
                source_feature: "Custom Logic",
                source_plugin_name: "custom-lua-plugin",
                category: "transformation",
                severity: "medium",
                recommendation:
                    "Rewrite the Lua plugin logic as a Python/Node.js Lambda function.",
                effort_estimate_hours: 4,
            },
        ],
        warnings: [
            'Kong rate-limiting uses "local" policy (per-node). API Gateway throttling is global. Effective rate may differ under load.',
            "Kong consumers with ACL groups will need equivalent IAM policy logic in the Lambda authorizer.",
        ],
        summary: {
            direct_count: 5,
            lambda_count: 2,
            alternative_count: 1,
            gap_count: 1,
            estimated_effort_hours: 12,
        },
    };
}

/**
 * Mirror the deployed API: every route except the CORS preflight requires an
 * Authorization header. This keeps local development honest so missing-token
 * bugs surface here instead of after deploying.
 */
function getCaller(req) {
    const header = req.headers["authorization"];
    if (!header) return null;
    const token = header.replace(/^Bearer\s+/i, "");
    try {
        const payload = JSON.parse(
            Buffer.from(token.split(".")[1], "base64").toString("utf8")
        );
        return payload.sub ? { sub: payload.sub, email: payload.email } : null;
    } catch {
        return null;
    }
}

// Route handler
function handleRequest(req, res) {
    const url = new URL(req.url, `http://localhost:${PORT}`);
    const path = url.pathname;
    const method = req.method;

    // CORS preflight
    if (method === "OPTIONS") {
        res.writeHead(204, corsHeaders);
        res.end();
        return;
    }

    // The mock S3 target stands in for a presigned URL, which carries its own
    // signature rather than an Authorization header.
    const isMockS3Upload = path === "/mock-s3-upload";

    if (!getCaller(req) && !isMockS3Upload) {
        res.writeHead(401, corsHeaders);
        res.end(JSON.stringify({ error: "Missing caller identity" }));
        return;
    }

    // POST /uploads/presign
    if (method === "POST" && path === "/uploads/presign") {
        let body = "";
        req.on("data", (chunk) => (body += chunk));
        req.on("end", () => {
            const { fileName } = JSON.parse(body || "{}");
            const uploadId = randomUUID().slice(0, 8);
            const s3Key = `input/${uploadId}/${fileName || "config.yaml"}`;
            res.writeHead(200, corsHeaders);
            res.end(
                JSON.stringify({
                    uploadUrl: `http://localhost:${PORT}/mock-s3-upload`,
                    s3Key,
                }),
            );
        });
        return;
    }

    // PUT /mock-s3-upload (simulates S3 presigned upload)
    if (method === "PUT" && path === "/mock-s3-upload") {
        let body = "";
        req.on("data", (chunk) => (body += chunk));
        req.on("end", () => {
            res.writeHead(200, corsHeaders);
            res.end();
        });
        return;
    }

    // POST /migrations
    if (method === "POST" && path === "/migrations") {
        let body = "";
        req.on("data", (chunk) => (body += chunk));
        req.on("end", () => {
            const { sourceType, configS3Key, fileName } = JSON.parse(
                body || "{}",
            );
            const migrationId = randomUUID();
            const now = new Date().toISOString();

            const migration = {
                migration_id: migrationId,
                source_type: sourceType || "kong",
                config_s3_key: configS3Key,
                file_name: fileName || "config.yaml",
                status: "PENDING",
                created_at: now,
                updated_at: now,
            };

            migrations.set(migrationId, migration);
            progressMigration(migrationId);

            res.writeHead(201, corsHeaders);
            res.end(JSON.stringify({ migrationId }));
        });
        return;
    }

    // GET /migrations
    if (method === "GET" && path === "/migrations") {
        const list = Array.from(migrations.values()).sort(
            (a, b) =>
                new Date(b.created_at).getTime() -
                new Date(a.created_at).getTime(),
        );
        res.writeHead(200, corsHeaders);
        res.end(JSON.stringify({ migrations: list }));
        return;
    }

    // GET /migrations/:id
    const migrationMatch = path.match(/^\/migrations\/([^/]+)$/);
    if (method === "GET" && migrationMatch) {
        const id = migrationMatch[1];
        const migration = migrations.get(id);
        if (!migration) {
            res.writeHead(404, corsHeaders);
            res.end(JSON.stringify({ error: "Not found" }));
            return;
        }
        res.writeHead(200, corsHeaders);
        res.end(JSON.stringify(migration));
        return;
    }

    // GET /migrations/:id/report
    const reportMatch = path.match(/^\/migrations\/([^/]+)\/report$/);
    if (method === "GET" && reportMatch) {
        const id = reportMatch[1];
        const migration = migrations.get(id);
        if (!migration) {
            res.writeHead(404, corsHeaders);
            res.end(JSON.stringify({ error: "Not found" }));
            return;
        }
        if (
            migration.status !== "COMPLETE" &&
            migration.status !== "NEEDS_REVIEW"
        ) {
            res.writeHead(409, corsHeaders);
            res.end(JSON.stringify({ error: "Migration still in progress" }));
            return;
        }
        res.writeHead(200, corsHeaders);
        res.end(JSON.stringify(getMockReport(id)));
        return;
    }

    // GET /migrations/:id/download/:artifact
    const downloadMatch = path.match(
        /^\/migrations\/([^/]+)\/download\/([^/]+)$/,
    );
    if (method === "GET" && downloadMatch) {
        res.writeHead(200, corsHeaders);
        res.end(
            JSON.stringify({
                url: "https://example.com/mock-download",
                artifact: downloadMatch[2],
            }),
        );
        return;
    }

    // 404
    res.writeHead(404, corsHeaders);
    res.end(JSON.stringify({ error: "Not found" }));
}

const server = http.createServer(handleRequest);
server.listen(PORT, () => {
    console.log(
        `\n  🔄 GateShift Mock API Server running at http://localhost:${PORT}\n`,
    );
    console.log("  Endpoints:");
    console.log("    POST /uploads/presign");
    console.log("    POST /migrations");
    console.log("    GET  /migrations");
    console.log("    GET  /migrations/:id");
    console.log("    GET  /migrations/:id/report");
    console.log("    GET  /migrations/:id/download/:artifact");
    console.log("");
});
