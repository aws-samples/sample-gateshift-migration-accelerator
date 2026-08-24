import { create } from 'zustand';
import type { AuthResult } from '../api/auth';
import { authEnabled } from '../api/authConfig';

const STORAGE_KEY = 'gateshift.auth';

interface StoredAuth {
    idToken: string;
    expiresAt: number;
    email: string;
}

function loadStored(): StoredAuth | null {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw) as StoredAuth;
        if (parsed.expiresAt <= Date.now()) {
            localStorage.removeItem(STORAGE_KEY);
            return null;
        }
        return parsed;
    } catch {
        return null;
    }
}

interface AuthState {
    idToken: string | null;
    email: string | null;
    isAuthenticated: boolean;
    setSession: (result: AuthResult, email: string) => void;
    logout: () => void;
}

const stored = loadStored();

export const useAuthStore = create<AuthState>((set) => ({
    idToken: stored?.idToken ?? null,
    email: stored?.email ?? null,
    // When auth is disabled (mock/local mode) the app behaves as always signed in.
    isAuthenticated: !authEnabled || Boolean(stored),

    setSession: (result, email) => {
        const record: StoredAuth = {
            idToken: result.idToken,
            expiresAt: result.expiresAt,
            email,
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
        set({ idToken: result.idToken, email, isAuthenticated: true });
    },

    logout: () => {
        localStorage.removeItem(STORAGE_KEY);
        set({
            idToken: null,
            email: null,
            isAuthenticated: !authEnabled ? true : false,
        });
    },
}));

/** Read the current token outside React (for the axios interceptor). */
export function getIdToken(): string | null {
    return loadStored()?.idToken ?? null;
}

/** Clear the session outside React (for the axios 401 interceptor). */
export function clearSession(): void {
    useAuthStore.getState().logout();
}
