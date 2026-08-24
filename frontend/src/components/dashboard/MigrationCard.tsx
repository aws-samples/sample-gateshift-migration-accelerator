import { Link } from 'react-router-dom';
import { FileText } from 'lucide-react';
import type { Migration } from '../../types/migration';
import { StatusBadge } from '../common/StatusBadge';
import { formatDate, formatConfidence } from '../../utils/formatters';

interface MigrationCardProps {
  migration: Migration;
}

export function MigrationCard({ migration }: MigrationCardProps) {
  return (
    <Link
      to={`/migrations/${migration.migration_id}`}
      className="block rounded-lg border border-gray-200 bg-white p-4 transition hover:border-blue-300 hover:shadow-sm"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-gray-400" />
          <div>
            <p className="font-medium text-gray-900">{migration.file_name}</p>
            <p className="text-xs text-gray-500 capitalize">
              {migration.source_type} • {formatDate(migration.created_at)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {migration.confidence_score !== undefined && (
            <span className="text-sm font-medium text-gray-700">
              {formatConfidence(migration.confidence_score)}
            </span>
          )}
          <StatusBadge status={migration.status} />
        </div>
      </div>
    </Link>
  );
}
