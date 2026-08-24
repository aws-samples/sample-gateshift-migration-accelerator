/**
 * Lightweight Cognito authentication via the InitiateAuth API.
 *
 * Uses USER_PASSWORD_AUTH against a public app client (no secret), so no AWS
 * SDK is required in the browser. Handles the NEW_PASSWORD_REQUIRED challenge
 * that admin-created users hit on first sign-in.
 */
import { cognitoConfig, cognitoEndpoint } from './authConfig';

interface AuthResult {
    idToken: string;
    accessToken: string;
    refreshToken?: string;
    expiresAt: number; // epoch ms
}

interface NewPasswordChallenge {
    challenge: 'NEW_PASSWORD_REQUIRED';
    session: string;
    email: string;
}

export type LoginOutcome =
    | { kind: 'success'; result: AuthResult }
    | { kind: 'newPasswordRequired'; challenge: NewPasswordChallenge };

async function cognitoCall(target: string, body: unknown): Promise<any> {
    const res = await fetch(cognitoEndpoint(), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-amz-json-1.1',
            'X-Amz-Target': `AWSCognitoIdentityProviderService.${target}`,
        },
        body: JSON.stringify(body),
    });

    const data = await res.json();
    if (!res.ok) {
        // Cognito returns { __type, message }
        const message = data?.message || data?.__type || 'Authentication failed';
        throw new Error(message);
    }
    return data;
}

function toAuthResult(authenticationResult: any): AuthResult {
    const expiresInSec = authenticationResult.ExpiresIn ?? 3600;
    return {
        idToken: authenticationResult.IdToken,
        accessToken: authenticationResult.AccessToken,
        refreshToken: authenticationResult.RefreshToken,
        expiresAt: Date.now() + expiresInSec * 1000,
    };
}

export async function login(email: string, password: string): Promise<LoginOutcome> {
    const data = await cognitoCall('InitiateAuth', {
        AuthFlow: 'USER_PASSWORD_AUTH',
        ClientId: cognitoConfig.clientId,
        AuthParameters: { USERNAME: email, PASSWORD: password },
    });

    if (data.ChallengeName === 'NEW_PASSWORD_REQUIRED') {
        return {
            kind: 'newPasswordRequired',
            challenge: { challenge: 'NEW_PASSWORD_REQUIRED', session: data.Session, email },
        };
    }

    return { kind: 'success', result: toAuthResult(data.AuthenticationResult) };
}

export async function completeNewPassword(
    challenge: NewPasswordChallenge,
    newPassword: string
): Promise<AuthResult> {
    const data = await cognitoCall('RespondToAuthChallenge', {
        ChallengeName: 'NEW_PASSWORD_REQUIRED',
        ClientId: cognitoConfig.clientId,
        Session: challenge.session,
        ChallengeResponses: {
            USERNAME: challenge.email,
            NEW_PASSWORD: newPassword,
        },
    });

    return toAuthResult(data.AuthenticationResult);
}

export type { AuthResult, NewPasswordChallenge };
