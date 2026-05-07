export type UserRole = 'caller' | 'admin';

const ROLE_KEY = 'afi_role';
const TOKEN_KEY = 'afi_token';

export const setRole = (role: UserRole) => {
  localStorage.setItem(ROLE_KEY, role);
};

export const setAuth = (role: UserRole, token: string) => {
  localStorage.setItem(ROLE_KEY, role);
  localStorage.setItem(TOKEN_KEY, token);
};

export const getRole = (): UserRole | null => {
  const role = localStorage.getItem(ROLE_KEY);
  if (role === 'caller' || role === 'admin') {
    return role;
  }
  return null;
};

export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const clearRole = () => {
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(TOKEN_KEY);
};
