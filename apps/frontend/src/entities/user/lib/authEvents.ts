export const AUTH_CHANGED_EVENT = 'papaya-auth-changed';
export const DEV_AUTO_LOGIN_DISABLED_KEY = 'papaya-dev-auto-login-disabled';

export function isDevAutoLoginDisabled(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }

  return window.sessionStorage.getItem(DEV_AUTO_LOGIN_DISABLED_KEY) === 'true';
}

export function disableDevAutoLogin(): void {
  window.sessionStorage.setItem(DEV_AUTO_LOGIN_DISABLED_KEY, 'true');
}

export function enableDevAutoLogin(): void {
  window.sessionStorage.removeItem(DEV_AUTO_LOGIN_DISABLED_KEY);
}

export function emitAuthChanged(): void {
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}
