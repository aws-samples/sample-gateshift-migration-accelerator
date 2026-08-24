import { useQuery } from '@tanstack/react-query';
import { getMigrations } from '../api/migrations';

export function useMigrations() {
  return useQuery({
    queryKey: ['migrations'],
    queryFn: getMigrations,
    refetchInterval: 10000,
  });
}
