import type { FeatureMapping, MappingType } from '../../types/migration';
import { CheckCircle, AlertTriangle, XCircle, Zap } from 'lucide-react';

interface FeatureMapProps {
  mappings: FeatureMapping[];
}

const MAPPING_CONFIG: Record<
  MappingType,
  { icon: typeof CheckCircle; color: string; label: string }
> = {
  direct: { icon: CheckCircle, color: 'text-green-600 bg-green-50', label: 'Direct' },
  lambda: { icon: Zap, color: 'text-yellow-600 bg-yellow-50', label: 'Lambda' },
  alternative: { icon: AlertTriangle, color: 'text-orange-600 bg-orange-50', label: 'Alternative' },
  gap: { icon: XCircle, color: 'text-red-600 bg-red-50', label: 'Gap' },
};

export function FeatureMap({ mappings }: FeatureMapProps) {
  if (!mappings.length) {
    return <p className="text-sm text-gray-500">No feature mappings available.</p>;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
              Kong Plugin
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
              AWS Equivalent
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
              Mapping
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
              Notes
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {mappings.map((mapping, idx) => {
            const config = MAPPING_CONFIG[mapping.mapping_type];
            const Icon = config.icon;
            return (
              <tr key={idx}>
                <td className="px-4 py-3 font-mono text-sm">
                  {mapping.source_plugin_name}
                </td>
                <td className="px-4 py-3 text-sm">{mapping.aws_equivalent}</td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ${config.color}`}
                  >
                    <Icon className="h-3 w-3" />
                    {config.label}
                  </span>
                </td>
                <td className="max-w-xs px-4 py-3 text-sm text-gray-600 truncate">
                  {mapping.implementation_notes}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
