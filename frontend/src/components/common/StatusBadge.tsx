import type { MigrationStatus } from '../../types/migration';
import {
  Clock,
  Loader2,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react';

const STATUS_CONFIG: Record<
  MigrationStatus,
  { label: string; color: string; icon: typeof Clock }
> = {
  PENDING: { label: 'Pending', color: 'text-gray-600 bg-gray-100', icon: Clock },
  PARSING: { label: 'Parsing', color: 'text-blue-600 bg-blue-100', icon: Loader2 },
  ANALYZING: { label: 'Analyzing', color: 'text-purple-600 bg-purple-100', icon: Loader2 },
  GENERATING: { label: 'Generating', color: 'text-indigo-600 bg-indigo-100', icon: Loader2 },
  VALIDATING: { label: 'Validating', color: 'text-cyan-600 bg-cyan-100', icon: Loader2 },
  COMPLETE: { label: 'Complete', color: 'text-green-600 bg-green-100', icon: CheckCircle },
  FAILED: { label: 'Failed', color: 'text-red-600 bg-red-100', icon: XCircle },
  NEEDS_REVIEW: { label: 'Needs Review', color: 'text-amber-600 bg-amber-100', icon: AlertTriangle },
};

interface StatusBadgeProps {
  status: MigrationStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  const isSpinning = ['PARSING', 'ANALYZING', 'GENERATING', 'VALIDATING'].includes(status);

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${config.color}`}
    >
      <Icon className={`h-3.5 w-3.5 ${isSpinning ? 'animate-spin' : ''}`} />
      {config.label}
    </span>
  );
}
