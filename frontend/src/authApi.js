import { API_URL } from './mapHelpers';
const TOKEN_KEY = 'hereji_access_token';
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const saveToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);
export async function authFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(url, { ...options, headers });
  if (response.status === 401) { clearToken(); window.dispatchEvent(new Event('hereji:session-expired')); }
  return response;
}
async function request(path, options = {}) {
  const response = await authFetch(`${API_URL}${path}`, options);
  let data = null; try { data = await response.json(); } catch { data = null; }
  if (!response.ok) throw new Error(data?.detail?.message || data?.detail || '요청을 처리하지 못했습니다.');
  return data;
}
const json = (method, payload) => ({ method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
export const signup = payload => request('/auth/signup', json('POST', payload));
export const login = payload => request('/auth/login', json('POST', payload));
export const getMe = () => request('/auth/me');
export const verifyGender = test_code => request('/auth/verify-gender', json('POST', {test_code}));
export async function logout() { try { await request('/auth/logout', {method:'POST'}); } finally { clearToken(); } }
