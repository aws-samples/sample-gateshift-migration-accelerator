/**
 * Cognito configuration read from Vite env vars.
 *
 * When the client id is unset or left at the "local-dev" sentinel (e.g. running
 * against the local mock-server), auth is treated as disabled so the UI stays
 * usable for frontend-only development. Fill in real values from the
 * `sam deploy` outputs to turn authentication on.
 */
const LOCAL_SENTINELS = new Set(['', 'local-dev']);

export const cognitoConfig = {
  clientId: import.meta.env.VITE_COGNITO_CLIENT_ID ?? '',
  userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID ?? '',
  region: import.meta.env.VITE_AWS_REGION ?? 'us-east-1',
};

export const authEnabled = !LOCAL_SENTINELS.has(cognitoConfig.clientId);

export function cognitoEndpoint(): string {
  return `https://cognito-idp.${cognitoConfig.region}.amazonaws.com/`;
}
