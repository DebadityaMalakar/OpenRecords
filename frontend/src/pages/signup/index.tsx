import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

import { useAuthStore } from '@/lib/store/auth';
import ThemeToggle from '@/components/ThemeToggle';

export default function SignUpPage() {
  const router = useRouter();
  const { signup, isLoading, error, clearError, setError } = useAuthStore();
  const [formData, setFormData] = useState({
    fullName: '',
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const errors: Record<string, string> = {};

    if (formData.fullName.trim().length < 2) {
      errors.fullName = 'Full name must be at least 2 characters';
    }

    if (!/^[a-zA-Z0-9_]{3,32}$/.test(formData.username)) {
      errors.username = 'Username must be 3-32 chars, letters, numbers, underscore';
    }

    if (!formData.email.includes('@')) {
      errors.email = 'Enter a valid email';
    }

    if (formData.password.length < 8) {
      errors.password = 'Password must be at least 8 characters';
    }

    if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) {
      setError('Please fix the highlighted fields');
      return;
    }

    const success = await signup(
      formData.fullName,
      formData.username,
      formData.email,
      formData.password
    );
    
    if (success) {
      router.push('/Home');
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (validationErrors[name]) {
      setValidationErrors(prev => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
    if (error) clearError();
  };

  return (
    <div className="min-h-screen bg-background text-text flex flex-col">
      <header className="border-b border-border bg-bg-secondary/80 backdrop-blur-md">
        <div className="container mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <Link href="/" className="flex items-center space-x-2 group">
              <div className="w-8 h-8 bi-gradient rounded-full"></div>
              <span className="text-2xl font-bold bi-gradient-text">OpenRecords</span>
            </Link>
            <div className="flex items-center space-x-4">
              <ThemeToggle />
              <Link 
                href="/login" 
                className="text-text-muted hover:text-text transition-colors duration-200 font-medium"
              >
                Login
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="surface-secondary rounded-2xl border border-border p-8 bi-glow">
            <h1 className="text-3xl font-bold text-center mb-2">
              Create your account
            </h1>
            <p className="text-text-muted text-center mb-8">
              Start building your private knowledge archive
            </p>

            {error && (
              <div className="mb-6 p-4 rounded-lg bg-red-900/20 border border-red-700 text-red-300">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="space-y-4">
                <div>
                  <label htmlFor="fullName" className="block text-sm font-medium text-text-muted mb-2">
                    Full Name
                  </label>
                  <input
                    type="text"
                    id="fullName"
                    name="fullName"
                    value={formData.fullName}
                    onChange={handleChange}
                    className={`w-full px-4 py-3 rounded-lg border bg-bg-tertiary text-text placeholder:text-text-subtle focus:outline-none focus:ring-2 focus:ring-blue-soft focus:border-transparent ${
                      validationErrors.fullName ? 'border-red-500' : 'border-border'
                    }`}
                    placeholder="Enter your full name"
                    required
                  />
                  {validationErrors.fullName && (
                    <p className="mt-2 text-sm text-red-400">{validationErrors.fullName}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-text-muted mb-2">
                    Username
                  </label>
                  <input
                    type="text"
                    id="username"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    className={`w-full px-4 py-3 rounded-lg border bg-bg-tertiary text-text placeholder:text-text-subtle focus:outline-none focus:ring-2 focus:ring-blue-soft focus:border-transparent ${
                      validationErrors.username ? 'border-red-500' : 'border-border'
                    }`}
                    placeholder="Choose a username"
                    required
                  />
                  {validationErrors.username && (
                    <p className="mt-2 text-sm text-red-400">{validationErrors.username}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-text-muted mb-2">
                    Email
                  </label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    className={`w-full px-4 py-3 rounded-lg border bg-bg-tertiary text-text placeholder:text-text-subtle focus:outline-none focus:ring-2 focus:ring-blue-soft focus:border-transparent ${
                      validationErrors.email ? 'border-red-500' : 'border-border'
                    }`}
                    placeholder="Enter your email"
                    required
                  />
                  {validationErrors.email && (
                    <p className="mt-2 text-sm text-red-400">{validationErrors.email}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-text-muted mb-2">
                    Password
                  </label>
                  <input
                    type="password"
                    id="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    className={`w-full px-4 py-3 rounded-lg border bg-bg-tertiary text-text placeholder:text-text-subtle focus:outline-none focus:ring-2 focus:ring-blue-soft focus:border-transparent ${
                      validationErrors.password ? 'border-red-500' : 'border-border'
                    }`}
                    placeholder="At least 6 characters"
                    required
                  />
                  {validationErrors.password && (
                    <p className="mt-2 text-sm text-red-400">{validationErrors.password}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-text-muted mb-2">
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    id="confirmPassword"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    className={`w-full px-4 py-3 rounded-lg border bg-bg-tertiary text-text placeholder:text-text-subtle focus:outline-none focus:ring-2 focus:ring-blue-soft focus:border-transparent ${
                      validationErrors.confirmPassword ? 'border-red-500' : 'border-border'
                    }`}
                    placeholder="Confirm your password"
                    required
                  />
                  {validationErrors.confirmPassword && (
                    <p className="mt-2 text-sm text-red-400">{validationErrors.confirmPassword}</p>
                  )}
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-8 py-3 px-4 bi-gradient rounded-lg font-bold text-white hover:shadow-lg transition-all duration-200 disabled:opacity-50"
              >
                {isLoading ? 'Creating account...' : 'Create Account'}
              </button>
            </form>

            <div className="mt-8 pt-6 border-t border-border">
              <p className="text-center text-text-muted">
                Already have an account?{' '}
                <Link href="/login" className="text-blue-soft font-medium hover:text-blue-400">
                  Log in
                </Link>
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}