'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '@/lib/api-client';

/* ── API response types (match apps/api/schemas.py) ── */

interface ProviderStatus {
  provider: string;
  connected: boolean;
  is_paper: boolean | null;
  key_names: string[];
}

interface KeyStatusResponse {
  providers: ProviderStatus[];
}

interface VerifyResponse {
  provider: string;
  valid: boolean;
  error?: string;
}

/* ── Per-provider UI state ── */

interface ProviderFormState {
  loading: boolean;
  error: string | null;
  verifyResult: VerifyResponse | null;
}

const INITIAL_FORM: ProviderFormState = {
  loading: false,
  error: null,
  verifyResult: null,
};

/* ── Badge components ── */

function ConnectedBadge() {
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
      Connected
    </span>
  );
}

function DisconnectedBadge() {
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
      Not connected
    </span>
  );
}

function PaperBadge({ isPaper }: { isPaper: boolean | null }) {
  if (isPaper === null) return null;
  return isPaper ? (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
      Paper
    </span>
  ) : (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
      Live
    </span>
  );
}

/* ── Main page ── */

export default function SettingsPage() {
  /* Provider status from backend */
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [statusError, setStatusError] = useState<string | null>(null);

  /* Per-provider form state */
  const [alpacaForm, setAlpacaForm] = useState<ProviderFormState>(INITIAL_FORM);
  const [finnhubForm, setFinnhubForm] = useState<ProviderFormState>(INITIAL_FORM);

  /* Alpaca form inputs */
  const [alpacaApiKey, setAlpacaApiKey] = useState('');
  const [alpacaSecretKey, setAlpacaSecretKey] = useState('');
  const [isPaper, setIsPaper] = useState(true);

  /* Finnhub form inputs */
  const [finnhubApiKey, setFinnhubApiKey] = useState('');

  /* ── Fetch status ── */

  const fetchStatus = useCallback(async () => {
    try {
      setStatusError(null);
      const res = await apiFetch('/api/keys/status');
      if (!res.ok) {
        throw new Error(`Status fetch failed (${res.status})`);
      }
      const data: KeyStatusResponse = await res.json();
      setProviders(data.providers);
    } catch (err) {
      setStatusError(err instanceof Error ? err.message : 'Failed to load key status');
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  /* ── Helpers ── */

  function getProvider(name: string): ProviderStatus | undefined {
    return providers.find((p) => p.provider === name);
  }

  /* ── Alpaca: Save & Verify ── */

  async function handleAlpacaSave(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setAlpacaForm({ loading: true, error: null, verifyResult: null });

    try {
      /* Store api_key */
      const res1 = await apiFetch('/api/keys/alpaca', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key_value: alpacaApiKey, key_name: 'api_key', is_paper: isPaper }),
      });
      if (!res1.ok) {
        const body = await res1.json().catch(() => null);
        throw new Error(body?.detail ?? `Failed to store API key (${res1.status})`);
      }

      /* Store secret_key */
      const res2 = await apiFetch('/api/keys/alpaca', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key_value: alpacaSecretKey, key_name: 'secret_key', is_paper: isPaper }),
      });
      if (!res2.ok) {
        throw new Error('Failed to store secret key — please retry');
      }

      /* Auto-verify */
      const verifyRes = await apiFetch('/api/keys/alpaca/verify', {
        method: 'POST',
      });
      const verifyData: VerifyResponse = await verifyRes.json();

      setAlpacaForm({ loading: false, error: null, verifyResult: verifyData });

      /* Clear inputs on success */
      setAlpacaApiKey('');
      setAlpacaSecretKey('');
    } catch (err) {
      setAlpacaForm({
        loading: false,
        error: err instanceof Error ? err.message : 'An unexpected error occurred',
        verifyResult: null,
      });
    }

    /* Always re-fetch status */
    await fetchStatus();
  }

  /* ── Alpaca: Verify only ── */

  async function handleAlpacaVerify() {
    setAlpacaForm((prev) => ({ ...prev, loading: true, error: null, verifyResult: null }));
    try {
      const res = await apiFetch('/api/keys/alpaca/verify', { method: 'POST' });
      const data: VerifyResponse = await res.json();
      setAlpacaForm({ loading: false, error: null, verifyResult: data });
    } catch (err) {
      setAlpacaForm({
        loading: false,
        error: err instanceof Error ? err.message : 'Verification failed',
        verifyResult: null,
      });
    }
  }

  /* ── Alpaca: Delete ── */

  async function handleAlpacaDelete() {
    if (!window.confirm('Delete all stored keys for Alpaca? This cannot be undone.')) return;
    setAlpacaForm({ loading: true, error: null, verifyResult: null });
    try {
      const res = await apiFetch('/api/keys/alpaca', { method: 'DELETE' });
      if (!res.ok) throw new Error(`Delete failed (${res.status})`);
    } catch (err) {
      setAlpacaForm({
        loading: false,
        error: err instanceof Error ? err.message : 'Delete failed',
        verifyResult: null,
      });
    }
    setAlpacaForm((prev) => ({ ...prev, loading: false }));
    await fetchStatus();
  }

  /* ── Finnhub: Save & Verify ── */

  async function handleFinnhubSave(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFinnhubForm({ loading: true, error: null, verifyResult: null });

    try {
      const res = await apiFetch('/api/keys/finnhub', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key_value: finnhubApiKey, key_name: 'api_key' }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? `Failed to store key (${res.status})`);
      }

      /* Auto-verify */
      const verifyRes = await apiFetch('/api/keys/finnhub/verify', { method: 'POST' });
      const verifyData: VerifyResponse = await verifyRes.json();

      setFinnhubForm({ loading: false, error: null, verifyResult: verifyData });

      /* Clear input on success */
      setFinnhubApiKey('');
    } catch (err) {
      setFinnhubForm({
        loading: false,
        error: err instanceof Error ? err.message : 'An unexpected error occurred',
        verifyResult: null,
      });
    }

    await fetchStatus();
  }

  /* ── Finnhub: Verify only ── */

  async function handleFinnhubVerify() {
    setFinnhubForm((prev) => ({ ...prev, loading: true, error: null, verifyResult: null }));
    try {
      const res = await apiFetch('/api/keys/finnhub/verify', { method: 'POST' });
      const data: VerifyResponse = await res.json();
      setFinnhubForm({ loading: false, error: null, verifyResult: data });
    } catch (err) {
      setFinnhubForm({
        loading: false,
        error: err instanceof Error ? err.message : 'Verification failed',
        verifyResult: null,
      });
    }
  }

  /* ── Finnhub: Delete ── */

  async function handleFinnhubDelete() {
    if (!window.confirm('Delete all stored keys for Finnhub? This cannot be undone.')) return;
    setFinnhubForm({ loading: true, error: null, verifyResult: null });
    try {
      const res = await apiFetch('/api/keys/finnhub', { method: 'DELETE' });
      if (!res.ok) throw new Error(`Delete failed (${res.status})`);
    } catch (err) {
      setFinnhubForm({
        loading: false,
        error: err instanceof Error ? err.message : 'Delete failed',
        verifyResult: null,
      });
    }
    setFinnhubForm((prev) => ({ ...prev, loading: false }));
    await fetchStatus();
  }

  /* ── Render ── */

  const alpaca = getProvider('alpaca');
  const finnhub = getProvider('finnhub');

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
      <p className="mt-2 text-gray-600">
        Manage your API keys for Alpaca and Finnhub. Keys are encrypted at rest.
      </p>

      {statusError && (
        <div
          className="mt-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm"
          role="alert"
        >
          {statusError}
        </div>
      )}

      <div className="mt-6 space-y-6">
        {/* ── Alpaca Card ── */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Alpaca</h2>
            <div className="flex items-center gap-2">
              {alpaca?.connected ? <ConnectedBadge /> : <DisconnectedBadge />}
              {alpaca?.connected && <PaperBadge isPaper={alpaca.is_paper} />}
            </div>
          </div>

          {/* Verify result */}
          {alpacaForm.verifyResult && (
            <div
              className={`mb-4 p-3 rounded-md text-sm ${
                alpacaForm.verifyResult.valid
                  ? 'bg-green-50 border border-green-200 text-green-700'
                  : 'bg-red-50 border border-red-200 text-red-700'
              }`}
              role="alert"
            >
              {alpacaForm.verifyResult.valid
                ? '✓ Alpaca keys verified — connection is working'
                : `✗ Verification failed: ${alpacaForm.verifyResult.error ?? 'Unknown error'}`}
            </div>
          )}

          {/* Error */}
          {alpacaForm.error && (
            <div
              className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm"
              role="alert"
            >
              {alpacaForm.error}
            </div>
          )}

          {alpaca?.connected ? (
            /* Connected state */
            <div className="space-y-3">
              <p className="text-sm text-gray-600">
                Stored keys:{' '}
                <span className="font-medium text-gray-900">{alpaca.key_names.join(', ')}</span>
              </p>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleAlpacaVerify}
                  disabled={alpacaForm.loading}
                  className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {alpacaForm.loading ? 'Verifying…' : 'Verify'}
                </button>
                <button
                  type="button"
                  onClick={handleAlpacaDelete}
                  disabled={alpacaForm.loading}
                  className="px-4 py-2 bg-red-50 text-red-700 text-sm rounded-md font-medium hover:bg-red-100 border border-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {alpacaForm.loading ? 'Deleting…' : 'Delete'}
                </button>
              </div>
            </div>
          ) : (
            /* Disconnected state — show form */
            <form onSubmit={handleAlpacaSave} className="space-y-4">
              <div>
                <label
                  htmlFor="alpaca-api-key"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  API Key
                </label>
                <input
                  id="alpaca-api-key"
                  type="password"
                  required
                  value={alpacaApiKey}
                  onChange={(e) => setAlpacaApiKey(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900"
                  placeholder="ALPACA_API_KEY"
                  disabled={alpacaForm.loading}
                />
              </div>

              <div>
                <label
                  htmlFor="alpaca-secret-key"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Secret Key
                </label>
                <input
                  id="alpaca-secret-key"
                  type="password"
                  required
                  value={alpacaSecretKey}
                  onChange={(e) => setAlpacaSecretKey(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900"
                  placeholder="ALPACA_SECRET_KEY"
                  disabled={alpacaForm.loading}
                />
              </div>

              <div className="flex items-center gap-3">
                <label htmlFor="alpaca-paper" className="relative inline-flex items-center cursor-pointer">
                  <input
                    id="alpaca-paper"
                    type="checkbox"
                    checked={isPaper}
                    onChange={(e) => setIsPaper(e.target.checked)}
                    disabled={alpacaForm.loading}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600" />
                </label>
                <span className="text-sm text-gray-700">
                  {isPaper ? 'Paper trading' : 'Live trading'}
                </span>
              </div>

              <button
                type="submit"
                disabled={alpacaForm.loading}
                className="w-full py-2 px-4 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {alpacaForm.loading ? 'Saving…' : 'Save & Verify'}
              </button>
            </form>
          )}
        </div>

        {/* ── Finnhub Card ── */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Finnhub</h2>
            {finnhub?.connected ? <ConnectedBadge /> : <DisconnectedBadge />}
          </div>

          {/* Verify result */}
          {finnhubForm.verifyResult && (
            <div
              className={`mb-4 p-3 rounded-md text-sm ${
                finnhubForm.verifyResult.valid
                  ? 'bg-green-50 border border-green-200 text-green-700'
                  : 'bg-red-50 border border-red-200 text-red-700'
              }`}
              role="alert"
            >
              {finnhubForm.verifyResult.valid
                ? '✓ Finnhub key verified — connection is working'
                : `✗ Verification failed: ${finnhubForm.verifyResult.error ?? 'Unknown error'}`}
            </div>
          )}

          {/* Error */}
          {finnhubForm.error && (
            <div
              className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm"
              role="alert"
            >
              {finnhubForm.error}
            </div>
          )}

          {finnhub?.connected ? (
            /* Connected state */
            <div className="space-y-3">
              <p className="text-sm text-gray-600">
                Stored keys:{' '}
                <span className="font-medium text-gray-900">{finnhub.key_names.join(', ')}</span>
              </p>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleFinnhubVerify}
                  disabled={finnhubForm.loading}
                  className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {finnhubForm.loading ? 'Verifying…' : 'Verify'}
                </button>
                <button
                  type="button"
                  onClick={handleFinnhubDelete}
                  disabled={finnhubForm.loading}
                  className="px-4 py-2 bg-red-50 text-red-700 text-sm rounded-md font-medium hover:bg-red-100 border border-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {finnhubForm.loading ? 'Deleting…' : 'Delete'}
                </button>
              </div>
            </div>
          ) : (
            /* Disconnected state — show form */
            <form onSubmit={handleFinnhubSave} className="space-y-4">
              <div>
                <label
                  htmlFor="finnhub-api-key"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  API Key
                </label>
                <input
                  id="finnhub-api-key"
                  type="password"
                  required
                  value={finnhubApiKey}
                  onChange={(e) => setFinnhubApiKey(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900"
                  placeholder="FINNHUB_API_KEY"
                  disabled={finnhubForm.loading}
                />
              </div>

              <button
                type="submit"
                disabled={finnhubForm.loading}
                className="w-full py-2 px-4 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {finnhubForm.loading ? 'Saving…' : 'Save & Verify'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
