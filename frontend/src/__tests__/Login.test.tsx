import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import Login from '../pages/Login';
import * as api from '../api';

// Mock the API layer so we don't make real network requests
vi.mock('../api', () => ({
  apiLogin: vi.fn()
}));

const mockNavigate = vi.fn();
// Mock React Router's useNavigate
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Login Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render the login form correctly', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    expect(screen.getByText('Welcome Back')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('name@example.com')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Authenticate Access/i })).toBeInTheDocument();
  });

  it('should display an error message if the API call fails', async () => {
    const user = userEvent.setup();
    // Setup API mock to reject
    vi.mocked(api.apiLogin).mockRejectedValueOnce(new Error('Invalid Credentials'));

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    // Form starts with default values "admin@example.com", "AdminPass123!"
    const button = screen.getByRole('button', { name: /Authenticate Access/i });
    await user.click(button);

    // Verify error is shown
    await waitFor(() => {
      expect(screen.getByText('Invalid Credentials')).toBeInTheDocument();
    });
    
    // Verify it didn't navigate
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('should navigate to dashboard upon successful login', async () => {
    const user = userEvent.setup();
    // Setup API mock to succeed
    vi.mocked(api.apiLogin).mockResolvedValueOnce({
      access_token: 'mock_access',
      refresh_token: 'mock_refresh',
      token_type: 'bearer'
    });

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    // Overwrite the default email
    const emailInput = screen.getByPlaceholderText('name@example.com');
    await user.clear(emailInput);
    await user.type(emailInput, 'auditor@example.com');

    // Click submit
    const button = screen.getByRole('button', { name: /Authenticate Access/i });
    await user.click(button);

    // Verify api was called
    await waitFor(() => {
      expect(api.apiLogin).toHaveBeenCalledWith('auditor@example.com', 'AdminPass123!');
    });

    // Verify navigation happened
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
  });
});
