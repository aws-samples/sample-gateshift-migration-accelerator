import { Link } from 'react-router-dom';
import { Plus, ArrowRightLeft } from 'lucide-react';
import { useMigrations } from '../hooks/useMigrations';
import { MigrationCard } from '../components/dashboard/MigrationCard';

export function DashboardPage() {
  const { data: migrations, isLoading, error } = useMigrations();

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Your Migrations</h1>
        <Link
          to="/migrate"
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          New Migration
        </Link>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load migrations. Make sure the backend is running.
        </div>
      )}

      {migrations && migrations.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 py-16">
          <ArrowRightLeft className="mb-4 h-12 w-12 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900">No migrations yet</h3>
          <p className="mt-1 text-sm text-gray-500">
            Upload a Kong config to get started
          </p>
          <Link
            to="/migrate"
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Start Your First Migration
          </Link>
        </div>
      )}

      {migrations && migrations.length > 0 && (
        <div className="space-y-3">
          {migrations.map((migration) => (
            <MigrationCard key={migration.migration_id} migration={migration} />
          ))}
        </div>
      )}
    </div>
  );
}
