import type { GapItem } from '../../types/migration';
import { AlertTriangle } from 'lucide-react';

interface GapReportProps {
  gaps: GapItem[];
  warnings: string[];
}

export function GapReport({ gaps, warnings }: GapReportProps) {
  if (!gaps.length && !warnings.length) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-center">
        <p className="text-sm text-green-700">No gaps detected. All features are mappable.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {gaps.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-900">Feature Gaps</h4>
          {gaps.map((gap, idx) => (
            <div
              key={idx}
              className="rounded-lg border border-red-200 bg-red-50 p-3"
            >
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 text-red-500 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-red-800">
                    {gap.source_plugin_name || gap.source_feature}
                  </p>
                  <p className="mt-1 text-sm text-red-700">{gap.recommendation}</p>
                  <p className="mt-1 text-xs text-red-500">
                    Est. effort: {gap.effort_estimate_hours}h
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-900">Warnings</h4>
          {warnings.map((warning, idx) => (
            <div
              key={idx}
              className="rounded-lg border border-amber-200 bg-amber-50 p-3"
            >
              <p className="text-sm text-amber-800">⚠️ {warning}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
