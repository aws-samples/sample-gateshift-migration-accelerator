import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

/**
 * Route guard. This is a usability control only — the API independently
 * validates the token on every request, so bypassing this in the browser
 * grants no access to data.
 */
export function RequireAuth() {
    const location = useLocation();
    const authed = useAuthStore((s) => s.isAuthenticated);

    if (!authed) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return <Outlet />;
}
