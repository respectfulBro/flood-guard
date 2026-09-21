const isNode = typeof window === 'undefined';

const isClearAccessTokenRequested = () =>
  !isNode && new URLSearchParams(window.location.search).get("clear_access_token") === 'true';

const clearStoredAccessToken = () => {
  window.localStorage.removeItem('auth_token');
}

const getAppParams = () => {
  if (isClearAccessTokenRequested()) {
    clearStoredAccessToken();
  }
  return {
    appId: import.meta.env.VITE_APP_ID || "floodguard-africa",
    token: localStorage.getItem('auth_token') || null,
    functionsVersion: import.meta.env.VITE_FUNCTIONS_VERSION || "1",
    appBaseUrl: import.meta.env.VITE_APP_BASE_URL || window.location.origin,
  }
}

export const appParams = {
  ...getAppParams()
}