import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuthStore } from '@/lib/store/auth';
import ThemeToggle from '@/components/ThemeToggle';

export default function Login() {
  const router = useRouter();
  const { signin, isLoading, error, clearError } = useAuthStore();
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const errors: Record<string, string> = {};

    if (!formData.username.trim()) {
      errors.username = 'Email or username is required';
    }

    if (!formData.password) {
      errors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      errors.password = 'Password must be at least 8 characters';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    if (validationErrors[name]) {
      setValidationErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
    
    if (error) clearError();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    const success = await signin(formData.username, formData.password);
    
    if (success) {
      setFormData({ username: '', password: '' });
      router.push('/Home');
    }
  };

  return (
    <div className="min-h-screen bg-background text-text flex flex-col">
      {/* Header */}
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
                href="/signup" 
                className="text-text-muted hover:text-text transition-colors duration-200 font-medium"
              >
                Sign up
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          {/* Login Card */}
          <div className="surface-secondary rounded-2xl border border-border p-8 bi-glow">
            <h1 className="text-3xl font-bold text-center mb-8">
              Welcome back
            </h1>

            {error && (
              <div className="mb-6 p-4 rounded-lg bg-red-900/20 border border-red-700 text-red-300">
                <div className="flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <span>{error}</span>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-6">
                <label htmlFor="username" className="block text-sm font-medium text-text-muted mb-2">
                  Email or Username
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
                  placeholder="Enter your email or username"
                  disabled={isLoading}
                  required
                />
                {validationErrors.username && (
                  <p className="mt-2 text-sm text-red-400">{validationErrors.username}</p>
                )}
              </div>

              <div className="mb-8">
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
                  placeholder="Enter your password"
                  disabled={isLoading}
                  required
                />
                {validationErrors.password && (
                  <p className="mt-2 text-sm text-red-400">{validationErrors.password}</p>
                )}
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 px-4 bi-gradient rounded-lg font-bold text-white hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Signing in...
                  </>
                ) : (
                  'Sign In'
                )}
              </button>
            </form>

            <div className="mt-8 pt-6 border-t border-border">
              <p className="text-center text-text-muted">
                Don&apos;t have an account?{' '}
                <Link href="/signup" className="text-blue-soft font-medium hover:text-blue-400">
                  Sign up
                </Link>
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}