
import { useEffect, useState } from "react";
import { apiRequest } from "../api/client";
import type {
  MonthlyGridResponse,
  CompletionResponse,
  HabitGridDay,
  Task,
  TaskListResponse,
  UpdateTaskResponse,
} from "../api/types";
import { useTheme } from "../features/theme/ThemeContext";
import CreateHabitModal from "../features/habits/CreateHabitModal";
import CreateTaskModal from "../features/tasks/CreateTaskModal";

function getMonthString(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

function getTodayString(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function shiftMonth(month: string, amount: number): string {
  const [year, monthNumber] = month.split("-").map(Number);
  return getMonthString(new Date(year, monthNumber - 1 + amount, 1));
}

function formatMonth(month: string): string {
  const [year, monthNumber] = month.split("-").map(Number);

  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    year: "numeric",
  }).format(new Date(year, monthNumber - 1, 1));
}

function formatDateNumber(day: HabitGridDay): string {
  return String(Number(day.date.slice(-2)));
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}

function DashboardPage() {
  const { isDark } = useTheme();

  // Modal state
  const [showCreateHabit, setShowCreateHabit] = useState(false);
  const [showCreateTask, setShowCreateTask] = useState(false);

  // Habit state
  const [month, setMonth] = useState(() => getMonthString(new Date()));
  const [grid, setGrid] = useState<MonthlyGridResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [gridError, setGridError] = useState<string | null>(null);
  const [savingCell, setSavingCell] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  // Task state
  const [tasks, setTasks] = useState<Task[]>([]);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [tasksError, setTasksError] = useState<string | null>(null);
  const [taskReloadKey, setTaskReloadKey] = useState(0);
  const [savingTaskId, setSavingTaskId] = useState<string | null>(null);

  const formattedDate = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(new Date());

  const theme = {
    page: isDark
      ? "bg-[#111111] text-white"
      : "bg-neutral-50 text-neutral-900",

    card: isDark
      ? "border-[#303030] bg-[#1b1b1b]"
      : "border-neutral-200 bg-white",

    heading: isDark ? "text-white" : "text-neutral-900",
    muted: isDark ? "text-neutral-400" : "text-neutral-500",
    subtle: isDark ? "text-neutral-500" : "text-neutral-400",

    outline: isDark
      ? "border-[#383838] text-neutral-300 hover:bg-[#292929]"
      : "border-neutral-200 text-neutral-700 hover:bg-neutral-50",

    button: isDark
      ? "bg-orange-500 text-black hover:bg-orange-400"
      : "bg-neutral-900 text-white hover:bg-neutral-700",

    dashed: isDark ? "border-[#383838]" : "border-neutral-200",
  };

  // Load the selected month's habit grid.
  useEffect(() => {
    let cancelled = false;

    async function loadGrid() {
      setLoading(true);
      setGridError(null);

      try {
        const result = await apiRequest<MonthlyGridResponse>(
          `/api/habits/grid?month=${encodeURIComponent(month)}`
        );

        if (!cancelled) {
          setGrid(result);
        }
      } catch (error) {
        if (!cancelled) {
          setGridError(getErrorMessage(error));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadGrid();

    return () => {
      cancelled = true;
    };
  }, [month, reloadKey]);

  // Load today's tasks.
  useEffect(() => {
    let cancelled = false;

    async function loadTasks() {
      setTasksLoading(true);
      setTasksError(null);

      try {
        const result = await apiRequest<TaskListResponse>(
          `/api/tasks?date=${encodeURIComponent(getTodayString())}`
        );

        if (!cancelled) {
          setTasks(result.tasks);
        }
      } catch (error) {
        if (!cancelled) {
          setTasksError(getErrorMessage(error));
        }
      } finally {
        if (!cancelled) {
          setTasksLoading(false);
        }
      }
    }

    void loadTasks();

    return () => {
      cancelled = true;
    };
  }, [taskReloadKey]);

  function retryGrid() {
    setReloadKey((current) => current + 1);
  }

  function retryTasks() {
    setTaskReloadKey((current) => current + 1);
  }

  // Toggle habit completion.
  async function toggleCompletion(
    habitId: string,
    day: HabitGridDay
  ) {
    if (!grid || savingCell) return;

    const lockedStatuses = [
      "before_start",
      "future",
      "archived",
    ];

    if (lockedStatuses.includes(day.status)) return;

    const cellKey = `${habitId}-${day.date}`;
    setSavingCell(cellKey);
    setGridError(null);

    try {
      if (day.completed) {
        await apiRequest<CompletionResponse>(
          `/api/habits/${encodeURIComponent(habitId)}/completions/${day.date}`,
          { method: "DELETE" }
        );

        setGrid((current) => {
          if (!current) return current;

          return {
            ...current,
            habits: current.habits.map((habit) =>
              habit.habit_id !== habitId
                ? habit
                : {
                    ...habit,
                    days: habit.days.map((item) =>
                      item.date !== day.date
                        ? item
                        : {
                            ...item,
                            completed: false,
                            is_bonus: false,
                            status: item.scheduled
                              ? item.date === current.today
                                ? "pending"
                                : "missed"
                              : "rest",
                          }
                    ),
                  }
            ),
          };
        });
      } else {
        const result = await apiRequest<CompletionResponse>(
          `/api/habits/${encodeURIComponent(habitId)}/completions/${day.date}`,
          { method: "PUT" }
        );

        setGrid((current) => {
          if (!current) return current;

          return {
            ...current,
            habits: current.habits.map((habit) =>
              habit.habit_id !== habitId
                ? habit
                : {
                    ...habit,
                    days: habit.days.map((item) =>
                      item.date !== day.date
                        ? item
                        : {
                            ...item,
                            completed: true,
                            is_bonus: Boolean(result.is_bonus),
                            status: result.is_bonus
                              ? "bonus"
                              : "completed",
                          }
                    ),
                  }
            ),
          };
        });
      }
    } catch (error) {
      setGridError(getErrorMessage(error));
    } finally {
      setSavingCell(null);
    }
  }

  // Toggle task completion.
  async function toggleTask(task: Task) {
    if (savingTaskId) return;

    setSavingTaskId(task.id);
    setTasksError(null);

    try {
      const result = await apiRequest<UpdateTaskResponse>(
        `/api/tasks/${encodeURIComponent(task.id)}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            is_completed: !task.is_completed,
          }),
        }
      );

      setTasks((current) =>
        current.map((item) =>
          item.id === task.id ? result.task : item
        )
      );
    } catch (error) {
      setTasksError(getErrorMessage(error));
    } finally {
      setSavingTaskId(null);
    }
  }

  function getCellStyle(day: HabitGridDay): string {
    if (day.status === "completed") {
      return isDark
        ? "border-orange-500 bg-orange-500 text-black hover:bg-orange-400"
        : "border-orange-500 bg-orange-500 text-white hover:bg-orange-600";
    }

    if (day.status === "bonus") {
      return isDark
        ? "border-orange-500/50 bg-orange-500/20 text-orange-400 hover:bg-orange-500/30"
        : "border-orange-300 bg-orange-100 text-orange-700 hover:bg-orange-200";
    }

    if (day.status === "missed") {
      return isDark
        ? "border-red-900 bg-red-950/40 text-red-400 hover:bg-red-950"
        : "border-red-200 bg-red-50 text-red-500 hover:bg-red-100";
    }

    if (day.status === "rest") {
      return isDark
        ? "border-[#383838] bg-[#252525] text-neutral-500 hover:border-orange-500"
        : "border-neutral-200 bg-neutral-100 text-neutral-400 hover:border-orange-400";
    }

    if (
      day.status === "future" ||
      day.status === "before_start" ||
      day.status === "archived"
    ) {
      return isDark
        ? "cursor-not-allowed border-[#292929] bg-[#151515] text-neutral-700"
        : "cursor-not-allowed border-neutral-100 bg-neutral-50 text-neutral-300";
    }

    return isDark
      ? "border-[#404040] bg-[#252525] text-neutral-300 hover:border-orange-500 hover:text-orange-400"
      : "border-neutral-300 bg-white text-neutral-500 hover:border-orange-400 hover:text-orange-600";
  }

  function getCellSymbol(day: HabitGridDay): string {
    if (day.status === "completed") return "✓";
    if (day.status === "bonus") return "+";
    if (day.status === "missed") return "×";
    if (day.status === "rest" || day.status === "future") return "·";
    if (day.status === "archived" || day.status === "before_start") return "—";
    return "";
  }

  const todayProgress = grid
    ? {
        completed: grid.habits.filter((habit) =>
          habit.days.some(
            (day) => day.date === grid.today && day.completed && !day.is_bonus
          )
        ).length,
        scheduled: grid.habits.filter((habit) =>
          habit.days.some(
            (day) => day.date === grid.today && day.scheduled
          )
        ).length,
      }
    : null;

  const monthlyStats = grid
    ? (() => {
        let completed = 0;
        let scheduled = 0;

        for (const habit of grid.habits) {
          for (const day of habit.days) {
            if (
              day.scheduled &&
              day.status !== "future" &&
              day.status !== "before_start" &&
              day.status !== "archived"
            ) {
              scheduled += 1;
              if (day.completed && !day.is_bonus) completed += 1;
            }
          }
        }

        return {
          completed,
          scheduled,
          rate: scheduled > 0
            ? Math.round((completed / scheduled) * 100)
            : 0,
        };
      })()
    : null;

  return (
    <div className={`min-w-0 ${theme.page}`}>
      {/* Dashboard header */}
      <header className="mb-8 flex min-w-0 flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <p className={`text-sm ${theme.muted}`}>{formattedDate}</p>

          <h1 className={`mt-2 text-3xl font-bold tracking-tight ${theme.heading}`}>
            Dashboard
          </h1>

          <p className={`mt-2 text-sm ${theme.muted}`}>
            Stay consistent. Make every day count.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowCreateHabit(true)}
          className={`shrink-0 rounded-lg px-5 py-3 text-sm font-medium transition ${theme.button}`}
        >
          + Add Habit
        </button>
      </header>

      {/* Summary cards */}
      <section className="mb-8 grid grid-cols-2 gap-4 xl:grid-cols-4">
        {[
          {
            title: "Habits tracked",
            value: grid ? grid.habits.length : "—",
          },
          {
            title: "Today's progress",
            value: todayProgress
              ? `${todayProgress.completed}/${todayProgress.scheduled}`
              : "—",
          },
          {
            title: "Current best streak",
            value: "—",
          },
          {
            title: "Monthly completion",
            value: monthlyStats ? `${monthlyStats.rate}%` : "—",
          },
        ].map((item) => (
          <div
            key={item.title}
            className={`min-w-0 rounded-xl border p-5 ${theme.card}`}
          >
            <p className={`text-xs font-medium ${theme.muted}`}>
              {item.title}
            </p>

            <p className={`mt-4 text-3xl font-semibold tracking-tight ${theme.heading}`}>
              {item.value}
            </p>
          </div>
        ))}
      </section>

      {/* Monthly habit tracker */}
      <section className={`mb-8 min-w-0 rounded-xl border p-4 sm:p-5 md:p-6 ${theme.card}`}>
        <div className="mb-6 flex min-w-0 flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h2 className={`text-lg font-semibold ${theme.heading}`}>
              Monthly habit tracker
            </h2>

            <p className={`mt-1 text-sm ${theme.muted}`}>
              Click a date to mark your habit complete.
            </p>
          </div>

          {/* Responsive month navigation */}
          <div className="flex w-full min-w-0 flex-wrap items-center gap-2 xl:w-auto xl:justify-end">
            <button
              type="button"
              onClick={() => setMonth((current) => shiftMonth(current, -1))}
              className={`rounded-lg border px-3 py-2 text-sm ${theme.outline}`}
              aria-label="Previous month"
            >
              ←
            </button>

            <span className={`min-w-0 flex-1 text-center text-sm font-semibold sm:min-w-32 sm:flex-none ${theme.heading}`}>
              {formatMonth(month)}
            </span>

            <button
              type="button"
              onClick={() => setMonth((current) => shiftMonth(current, 1))}
              className={`rounded-lg border px-3 py-2 text-sm ${theme.outline}`}
              aria-label="Next month"
            >
              →
            </button>

            <button
              type="button"
              onClick={() => setMonth(getMonthString(new Date()))}
              className={`rounded-lg border px-3 py-2 text-sm ${theme.outline}`}
            >
              Today
            </button>
          </div>
        </div>

        {/* Legend */}
        <div className="mb-5 flex flex-wrap gap-x-5 gap-y-2 text-xs">
          <span className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-sm bg-orange-500" />
            <span className={theme.muted}>Completed</span>
          </span>

          <span className="flex items-center gap-2">
            <span className={`h-3 w-3 rounded-sm border ${
              isDark
                ? "border-[#404040] bg-[#252525]"
                : "border-neutral-300 bg-neutral-100"
            }`} />
            <span className={theme.muted}>Rest / Pending</span>
          </span>

          <span className="flex items-center gap-2">
            <span className={`h-3 w-3 rounded-sm border ${
              isDark
                ? "border-red-900 bg-red-950/40"
                : "border-red-200 bg-red-50"
            }`} />
            <span className={theme.muted}>Missed</span>
          </span>

          <span className="flex items-center gap-2">
            <span className="flex h-3 w-3 items-center justify-center rounded-sm border border-orange-500/50 bg-orange-500/20 text-[9px] text-orange-500">
              +
            </span>
            <span className={theme.muted}>Bonus</span>
          </span>
        </div>

        {gridError && (
          <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-500">
            {gridError}

            <button
              type="button"
              onClick={retryGrid}
              className="ml-2 font-semibold underline"
            >
              Retry
            </button>
          </div>
        )}

        {loading ? (
          <div className={`flex min-h-48 items-center justify-center text-sm ${theme.muted}`}>
            Loading your monthly habits...
          </div>
        ) : grid && grid.habits.length === 0 ? (
          <div className={`flex min-h-48 flex-col items-center justify-center rounded-lg border border-dashed text-center ${theme.dashed}`}>
            <p className={`text-sm font-medium ${theme.heading}`}>
              No habits yet.
            </p>

            <p className={`mt-2 text-xs ${theme.muted}`}>
              Add your first habit to start tracking your progress.
            </p>
          </div>
        ) : grid ? (
          <div className="max-w-full overflow-x-auto rounded-lg border border-neutral-300/20">
            <table className="w-full min-w-max border-collapse text-center">
              <thead>
                <tr className={isDark ? "bg-[#252525]" : "bg-neutral-100"}>
                  <th className={`sticky left-0 z-20 min-w-48 border-b border-r p-3 text-left text-xs font-semibold ${theme.card} ${theme.heading}`}>
                    HABIT
                  </th>

                  {grid.habits[0]?.days.map((day) => (
                    <th
                      key={day.date}
                      className={`min-w-10 border-b p-2 text-xs font-semibold ${
                        day.date === grid.today ? "text-orange-500" : theme.muted
                      }`}
                    >
                      {formatDateNumber(day)}
                    </th>
                  ))}
                </tr>

                <tr className={isDark ? "bg-[#202020]" : "bg-neutral-50"}>
                  <th className={`sticky left-0 z-20 border-r p-2 text-left text-[10px] ${theme.card} ${theme.subtle}`}>
                    DAILY TRACKING
                  </th>

                  {grid.habits[0]?.days.map((day) => (
                    <th
                      key={day.date}
                      className={`p-2 text-[10px] ${theme.subtle}`}
                    >
                      {new Intl.DateTimeFormat("en-US", {
                        weekday: "narrow",
                      }).format(new Date(`${day.date}T12:00:00`))}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {grid.habits.map((habit) => {
                  const completedCount = habit.days.filter(
                    (day) => day.completed && !day.is_bonus
                  ).length;

                  const scheduledCount = habit.days.filter(
                    (day) =>
                      day.scheduled &&
                      day.status !== "future" &&
                      day.status !== "before_start" &&
                      day.status !== "archived"
                  ).length;

                  return (
                    <tr
                      key={habit.habit_id}
                      className={isDark ? "hover:bg-[#222222]" : "hover:bg-neutral-50"}
                    >
                      <td className={`sticky left-0 z-10 border-b border-r p-3 text-left ${theme.card}`}>
                        <div className="min-w-40">
                          <p className={`text-sm font-medium ${theme.heading}`}>
                            {habit.habit_name}
                          </p>

                          <p className={`mt-1 text-[10px] ${theme.subtle}`}>
                            {completedCount} / {scheduledCount} scheduled
                          </p>
                        </div>
                      </td>

                      {habit.days.map((day) => {
                        const cellKey = `${habit.habit_id}-${day.date}`;
                        const isSaving = savingCell === cellKey;

                        const disabled =
                          Boolean(savingCell) ||
                          [
                            "before_start",
                            "future",
                            "archived",
                          ].includes(day.status);

                        return (
                          <td key={day.date} className="border-b p-1">
                            <button
                              type="button"
                              title={`${habit.habit_name} — ${day.date} — ${day.status}`}
                              aria-label={`${habit.habit_name}, ${day.date}, ${day.status}`}
                              disabled={disabled}
                              onClick={() => void toggleCompletion(habit.habit_id, day)}
                              className={`flex h-7 w-7 items-center justify-center rounded-md border text-xs font-bold transition ${getCellStyle(day)} ${
                                isSaving ? "animate-pulse opacity-50" : ""
                              }`}
                            >
                              {getCellSymbol(day)}
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}

        <p className={`mt-4 text-xs ${theme.subtle}`}>
          Tip: Click an available date to complete a habit. Click it again to undo.
        </p>
      </section>

      {/* Today's tasks */}
      <section className={`mb-8 rounded-xl border p-5 md:p-6 ${theme.card}`}>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className={`text-lg font-semibold ${theme.heading}`}>
              Today's tasks
            </h2>

            <p className={`mt-1 text-sm ${theme.muted}`}>
              Your flexible daily to-do list.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setShowCreateTask(true)}
            className={`rounded-lg border px-4 py-2 text-sm ${theme.outline}`}
          >
            + Add task
          </button>
        </div>

        {tasksError && (
          <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-500">
            {tasksError}

            <button
              type="button"
              onClick={retryTasks}
              className="ml-2 font-semibold underline"
            >
              Retry
            </button>
          </div>
        )}

        {tasksLoading ? (
          <div className={`flex min-h-28 items-center justify-center text-sm ${theme.muted}`}>
            Loading today's tasks...
          </div>
        ) : tasks.length === 0 ? (
          <div className={`flex min-h-28 flex-col items-center justify-center rounded-lg border border-dashed ${theme.dashed}`}>
            <p className={`text-sm font-medium ${theme.heading}`}>
              No tasks for today.
            </p>

            <p className={`mt-2 text-xs ${theme.muted}`}>
              Add a task to organize your day.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => (
              <div
                key={task.id}
                className={`flex items-start gap-3 rounded-lg border p-3 transition ${
                  isDark
                    ? "border-[#383838] bg-[#202020]"
                    : "border-neutral-200 bg-neutral-50"
                }`}
              >
                <input
                  type="checkbox"
                  checked={task.is_completed}
                  disabled={savingTaskId !== null}
                  onChange={() => void toggleTask(task)}
                  aria-label={`Mark ${task.title} ${
                    task.is_completed ? "incomplete" : "complete"
                  }`}
                  className="mt-1 h-4 w-4 shrink-0 cursor-pointer accent-orange-500 disabled:cursor-not-allowed"
                />

                <div className="min-w-0 flex-1">
                  <p
                    className={`break-words text-sm font-medium ${
                      task.is_completed
                        ? "text-neutral-500 line-through"
                        : theme.heading
                    }`}
                  >
                    {task.title}
                  </p>

                  {task.notes && (
                    <p className={`mt-1 break-words text-xs ${theme.muted}`}>
                      {task.notes}
                    </p>
                  )}
                </div>

                {savingTaskId === task.id && (
                  <span className={`text-xs ${theme.subtle}`}>
                    Saving...
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        {!tasksLoading && tasks.length > 0 && (
          <p className={`mt-4 text-xs ${theme.muted}`}>
            {tasks.filter((task) => task.is_completed).length} of{" "}
            {tasks.length} tasks completed
          </p>
        )}
      </section>

      {/* Progress reports */}
      <section className={`rounded-xl border p-5 md:p-6 ${theme.card}`}>
        <h2 className={`text-lg font-semibold ${theme.heading}`}>
          Progress reports
        </h2>

        <p className={`mt-2 text-sm ${theme.muted}`}>
          Weekly and monthly insights will appear here.
        </p>
      </section>

      {/* Create Habit Modal */}
      {showCreateHabit && (
        <CreateHabitModal
          onClose={() => setShowCreateHabit(false)}
          onCreated={() => {
            setReloadKey((current) => current + 1);
          }}
        />
      )}

      {/* Create Task Modal */}
      {showCreateTask && (
        <CreateTaskModal
          onClose={() => setShowCreateTask(false)}
          onCreated={() => {
            setTaskReloadKey((current) => current + 1);
          }}
        />
      )}
    </div>
  );
}

export default DashboardPage;
