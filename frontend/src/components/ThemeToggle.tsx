import { useEffect, useRef, useState } from "react";

type ThemeOption = {
  id: string;
  label: string;
  description: string;
};

export const THEME_OPTIONS: ThemeOption[] = [
  { id: "bi-dark", label: "Bi Dark", description: "Pastel bi pride" },
  { id: "bi-light", label: "Bi Light", description: "Pastel bi pride" },
  { id: "matcha", label: "Matcha", description: "Pastel green calm" },
  { id: "mocha", label: "Mocha", description: "Warm, cozy tones" },
  { id: "nord", label: "Nord", description: "Cool, arctic hues" },
  { id: "gruvbox", label: "Gruvbox", description: "Earthy retro palette" },
];

export const THEME_STORAGE_KEY = "openrecords-theme";

type ThemeToggleProps = {
  compact?: boolean;
};

const getInitialTheme = () => {
  if (typeof window === "undefined") return "bi-dark";
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored) return stored;
  return "bi-dark";
};

export const applyTheme = (themeId: string) => {
  if (typeof document === "undefined" || typeof window === "undefined") return;
  document.documentElement.setAttribute("data-theme", themeId);
  document.documentElement.style.colorScheme = themeId === "bi-light" ? "light" : "dark";
  window.localStorage.setItem(THEME_STORAGE_KEY, themeId);
};

export default function ThemeToggle({ compact = false }: ThemeToggleProps) {
  const [open, setOpen] = useState(false);
  const [currentTheme, setCurrentTheme] = useState<string>("bi-dark");
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const theme = getInitialTheme();
    setCurrentTheme(theme);
    applyTheme(theme);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (!menuRef.current) return;
      if (!menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const selected = THEME_OPTIONS.find((theme) => theme.id === currentTheme);

  const handleSelect = (themeId: string) => {
    setCurrentTheme(themeId);
    applyTheme(themeId);
    setOpen(false);
  };

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className={`inline-flex items-center gap-2 rounded-full border border-border bg-bg-tertiary px-3 py-2 text-sm text-text transition-colors hover:bg-bg-secondary ${
          compact ? "px-2" : ""
        }`}
        aria-label="Toggle theme"
      >
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bi-gradient text-white">
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 3a9 9 0 100 18 9 9 0 000-18z" />
            <path d="M12 3v18M3 12h18" />
          </svg>
        </span>
        {!compact && (
          <span className="font-medium">
            {selected ? selected.label : "Theme"}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-3 w-64 rounded-2xl border border-border bg-bg-secondary shadow-lg overflow-hidden z-50">
          <div className="px-4 py-3 text-xs uppercase tracking-wide text-text-subtle">
            Choose Theme
          </div>
          <div className="flex flex-col">
            {THEME_OPTIONS.map((theme) => (
              <button
                key={theme.id}
                type="button"
                onClick={() => handleSelect(theme.id)}
                className={`w-full text-left px-4 py-3 text-sm transition-colors hover:bg-bg-tertiary ${
                  theme.id === currentTheme ? "bg-bg-tertiary" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-text">{theme.label}</span>
                  {theme.id === currentTheme && (
                    <span className="text-xs text-text-muted">Active</span>
                  )}
                </div>
                <span className="text-xs text-text-muted">{theme.description}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
