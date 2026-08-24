import { Link } from 'react-router-dom';
import { ArrowRightLeft, LogOut } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { authEnabled } from '../../api/authConfig';

export function Header() {
  const email = useAuthStore((s) => s.email);
  const logout = useAuthStore((s) => s.logout);

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <ArrowRightLeft className="h-7 w-7 text-blue-600" />
            <span className="text-xl font-bold text-gray-900">GateShift</span>
          </Link>
          <nav className="flex items-center gap-4">
            <Link
              to="/"
              className="text-sm font-medium text-gray-600 hover:text-gray-900"
            >
              Dashboard
            </Link>
            <Link
              to="/migrate"
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              + New Migration
            </Link>
            {authEnabled && (
              <div className="flex items-center gap-3 border-l border-gray-200 pl-4">
                {email && (
                  <span className="hidden text-sm text-gray-500 sm:inline">{email}</span>
                )}
                <button
                  onClick={logout}
                  aria-label="Sign out"
                  title="Sign out"
                  className="flex items-center gap-1 rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            )}
          </nav>
        </div>
      </div>
    </header>
  );
}
