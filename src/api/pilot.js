import { useQuery } from '@tanstack/react-query';

export async function request(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    credentials: 'same-origin', ...options,
    headers: { 'Content-Type': 'application/json', 'X-Pilot-Request': '1', ...options.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = Array.isArray(payload.detail) ? payload.detail.map((e) => e.msg).join('; ') : payload.detail;
    throw new Error(response.status === 401 ? 'Sign in to the private pilot by reloading this page.' : detail || 'The research service is unavailable. Please retry.');
  }
  return response.json();
}
export function usePilot(path) {
  return useQuery({ queryKey: ['pilot', path], queryFn: () => request(path), refetchInterval: 60000, retry: 1 });
}
export function lagosTime(stamp) {
  return stamp ? new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Africa/Lagos', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(new Date(stamp)) + ' WAT' : 'Not available';
}
