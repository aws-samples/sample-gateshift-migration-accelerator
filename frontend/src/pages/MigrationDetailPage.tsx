import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Server } from 'lucide-react';
import { useMigration, useValidationReport, isStuck } from '../hooks/useMigration';
import { StatusBadge } from '../components/common/StatusBadge';
import { ConfidenceGauge } from '../components/analysis/ConfidenceGauge';
import { FeatureMap } from '../components/analysis/FeatureMap';
import { GapReport } from '../components/analysis/GapReport';
import { TemplateLint } from '../components/analysis/TemplateLint';
import { DownloadPanel } from '../components/output/DownloadPanel';
import type { MigrationStatus } from '../types/migration';

const PIPELINE_STEPS: { status: MigrationStatus; label: string }[] = [
  { status: 'PARSING', label: 'Parse' },
  { status: 'ANALYZING', label: 'Analyze' },
  { status: 'GENERATING', label: 'Generate' },
  { status: 'VALIDATING', label: 'Validate' },
];

const STATUS_ORDER: MigrationStatus[] = [
  'PENDING',
  'PARSING',
  'ANALYZING',
  'GENERATING',
  'VALIDATING',
  'COMPLETE',
  'NEEDS_REVIEW',
];

export function MigrationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: migration, isLoading } = useMigration(id);
  const isFinished = migration?.status === 'COMPLETE' || migration?.status === 'NEEDS_REVIEW';
  const { data: report } = useValidationReport(id, isFinished);

  if (isLoading || !migration) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  const currentStepIdx = STATUS_ORDER.indexOf(migration.status);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/" className="text-gray-400 hover:text-gray-600">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-gray-900">{migration.file_name}</h1>
            <p className="text-sm text-gray-500 capitalize">{migration.source_type} migration</p>
          </div>
        </div>
        <StatusBadge status={migration.status} />
      </div>

      {/* Pipeline Progress */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex items-center justify-between">
          {PIPELINE_STEPS.map((step, idx) => {
            const stepIdx = STATUS_ORDER.indexOf(step.status);
            const isDone = currentStepIdx > stepIdx;
            const isActive = currentStepIdx === stepIdx;
            const isFailed = migration.status === 'FAILED';

            return (
              <div key={step.status} className="flex items-center flex-1">
                <div className="flex flex-col items-center">
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium ${isDone
                      ? 'bg-green-100 text-green-700'
                      : isActive
                        ? 'bg-blue-100 text-blue-700 ring-2 ring-blue-400'
                        : isFailed
                          ? 'bg-red-100 text-red-700'
                          : 'bg-gray-100 text-gray-400'
                      }`}
                  >
                    {isDone ? '✓' : idx + 1}
                  </div>
                  <span className="mt-1 text-xs text-gray-500">{step.label}</span>
                </div>
                {idx < PIPELINE_STEPS.length - 1 && (
                  <div
                    className={`mx-2 h-0.5 flex-1 ${isDone ? 'bg-green-300' : 'bg-gray-200'
                      }`}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Error State */}
      {migration.status === 'FAILED' && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">Migration Failed</p>
          <p className="mt-1 text-sm text-red-700">
            {migration.error_message || 'An unexpected error occurred during the pipeline.'}
          </p>
        </div>
      )}

      {/* Stalled State — in progress far longer than expected */}
      {migration.status !== 'FAILED' &&
        isStuck(migration.status, migration.created_at) && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm font-medium text-amber-800">
              Migration is taking longer than expected
            </p>
            <p className="mt-1 text-sm text-amber-700">
              This run has been in progress for over 10 minutes and may have
              stalled. Check the Step Functions execution logs in the AWS console
              for details.
            </p>
          </div>
        )}

      {/* Results */}
      {isFinished && report && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="flex flex-col items-center rounded-lg border border-gray-200 bg-white p-4">
              <ConfidenceGauge score={report.confidence_score} />
            </div>
            <div className="flex flex-col items-center justify-center rounded-lg border border-gray-200 bg-white p-4">
              <Server className="mb-2 h-8 w-8 text-blue-600" />
              <p className="text-lg font-bold text-gray-900">{report.target_api_type} API</p>
              <p className="text-xs text-gray-500">Recommended</p>
              <p className="mt-2 text-center text-xs text-gray-500 line-clamp-2">
                {report.target_api_type_reasoning}
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <h4 className="mb-2 text-sm font-medium text-gray-500">Summary</h4>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Direct Mappings</span>
                  <span className="font-medium text-green-600">{report.summary.direct_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Lambda Required</span>
                  <span className="font-medium text-yellow-600">{report.summary.lambda_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Alternative</span>
                  <span className="font-medium text-orange-600">{report.summary.alternative_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Gaps</span>
                  <span className="font-medium text-red-600">{report.summary.gap_count}</span>
                </div>
                <hr className="my-1" />
                <div className="flex justify-between">
                  <span className="text-gray-600">Est. Effort</span>
                  <span className="font-medium">{report.summary.estimated_effort_hours}h</span>
                </div>
              </div>
            </div>
          </div>

          {/* Feature Mapping Table */}
          <div>
            <h3 className="mb-3 text-lg font-medium text-gray-900">Feature Mapping</h3>
            <FeatureMap mappings={report.feature_mappings} />
          </div>

          {/* Gap Report */}
          <div>
            <h3 className="mb-3 text-lg font-medium text-gray-900">Gaps & Warnings</h3>
            <GapReport gaps={report.gaps} warnings={report.warnings} />
          </div>

          {/* Template Lint (cfn-lint) */}
          {report.template_lint && (
            <div>
              <h3 className="mb-3 text-lg font-medium text-gray-900">Template Validation</h3>
              <TemplateLint result={report.template_lint} />
            </div>
          )}

          {/* Downloads */}
          <DownloadPanel migrationId={migration.migration_id} />
        </>
      )}
    </div>
  );
}
