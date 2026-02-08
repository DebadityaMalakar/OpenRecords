import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";

import ThemeToggle, { THEME_OPTIONS, THEME_STORAGE_KEY, applyTheme } from "@/components/ThemeToggle";
import { useAuthStore } from "@/lib/store/auth";

type ModelInfo = {
  id: string;
  name?: string;
  provider?: string;
  context_length?: number;
  categories?: string[];
};

type SettingsState = {
  defaultChatModel: string;
  defaultEmbedModel: string;
  theme: string;
  temperature: string;
};

export default function AccountSettings() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);
  const signout = useAuthStore((state) => state.signout);

  const [profile, setProfile] = useState({
    fullName: "",
    username: "",
    email: "",
  });
  const [profileStatus, setProfileStatus] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);

  const [settings, setSettings] = useState<SettingsState>({
    defaultChatModel: "",
    defaultEmbedModel: "",
    theme: "",
    temperature: "",
  });
  const [settingsStatus, setSettingsStatus] = useState<string | null>(null);
  const [settingsError, setSettingsError] = useState<string | null>(null);

  const [models, setModels] = useState<ModelInfo[]>([]);
  const [embedModels, setEmbedModels] = useState<ModelInfo[]>([]);
  const [modelsError, setModelsError] = useState<string | null>(null);

  const [passwordForm, setPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [passwordStatus, setPasswordStatus] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const [deletePassword, setDeletePassword] = useState("");
  const [deleteStatus, setDeleteStatus] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      router.push("/login");
      return;
    }
    setProfile({
      fullName: user.fullName,
      username: user.username,
      email: user.email,
    });
  }, [router, user]);

  useEffect(() => {
    if (!user) return;
    const loadSettings = async () => {
      try {
        const response = await fetch("/api/users/settings", { credentials: "include" });
        if (!response.ok) {
          const err = await response.json().catch(() => ({ detail: "Failed to load settings" }));
          throw new Error(err.detail || "Failed to load settings");
        }
        const data = await response.json();
        setSettings({
          defaultChatModel: data.default_chat_model || "",
          defaultEmbedModel: data.default_embed_model || "",
          theme: data.theme || "",
          temperature: data.temperature != null ? String(data.temperature) : "",
        });
        if (data.theme) {
          applyTheme(data.theme);
          window.localStorage.setItem(THEME_STORAGE_KEY, data.theme);
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to load settings";
        setSettingsError(message);
      }
    };

    void loadSettings();
  }, [user]);

  useEffect(() => {
    const loadModels = async () => {
      try {
        const [modelsRes, embedRes] = await Promise.all([
          fetch("/api/models", { credentials: "include" }),
          fetch("/api/models/embeddings", { credentials: "include" }),
        ]);

        if (!modelsRes.ok) {
          const err = await modelsRes.json().catch(() => ({ detail: "Failed to load models" }));
          throw new Error(err.detail || "Failed to load models");
        }

        if (!embedRes.ok) {
          const err = await embedRes.json().catch(() => ({ detail: "Failed to load embedding models" }));
          throw new Error(err.detail || "Failed to load embedding models");
        }

        const modelsData = await modelsRes.json();
        const embedData = await embedRes.json();

        const rawModels = Array.isArray(modelsData.models) ? modelsData.models : [];
        const chatModels = rawModels.filter((model: ModelInfo) => {
          const categories = model.categories || [];
          if (model.id?.toLowerCase().includes("embed")) return false;
          if (categories.includes("embedding")) return false;
          return categories.includes("chat") || categories.includes("text");
        });

        const rawEmbedModels = Array.isArray(embedData.models) ? embedData.models : [];

        setModels(chatModels);
        setEmbedModels(rawEmbedModels);
        setModelsError(null);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to load models";
        setModelsError(message);
      }
    };

    void loadModels();
  }, []);

  const themeOptions = [{ id: "", label: "System default" }, ...THEME_OPTIONS];

  const handleProfileSave = async () => {
    setProfileStatus(null);
    setProfileError(null);
    try {
      const response = await fetch("/api/users/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          full_name: profile.fullName,
          username: profile.username,
          email: profile.email,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to update profile");
      }
      setUser({
        id: data.id,
        fullName: data.full_name,
        username: data.username,
        email: data.email,
      });
      setProfileStatus("Profile updated");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to update profile";
      setProfileError(message);
    }
  };

  const handleSettingsSave = async () => {
    setSettingsStatus(null);
    setSettingsError(null);
    try {
      const response = await fetch("/api/users/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          default_chat_model: settings.defaultChatModel || null,
          default_embed_model: settings.defaultEmbedModel || null,
          theme: settings.theme || null,
          temperature: settings.temperature ? Number(settings.temperature) : null,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to update settings");
      }
      if (data.theme) {
        applyTheme(data.theme);
        window.localStorage.setItem(THEME_STORAGE_KEY, data.theme);
      }
      setSettingsStatus("Settings saved");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to update settings";
      setSettingsError(message);
    }
  };

  const handlePasswordSave = async () => {
    setPasswordStatus(null);
    setPasswordError(null);

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordError("New passwords do not match");
      return;
    }

    try {
      const response = await fetch("/api/users/me/password", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          current_password: passwordForm.currentPassword,
          new_password: passwordForm.newPassword,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || "Failed to change password");
      }
      setPasswordStatus("Password updated");
      setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to change password";
      setPasswordError(message);
    }
  };

  const handleDeleteAccount = async () => {
    setDeleteStatus(null);
    setDeleteError(null);

    try {
      const response = await fetch("/api/users/me", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ password: deletePassword }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || "Failed to delete account");
      }
      setDeleteStatus("Account deleted");
      await signout();
      router.push("/");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to delete account";
      setDeleteError(message);
    }
  };

  return (
    <div className="min-h-screen bg-background text-text">
      <header className="sticky top-0 z-40 border-b border-border bg-bg-secondary/90 backdrop-blur-md">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/Home" className="text-text-muted hover:text-text text-sm">
              Back to Home
            </Link>
            <span className="text-text-subtle text-xs">/</span>
            <h1 className="text-lg font-semibold">Account Settings</h1>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="container mx-auto px-6 py-10 space-y-10">
        <section className="rounded-2xl border border-border bg-bg-secondary/70 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold">Profile</h2>
              <p className="text-sm text-text-muted">Update your account details.</p>
            </div>
            {profileStatus && <span className="text-xs text-green-400">{profileStatus}</span>}
          </div>
          {profileError && <p className="text-sm text-red-400 mt-2">{profileError}</p>}
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <label className="text-sm">
              <span className="text-text-muted">Full name</span>
              <input
                value={profile.fullName}
                onChange={(event) => setProfile((prev) => ({ ...prev, fullName: event.target.value }))}
                className="mt-2 w-full rounded-lg border border-border bg-bg-tertiary px-3 py-2 text-sm"
              />
            </label>
            <label className="text-sm">
              <span className="text-text-muted">Username</span>
              <input
                value={profile.username}
                onChange={(event) => setProfile((prev) => ({ ...prev, username: event.target.value }))}
                className="mt-2 w-full rounded-lg border border-border bg-bg-tertiary px-3 py-2 text-sm"
              />
            </label>
            <label className="text-sm md:col-span-2">
              <span className="text-text-muted">Email</span>
              <input
                type="email"
                value={profile.email}
                onChange={(event) => setProfile((prev) => ({ ...prev, email: event.target.value }))}
                className="mt-2 w-full rounded-lg border border-border bg-bg-tertiary px-3 py-2 text-sm"
              />
            </label>
          </div>
          <div className="mt-6 flex justify-end">
            <button
              type="button"
              onClick={handleProfileSave}
              className="rounded-full bi-gradient px-5 py-2 text-sm font-semibold text-white"
            >
              Save profile
            </button>
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-bg-secondary/70 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold">Appearance</h2>
              <p className="text-sm text-text-muted">Choose a default theme for your account.</p>
            </div>
            {settingsStatus && <span className="text-xs text-green-400">{settingsStatus}</span>}
          </div>
          {settingsError && <p className="text-sm text-red-400 mt-2">{settingsError}</p>}
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <label className="text-sm">
              <span className="text-text-muted">Default theme</span>
              <select
                value={settings.theme}
                onChange={(event) => setSettings((prev) => ({ ...prev, theme: event.target.value }))}
                className="mt-2 w-full rounded-lg border border-border bg-bg-tertiary px-3 py-2 text-sm"
              >
                {themeOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="text-text-muted">Quick theme picker</span>
              <div className="mt-2">
                <ThemeToggle />
              </div>
            </label>
          </div>
          <div className="mt-6 flex justify-end">
            <button
              type="button"
              onClick={handleSettingsSave}
              className="rounded-full border border-border px-5 py-2 text-sm text-text hover:bg-bg-secondary"
            >
              Save appearance
            </button>
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-bg-secondary/70 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold">AI Defaults</h2>
              <p className="text-sm text-text-muted">Pick default models and generation settings.</p>
            </div>
            {settingsStatus && <span className="text-xs text-green-400">{settingsStatus}</span>}
          </div>
          {modelsError && <p className="text-sm text-red-400 mt-2">{modelsError}</p>}
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <label className="text-sm">
              <span className="text-text-muted">Default chat model</span>
              <select
                value={settings.defaultChatModel}
                onChange={(event) => setSettings((prev) => ({ ...prev, defaultChatModel: event.target.value }))}
                className="mt-2 w-full rounded-lg border border-border bg-bg-tertiary px-3 py-2 text-sm"
              >
                <option value="">System default</option>
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name || model.id}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="text-text-muted">Default embedding model</span>
              <select
                value={settings.defaultEmbedModel}
                onChange={(event) => setSettings((prev) => ({ ...prev, defaultEmbedModel: event.target.value }))}
                className="mt-2 w-full rounded-lg border border-border bg-bg-tertiary px-3 py-2 text-sm"
              >
                <option value="">System default</option>
                {embedModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name || model.id}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="text-text-muted">Temperature</span>
              <input
                type="number"
                min="0"
                max="2"
                step="0.1"
                value={settings.temperature}
                onChange={(event) => setSettings((prev) => ({ ...prev, temperature: event.target.value }))}
                className="mt-2 w-full rounded-lg border border-border bg-bg-tertiary px-3 py-2 text-sm"
                placeholder="0.7"
              />
            </label>
          </div>
          <div className="mt-6 flex justify-end">
            <button
              type="button"
              onClick={handleSettingsSave}
              className="rounded-full bi-gradient px-5 py-2 text-sm font-semibold text-white"
            >
              Save AI defaults
            </button>
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-bg-secondary/70 p-6">
          <div>
            <h2 className="text-xl font-semibold">Security</h2>
            <p className="text-sm text-text-muted">Change your password or remove your account.</p>
          </div>

          <div className="mt-6 rounded-xl border border-border bg-bg-tertiary/40 p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Change password</h3>
              {passwordStatus && <span className="text-xs text-green-400">{passwordStatus}</span>}
            </div>
            {passwordError && <p className="text-sm text-red-400 mt-2">{passwordError}</p>}
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <input
                type="password"
                placeholder="Current password"
                value={passwordForm.currentPassword}
                onChange={(event) =>
                  setPasswordForm((prev) => ({ ...prev, currentPassword: event.target.value }))
                }
                className="w-full rounded-lg border border-border bg-bg-secondary px-3 py-2 text-sm"
              />
              <input
                type="password"
                placeholder="New password"
                value={passwordForm.newPassword}
                onChange={(event) =>
                  setPasswordForm((prev) => ({ ...prev, newPassword: event.target.value }))
                }
                className="w-full rounded-lg border border-border bg-bg-secondary px-3 py-2 text-sm"
              />
              <input
                type="password"
                placeholder="Confirm new password"
                value={passwordForm.confirmPassword}
                onChange={(event) =>
                  setPasswordForm((prev) => ({ ...prev, confirmPassword: event.target.value }))
                }
                className="w-full rounded-lg border border-border bg-bg-secondary px-3 py-2 text-sm"
              />
            </div>
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={handlePasswordSave}
                className="rounded-full border border-border px-4 py-2 text-sm text-text hover:bg-bg-secondary"
              >
                Update password
              </button>
            </div>
          </div>

          <div className="mt-6 rounded-xl border border-red-500/40 bg-red-900/10 p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-red-300">Delete account</h3>
              {deleteStatus && <span className="text-xs text-red-300">{deleteStatus}</span>}
            </div>
            {deleteError && <p className="text-sm text-red-300 mt-2">{deleteError}</p>}
            <p className="text-xs text-red-200 mt-2">
              This permanently removes your account, records, and stored documents.
            </p>
            <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <input
                type="password"
                placeholder="Confirm password"
                value={deletePassword}
                onChange={(event) => setDeletePassword(event.target.value)}
                className="w-full rounded-lg border border-red-500/40 bg-bg-secondary px-3 py-2 text-sm"
              />
              <button
                type="button"
                onClick={handleDeleteAccount}
                className="rounded-full border border-red-500/60 px-4 py-2 text-sm text-red-200 hover:bg-red-900/30"
              >
                Delete account
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
