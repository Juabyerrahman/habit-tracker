
import { useTheme } from "../features/theme/ThemeContext";

interface PlaceholderPageProps {
  title: string;
  description: string;
}

export default function PlaceholderPage({
  title,
  description,
}: PlaceholderPageProps) {
  const { isDark } = useTheme();

  return (
    <section
      className={`min-h-[80vh] rounded-2xl border p-8 ${
        isDark
          ? "border-[#303030] bg-[#1b1b1b] text-white"
          : "border-neutral-200 bg-white text-neutral-900"
      }`}
    >
      <p className="text-xs font-semibold uppercase tracking-widest text-orange-500">
        Habit Tracker
      </p>

      <h1 className="mt-4 text-3xl font-bold">
        {title}
      </h1>

      <p
        className={`mt-3 max-w-lg text-sm leading-6 ${
          isDark ? "text-neutral-400" : "text-neutral-600"
        }`}
      >
        {description}
      </p>

      <div
        className={`mt-8 rounded-xl border border-dashed p-6 ${
          isDark ? "border-[#383838]" : "border-neutral-200"
        }`}
      >
        <p className="text-sm font-medium">
          This page is under development.
        </p>
        <p
          className={`mt-2 text-xs ${
            isDark ? "text-neutral-500" : "text-neutral-400"
          }`}
        >
          Your existing data and account remain unchanged.
        </p>
      </div>
    </section>
  );
}
