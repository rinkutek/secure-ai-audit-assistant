import { jwtDecode } from 'jwt-decode'

export function getAccessToken(): string | null { return localStorage.getItem('access_token') }
export function setTokens(access: string, refresh: string) { localStorage.setItem('access_token', access); localStorage.setItem('refresh_token', refresh) }
export function logout() { localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token') }

export function getUserRoles(): string[] {
    const token = getAccessToken()
    if (!token) return []
    try {
        const decoded = jwtDecode<any>(token)
        return decoded.roles || []
    } catch (e) {
        return []
    }
}
