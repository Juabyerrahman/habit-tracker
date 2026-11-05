
import { useTheme } from "../features/theme/ThemeContext";

interface ThemeToggleProps {
  className?: string;
}

export default function ThemeToggle({
  className = "",
}: ThemeToggleProps) {
  const { isDark, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light mode" : "Switch to night mode"}
      className={`whitespace-nowrap rounded-lg border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-700 transition hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-200 dark:hover:bg-neutral-800 ${className}`}
    >
      {isDark ? "Light mode" : "Night mode"}
    </button>
  );
}
