
import { useEffect, useMemo, useState } from "react";
import { getMonthlyReport, getWeeklyReport } from "../api/reports";
import type { ProgressReport } from "../api/types";
import { useTheme } from "../features/theme/ThemeContext";

type PeriodMode = "weekly" | "monthly";

function getToday(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getMonday(date: Date): Date {
  const result = new Date(date);
  const day = result.getDay();
  result.setDate(result.getDate() - ((day + 6) % 7));
  return result;
}

function getMonth(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function formatPeriod(value: string, mode: PeriodMode): string {
  const date = new Date(`${value}T12:00:00`);

  if (mode === "monthly") {
    return new Intl.DateTimeFormat("en-US", {
      month: "long",
      year: "numeric",
    }).format(date);
  }

  const end = new Date(date);
  end.setDate(end.getDate() + 6);

  const formatter = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  });

  return `${formatter.format(date)} – ${formatter.format(end)}, ${end.getFullYear()}`;
}

function formatDay(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  }).format(new Date(`${value}T12:00:00`));
}

function formatRate(value: number | null): string {
  return value === null ? "—" : `${value}%`;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}

function ReportsPage() {
  const { isDark } = useTheme();

  const [mode, setMode] = useState<PeriodMode>("weekly");
  const [period, setPeriod] = useState(() => formatDate(getMonday(getToday())));
  const [report, setReport] = useState<ProgressReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const theme = {
    page: isDark ? "bg-[#111111] text-white" : "bg-neutral-50 text-neutral-900",
    card: isDark ? "border-[#303030] bg-[#1b1b1b]" : "border-neutral-200 bg-white",
    heading: isDark ? "text-white" : "text-neutral-900",
    muted: isDark ? "text-neutral-400" : "text-neutral-500",
    subtle: isDark ? "text-neutral-500" : "text-neutral-400",
    outline: isDark
      ? "border-[#383838] text-neutral-300 hover:bg-[#292929]"
      : "border-neutral-200 text-neutral-700 hover:bg-neutral-50",
    selected: isDark
      ? "bg-orange-500 text-black"
      : "bg-neutral-900 text-white",
  };

  useEffect(() => {
    let cancelled = false;

    async function loadReport() {
      setLoading(true);
      setError(null);

      try {
        const result =
          mode === "weekly"
            ? await getWeeklyReport(period)
            : await getMonthlyReport(period);

        if (!cancelled) {
          setReport(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(getErrorMessage(err));
          setReport(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadReport();

    return () => {
      cancelled = true;
    };
  }, [mode, period, reloadKey]);

  function changeMode(nextMode: PeriodMode) {
    setMode(nextMode);

    if (nextMode === "weekly") {
      setPeriod(formatDate(getMonday(getToday())));
    } else {
      setPeriod(getMonth(getToday()));
    }
  }

  function shiftPeriod(amount: number) {
    if (mode === "weekly") {
      const date = new Date(`${period}T12:00:00`);
      date.setDate(date.getDate() + amount * 7);
      setPeriod(formatDate(date));
    } else {
      const [year, month] = period.split("-").map(Number);
      const date = new Date(year, month - 1 + amount, 1);
      setPeriod(getMonth(date));
    }
  }

  const isCurrentPeriod = useMemo(() => {
    if (mode === "weekly") {
      return period === formatDate(getMonday(getToday()));
    }

    return period === getMonth(getToday());
  }, [mode, period]);

  const trends = report?.daily_trends ?? [];

  return (
    <div className={`min-w-0 ${theme.page}`}>
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className={`text-sm ${theme.muted}`}>Your consistency, measured.</p>
          <h1 className={`mt-2 text-3xl font-bold tracking-tight ${theme.heading}`}>
            Progress Reports
          </h1>
          <p className={`mt-2 text-sm ${theme.muted}`}>
            Understand your habits, tasks, and daily performance.
          </p>
        </div>
      </header>

      {/* Period controls */}
      <section className={`mb-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border p-4 ${theme.card}`}>
        <div className="flex gap-2">
          {(["weekly", "monthly"] as const).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => changeMode(item)}
              className={`rounded-lg px-4 py-2 text-sm font-medium capitalize transition ${
                mode === item ? theme.selected : theme.outline + " border"
              }`}
            >
              {item}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => shiftPeriod(-1)}
            className={`rounded-lg border px-3 py-2 text-sm ${theme.outline}`}
            aria-label="Previous period"
          >
            ←
          </button>

          <span className={`min-w-36 text-center text-sm font-semibold ${theme.heading}`}>
            {formatPeriod(period, mode)}
          </span>

          <button
            type="button"
            onClick={() => shiftPeriod(1)}
            disabled={isCurrentPeriod}
            className={`rounded-lg border px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-30 ${theme.outline}`}
            aria-label="Next period"
          >
            →
          </button>

          <button
            type="button"
            onClick={() => changeMode(mode)}
            className={`rounded-lg border px-3 py-2 text-sm ${theme.outline}`}
          >
            Today
          </button>
        </div>
      </section>

      {error && (
        <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-500">
          {error}
          <button
            type="button"
            onClick={() => setReloadKey((value) => value + 1)}
            className="ml-2 font-semibold underline"
          >
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className={`flex min-h-64 items-center justify-center text-sm ${theme.muted}`}>
          Loading your report...
        </div>
      ) : report ? (
        <>
          {/* Overview */}
          <section className="mb-8 grid grid-cols-2 gap-4 xl:grid-cols-4">
            {[
              {
                title: "Overall completion",
                value: formatRate(report.overview.overall_completion_rate),
                detail: `${report.overview.overall_completed} / ${report.overview.overall_total} completed`,
              },
              {
                title: "Habit completion",
                value: formatRate(report.overview.habit_completion_rate),
                detail: `${report.overview.habit_completed} / ${report.overview.habit_scheduled} completed`,
              },
              {
                title: "Task completion",
                value: formatRate(report.overview.task_completion_rate),
                detail: `${report.overview.task_completed} / ${report.overview.task_total} completed`,
              },
              {
                title: "Missed habits",
                value: String(report.overview.habit_missed),
                detail: `${report.overview.habit_pending} still pending`,
              },
            ].map((item) => (
              <div key={item.title} className={`min-w-0 rounded-xl border p-5 ${theme.card}`}>
                <p className={`text-xs font-medium ${theme.muted}`}>{item.title}</p>
                <p className={`mt-4 text-3xl font-semibold tracking-tight ${theme.heading}`}>
                  {item.value}
                </p>
                <p className={`mt-2 text-xs ${theme.subtle}`}>{item.detail}</p>
              </div>
            ))}
          </section>

          {/* Daily chart */}
          <section className={`mb-8 rounded-xl border p-5 md:p-6 ${theme.card}`}>
            <div className="mb-6">
              <h2 className={`text-lg font-semibold ${theme.heading}`}>
                Daily progress
              </h2>
              <p className={`mt-1 text-sm ${theme.muted}`}>
                Percentage of scheduled habits and tasks completed each day.
              </p>
            </div>

            {trends.length === 0 ? (
              <p className={`py-12 text-center text-sm ${theme.muted}`}>
                No activity recorded in this period yet.
              </p>
            ) : (
              <div className="w-full overflow-x-auto">
                <div className="flex h-64 min-w-max items-end gap-3 border-b border-neutral-300/20 px-2">
                  {trends.map((day) => {
                    const rate = day.overall_completion_rate ?? 0;

                    return (
                      <div
                        key={day.date}
                        className="flex h-full w-10 flex-col items-center justify-end gap-2"
                        title={`${formatDay(day.date)}: ${formatRate(day.overall_completion_rate)}`}
                      >
                        <span className={`text-[10px] ${theme.muted}`}>
                          {day.overall_completion_rate === null ? "—" : `${rate}%`}
                        </span>

                        <div className="flex h-44 w-7 items-end overflow-hidden rounded-t-md bg-neutral-500/10">
                          <div
                            className="w-full rounded-t-md bg-orange-500 transition-all"
                            style={{ height: `${rate}%` }}
                          />
                        </div>

                        <span className={`text-[10px] ${theme.muted}`}>
                          {Number(day.date.slice(-2))}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </section>

          {/* Habit analysis */}
          <section className="mb-8 grid gap-4 lg:grid-cols-2">
            {[
              {
                title: "Strongest habits",
                items: report.strongest_habits,
                empty: "No completed habit data available.",
              },
              {
                title: "Habits needing attention",
                items: report.weakest_habits,
                empty: "No habit data available.",
              },
            ].map((group) => (
              <div key={group.title} className={`rounded-xl border p-5 md:p-6 ${theme.card}`}>
                <h2 className={`mb-5 text-lg font-semibold ${theme.heading}`}>
                  {group.title}
                </h2>

                {group.items.length === 0 ? (
                  <p className={`text-sm ${theme.muted}`}>{group.empty}</p>
                ) : (
                  <div className="space-y-5">
                    {group.items.map((habit) => (
                      <div key={habit.habit_id}>
                        <div className="mb-2 flex items-center justify-between gap-3">
                          <span className={`truncate text-sm font-medium ${theme.heading}`}>
                            {habit.habit_name}
                          </span>
                          <span className="shrink-0 text-sm font-semibold text-orange-500">
                            {formatRate(habit.completion_rate)}
                          </span>
                        </div>

                        <div className="h-2 overflow-hidden rounded-full bg-neutral-500/15">
                          <div
                            className="h-full rounded-full bg-orange-500"
                            style={{ width: `${habit.completion_rate ?? 0}%` }}
                          />
                        </div>

                        <p className={`mt-2 text-xs ${theme.subtle}`}>
                          {habit.completed_days} of {habit.scheduled_days} scheduled days
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </section>

          {/* All habits */}
          <section className={`mb-8 overflow-hidden rounded-xl border ${theme.card}`}>
            <div className="p-5 md:p-6">
              <h2 className={`text-lg font-semibold ${theme.heading}`}>
                Habit breakdown
              </h2>
              <p className={`mt-1 text-sm ${theme.muted}`}>
                Every habit included in this period, including historical archived habits.
              </p>
            </div>

            {report.habits.length === 0 ? (
              <p className={`px-5 pb-6 text-sm ${theme.muted}`}>
                No habits tracked during this period.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] text-left text-sm">
                  <thead className={isDark ? "bg-[#252525]" : "bg-neutral-50"}>
                    <tr className={theme.muted}>
                      <th className="px-5 py-3 font-medium">Habit</th>
                      <th className="px-5 py-3 font-medium">Completed</th>
                      <th className="px-5 py-3 font-medium">Missed</th>
                      <th className="px-5 py-3 font-medium">Pending</th>
                      <th className="px-5 py-3 font-medium">Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.habits.map((habit) => (
                      <tr key={habit.habit_id} className="border-t border-neutral-500/15">
                        <td className={`px-5 py-4 font-medium ${theme.heading}`}>
                          {habit.habit_name}
                        </td>
                        <td className={`px-5 py-4 ${theme.muted}`}>
                          {habit.completed_days}/{habit.scheduled_days}
                        </td>
                        <td className="px-5 py-4 text-red-500">
                          {habit.missed_days}
                        </td>
                        <td className={`px-5 py-4 ${theme.muted}`}>
                          {habit.pending_days}
                        </td>
                        <td className="px-5 py-4 font-semibold text-orange-500">
                          {formatRate(habit.completion_rate)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Best and worst days */}
          <section className="grid gap-4 sm:grid-cols-2">
            {[
              { title: "Best day", day: report.best_day },
              { title: "Lowest-performing day", day: report.worst_day },
            ].map((item) => (
              <div key={item.title} className={`rounded-xl border p-5 ${theme.card}`}>
                <p className={`text-sm ${theme.muted}`}>{item.title}</p>
                {item.day ? (
                  <>
                    <p className={`mt-3 text-xl font-semibold ${theme.heading}`}>
                      {formatDay(item.day.date)}
                    </p>
                    <p className="mt-2 text-2xl font-bold text-orange-500">
                      {formatRate(item.day.overall_completion_rate)}
                    </p>
                    <p className={`mt-2 text-xs ${theme.subtle}`}>
                      {item.day.overall_completed} of {item.day.overall_total} tracked items completed
                    </p>
                  </>
                ) : (
                  <p className={`mt-3 text-sm ${theme.muted}`}>
                    Not enough activity to calculate.
                  </p>
                )}
              </div>
            ))}
          </section>

          <p className={`mt-6 text-xs ${theme.subtle}`}>
            Report covers {report.period.start} through {report.period.through ?? "no recorded days"}.
            Future dates are excluded.
          </p>
        </>
      ) : (
        <div className={`rounded-xl border p-10 text-center ${theme.card}`}>
          <p className={`text-sm ${theme.muted}`}>
            Your report couldn't be loaded. Please try again.
          </p>
          <button
            type="button"
            onClick={() => setReloadKey((value) => value + 1)}
            className={`mt-4 rounded-lg px-4 py-2 text-sm ${theme.selected}`}
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}

export default ReportsPage;
