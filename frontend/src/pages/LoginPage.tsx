import { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { ArrowRightLeft, Loader2 } from 'lucide-react';
import { login, completeNewPassword } from '../api/auth';
import type { NewPasswordChallenge } from '../api/auth';
import { useAuthStore } from '../store/authStore';

export function LoginPage() {
    const setSession = useAuthStore((s) => s.setSession);
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
    const location = useLocation();
    const from =
        (location.state as { from?: { pathname?: string } })?.from?.pathname || '/';

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [challenge, setChallenge] = useState<NewPasswordChallenge | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            if (challenge) {
                const result = await completeNewPassword(challenge, newPassword);
                setSession(result, challenge.email);
                return;
            }

            const outcome = await login(email, password);
            if (outcome.kind === 'newPasswordRequired') {
                setChallenge(outcome.challenge);
            } else {
                setSession(outcome.result, email);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Sign in failed');
        } finally {
            setLoading(false);
        }
    };

    // Already signed in (including local "auth disabled" mode): go straight in.
    if (isAuthenticated) {
        return <Navigate to={from} replace />;
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
            <div className="w-full max-w-sm">
                <div className="mb-8 flex flex-col items-center">
                    <ArrowRightLeft className="h-10 w-10 text-blue-600" />
                    <h1 className="mt-2 text-2xl font-bold text-gray-900">GateShift</h1>
                    <p className="text-sm text-gray-500">Sign in to continue</p>
                </div>

                <form
                    onSubmit={handleSubmit}
                    className="space-y-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
                >
                    {!challenge ? (
                        <>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Email</label>
                                <input
                                    type="email"
                                    required
                                    autoComplete="username"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Password</label>
                                <input
                                    type="password"
                                    required
                                    autoComplete="current-password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                />
                            </div>
                        </>
                    ) : (
                        <>
                            <p className="rounded-lg bg-blue-50 p-3 text-sm text-blue-700">
                                First sign-in: choose a new password (min 12 chars, with upper,
                                lower, number, and symbol).
                            </p>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">New Password</label>
                                <input
                                    type="password"
                                    required
                                    autoComplete="new-password"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                />
                            </div>
                        </>
                    )}

                    {error && (
                        <div className="rounded-lg border border-red-200 bg-red-50 p-2 text-sm text-red-700">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                        {challenge ? 'Set Password & Sign In' : 'Sign In'}
                    </button>
                </form>
            </div>
        </div>
    );
}
