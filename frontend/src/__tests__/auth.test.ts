import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setTokens, getAccessToken, logout, getUserRoles } from '../auth';

// Mock jwt-decode since we don't have a real JWT to decode in the unit test
vi.mock('jwt-decode', () => ({
  jwtDecode: vi.fn((token: string) => {
    if (token === 'valid.mock.token') {
      return { roles: ['admin', 'viewer'] };
    }
    throw new Error('Invalid token');
  })
}));

describe('Auth Utilities', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('should save and retrieve tokens from localStorage', () => {
    setTokens('access123', 'refresh123');
    expect(getAccessToken()).toBe('access123');
    expect(localStorage.getItem('refresh_token')).toBe('refresh123');
  });

  it('should clear tokens from localStorage', () => {
    setTokens('access123', 'refresh123');
    logout();
    expect(getAccessToken()).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('should safely decode roles from a valid JWT', () => {
    setTokens('valid.mock.token', 'refresh123');
    const roles = getUserRoles();
    expect(roles).toEqual(['admin', 'viewer']);
  });

  it('should return empty array for roles if token is missing or invalid', () => {
    expect(getUserRoles()).toEqual([]);
    
    setTokens('invalid.token', 'refresh123');
    expect(getUserRoles()).toEqual([]);
  });
});
