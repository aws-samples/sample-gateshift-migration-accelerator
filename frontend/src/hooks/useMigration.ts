import { useQuery } from '@tanstack/react-query';
import { getMigration, getValidationReport } from '../api/migrations';
import type { MigrationStatus } from '../types/migration';

const IN_PROGRESS_STATUSES: MigrationStatus[] = [
  'PENDING',
  'PARSING',
  'ANALYZING',
  'GENERATING',
  'VALIDATING',
];

// Safety net: stop polling a migration that has been in progress too long.
// A crashed/timed-out Lambda that never records a terminal status would
// otherwise be polled forever.
export const STUCK_THRESHOLD_MS = 10 * 60 * 1000; // 10 minutes

export function isStuck(status: MigrationStatus, createdAt: string): boolean {
  if (!IN_PROGRESS_STATUSES.includes(status)) return false;
  const ageMs = Date.now() - new Date(createdAt).getTime();
  return ageMs > STUCK_THRESHOLD_MS;
}

export function useMigration(migrationId: string | undefined) {
  return useQuery({
    queryKey: ['migration', migrationId],
    queryFn: () => getMigration(migrationId!),
    enabled: !!migrationId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 3000;
      if (!IN_PROGRESS_STATUSES.includes(data.status)) {
        return false; // Terminal status: stop polling.
      }
      if (isStuck(data.status, data.created_at)) {
        return false; // Been in progress too long; treat as stalled.
      }
      return 3000; // Poll every 3s while in progress.
    },
  });
}

export function useValidationReport(migrationId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['report', migrationId],
    queryFn: () => getValidationReport(migrationId!),
    enabled: !!migrationId && enabled,
  });
}
