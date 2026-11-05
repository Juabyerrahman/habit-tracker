
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { apiRequest } from "../api/client";
import CreateHabitModal from "../features/habits/CreateHabitModal";
import { useTheme } from "../features/theme/ThemeContext";

interface Habit {
  id: string;
  name: string;
  description: string;
  category: string | null;
  icon: string | null;
  start_date: string;
  schedule: number[];
  sort_order: number;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

interface HabitsResponse {
  habits: Habit[];
}

interface HabitResponse {
  habit: Habit;
}

const weekdays = [
  { label: "Mon", value: 0 },
  { label: "Tue", value: 1 },
  { label: "Wed", value: 2 },
  { label: "Thu", value: 3 },
  { label: "Fri", value: 4 },
  { label: "Sat", value: 5 },
  { label: "Sun", value: 6 },
];

function formatDate(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function getToday() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getScheduleLabel(schedule: number[]) {
  if (schedule.length === 7) return "Every day";
  if (schedule.length === 5 && [0, 1, 2, 3, 4].every((d) => schedule.includes(d))) {
    return "Weekdays";
  }
  if (schedule.length === 2 && schedule.includes(5) && schedule.includes(6)) {
    return "Weekends";
  }
  return weekdays
    .filter((day) => schedule.includes(day.value))
    .map((day) => day.label)
    .join(", ");
}

export default function HabitsPage() {
  const { isDark } = useTheme();

  const [habits, setHabits] = useState<Habit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingHabit, setEditingHabit] = useState<Habit | null>(null);
  const [busyHabitId, setBusyHabitId] = useState<string | null>(null);

  const pageText = isDark ? "text-white" : "text-neutral-900";
  const mutedText = isDark ? "text-neutral-400" : "text-neutral-500";
  const cardStyle = isDark
    ? "border-[#303030] bg-[#191919]"
    : "border-neutral-200 bg-white";
  const secondaryButton = isDark
    ? "border-[#404040] text-neutral-300 hover:bg-[#292929]"
    : "border-neutral-300 text-neutral-700 hover:bg-neutral-100";

  const loadHabits = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const query = showArchived ? "?include_archived=true" : "";
      const response = await apiRequest<HabitsResponse>(
        `/api/habits${query}`
      );
      setHabits(response.habits);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load habits."
      );
    } finally {
      setLoading(false);
    }
  }, [showArchived]);

  useEffect(() => {
    void loadHabits();
  }, [loadHabits]);

  async function handleArchive(habit: Habit) {
    const confirmed = window.confirm(
      `Archive "${habit.name}"? Its history will be preserved.`
    );
    if (!confirmed) return;

    setBusyHabitId(habit.id);
    setError(null);

    try {
      await apiRequest<HabitResponse>(
        `/api/habits/${habit.id}/archive`,
        { method: "POST" }
      );
      await loadHabits();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not archive habit.");
    } finally {
      setBusyHabitId(null);
    }
  }

  async function handleRestore(habit: Habit) {
    setBusyHabitId(habit.id);
    setError(null);

    try {
      await apiRequest<HabitResponse>(
        `/api/habits/${habit.id}/restore`,
        { method: "POST" }
      );
      await loadHabits();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not restore habit.");
    } finally {
      setBusyHabitId(null);
    }
  }

  return (
    <div className={`mx-auto w-full max-w-7xl space-y-7 ${pageText}`}>
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">My Habits</h1>
          <p className={`mt-1 text-sm ${mutedText}`}>
            Build consistency by managing your recurring habits.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowCreateModal(true)}
          className="rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-black transition hover:bg-orange-400"
        >
          + Create habit
        </button>
      </header>

      <section className={`rounded-xl border p-4 ${cardStyle}`}>
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <p className="text-sm font-semibold">
              {showArchived ? "Archived habits" : "Active habits"}
            </p>
            <p className={`mt-1 text-xs ${mutedText}`}>
              {showArchived
                ? "Archived habits are read-only. Restore one to manage it again."
                : "Your recurring habits and their current schedules."}
            </p>
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setShowArchived(false)}
              aria-pressed={!showArchived}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                !showArchived
                  ? "bg-orange-500 text-black"
                  : secondaryButton + " border"
              }`}
            >
              Active
            </button>
            <button
              type="button"
              onClick={() => setShowArchived(true)}
              aria-pressed={showArchived}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                showArchived
                  ? "bg-orange-500 text-black"
                  : secondaryButton + " border"
              }`}
            >
              Archived
            </button>
          </div>
        </div>
      </section>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-500"
        >
          {error}
          <button
            type="button"
            onClick={() => void loadHabits()}
            className="ml-3 font-semibold underline"
          >
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className={`py-16 text-center text-sm ${mutedText}`}>
          Loading habits...
        </div>
      ) : habits.length === 0 ? (
        <section className={`rounded-xl border px-5 py-16 text-center ${cardStyle}`}>
          <div className="text-3xl">◎</div>
          <h2 className="mt-3 text-lg font-semibold">
            {showArchived ? "No archived habits" : "No habits yet"}
          </h2>
          <p className={`mx-auto mt-2 max-w-md text-sm ${mutedText}`}>
            {showArchived
              ? "Habits you archive will appear here. You can restore them whenever you want."
              : "Start with one small habit. Consistency matters more than creating a long list."}
          </p>
          {!showArchived && (
            <button
              type="button"
              onClick={() => setShowCreateModal(true)}
              className="mt-5 rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-black hover:bg-orange-400"
            >
              Create your first habit
            </button>
          )}
        </section>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <p className={`text-sm ${mutedText}`}>
              {habits.length} {habits.length === 1 ? "habit" : "habits"}
            </p>
            <button
              type="button"
              onClick={() => void loadHabits()}
              className={`text-sm ${mutedText} hover:text-orange-500`}
            >
              Refresh
            </button>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {habits.map((habit) => {
              const isBusy = busyHabitId === habit.id;

              return (
                <article
                  key={habit.id}
                  className={`rounded-xl border p-5 transition ${cardStyle}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex min-w-0 items-start gap-3">
                      <div
                        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-xl ${
                          isDark ? "bg-[#292929]" : "bg-neutral-100"
                        }`}
                      >
                        {habit.icon || "◎"}
                      </div>

                      <div className="min-w-0">
                        <h2 className="break-words font-semibold">
                          {habit.name}
                        </h2>
                        {habit.category && (
                          <span className={`mt-1 inline-block text-xs ${mutedText}`}>
                            {habit.category}
                          </span>
                        )}
                      </div>
                    </div>

                    {habit.archived_at && (
                      <span className="shrink-0 rounded-full bg-neutral-500/15 px-3 py-1 text-xs text-neutral-500">
                        Archived
                      </span>
                    )}
                  </div>

                  {habit.description && (
                    <p className={`mt-4 whitespace-pre-wrap text-sm ${mutedText}`}>
                      {habit.description}
                    </p>
                  )}

                  <div className={`mt-5 space-y-2 border-t pt-4 text-sm ${
                    isDark ? "border-[#303030]" : "border-neutral-100"
                  }`}>
                    <div className="flex justify-between gap-3">
                      <span className={mutedText}>Schedule</span>
                      <span className="text-right font-medium">
                        {getScheduleLabel(habit.schedule)}
                      </span>
                    </div>
                    <div className="flex justify-between gap-3">
                      <span className={mutedText}>Start date</span>
                      <span className="font-medium">
                        {formatDate(habit.start_date)}
                      </span>
                    </div>
                  </div>

                  <div className={`mt-5 flex flex-wrap justify-end gap-2 border-t pt-4 ${
                    isDark ? "border-[#303030]" : "border-neutral-100"
                  }`}>
                    {habit.archived_at ? (
                      <button
                        type="button"
                        disabled={isBusy}
                        onClick={() => void handleRestore(habit)}
                        className="rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-black hover:bg-orange-400 disabled:opacity-50"
                      >
                        {isBusy ? "Restoring..." : "Restore"}
                      </button>
                    ) : (
                      <>
                        <button
                          type="button"
                          disabled={isBusy}
                          onClick={() => setEditingHabit(habit)}
                          className={`rounded-lg border px-4 py-2 text-sm font-medium ${secondaryButton} disabled:opacity-50`}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          disabled={isBusy}
                          onClick={() => void handleArchive(habit)}
                          className="rounded-lg border border-red-500/30 px-4 py-2 text-sm font-medium text-red-500 hover:bg-red-500/10 disabled:opacity-50"
                        >
                          {isBusy ? "Archiving..." : "Archive"}
                        </button>
                      </>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </>
      )}

      {showCreateModal && (
        <CreateHabitModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => void loadHabits()}
        />
      )}

      {editingHabit && (
        <EditHabitModal
          habit={editingHabit}
          onClose={() => setEditingHabit(null)}
          onUpdated={() => {
            setEditingHabit(null);
            void loadHabits();
          }}
        />
      )}
    </div>
  );
}

function EditHabitModal({
  habit,
  onClose,
  onUpdated,
}: {
  habit: Habit;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const { isDark } = useTheme();

  const [name, setName] = useState(habit.name);
  const [description, setDescription] = useState(habit.description);
  const [category, setCategory] = useState(habit.category || "");
  const [icon, setIcon] = useState(habit.icon || "");
  const [startDate, setStartDate] = useState(habit.start_date);
  const [schedule, setSchedule] = useState<number[]>(habit.schedule);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const panelStyle = isDark
    ? "border-[#383838] bg-[#1b1b1b] text-white"
    : "border-neutral-200 bg-white text-neutral-900";
  const inputStyle = isDark
    ? "border-[#404040] bg-[#202020] text-white"
    : "border-neutral-300 bg-white text-neutral-900";
  const labelStyle = isDark ? "text-neutral-300" : "text-neutral-700";

  function toggleDay(day: number) {
    setSchedule((current) =>
      current.includes(day)
        ? current.filter((value) => value !== day)
        : [...current, day].sort((a, b) => a - b)
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Habit name is required.");
      return;
    }

    if (schedule.length === 0) {
      setError("Select at least one scheduled day.");
      return;
    }

    const updates: Record<string, unknown> = {};

    if (name.trim() !== habit.name) updates.name = name.trim();
    if (description.trim() !== habit.description) updates.description = description.trim();
    if (category.trim() !== (habit.category || "")) updates.category = category.trim() || null;
    if (icon.trim() !== (habit.icon || "")) updates.icon = icon.trim() || null;
    if (startDate !== habit.start_date) updates.start_date = startDate;
    if (
      schedule.length !== habit.schedule.length ||
      !schedule.every((day) => habit.schedule.includes(day))
    ) {
      updates.schedule = schedule;
    }

    if (Object.keys(updates).length === 0) {
      onClose();
      return;
    }

    setSaving(true);

    try {
      await apiRequest<HabitResponse>(`/api/habits/${habit.id}`, {
        method: "PATCH",
        body: JSON.stringify(updates),
      });
      onUpdated();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not update the habit."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-black/60 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !saving) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-habit-title"
        className={`my-auto w-full max-w-xl rounded-2xl border p-6 shadow-2xl ${panelStyle}`}
      >
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 id="edit-habit-title" className="text-xl font-bold">
              Edit habit
            </h2>
            <p className={`mt-1 text-sm ${isDark ? "text-neutral-400" : "text-neutral-500"}`}>
              Changes to the schedule apply from today onward.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            aria-label="Close"
            className="rounded-lg px-3 py-1 text-xl text-neutral-500 hover:bg-neutral-500/10"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="edit-habit-name" className={`mb-2 block text-sm font-medium ${labelStyle}`}>
              Habit name *
            </label>
            <input
              id="edit-habit-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={100}
              required
              className={`w-full rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-orange-500 ${inputStyle}`}
            />
          </div>

          <div>
            <label htmlFor="edit-habit-description" className={`mb-2 block text-sm font-medium ${labelStyle}`}>
              Description
            </label>
            <textarea
              id="edit-habit-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={500}
              rows={2}
              className={`w-full resize-y rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-orange-500 ${inputStyle}`}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="edit-habit-category" className={`mb-2 block text-sm font-medium ${labelStyle}`}>
                Category
              </label>
              <input
                id="edit-habit-category"
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                maxLength={50}
                className={`w-full rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-orange-500 ${inputStyle}`}
              />
            </div>
            <div>
              <label htmlFor="edit-habit-icon" className={`mb-2 block text-sm font-medium ${labelStyle}`}>
                Icon
              </label>
              <input
                id="edit-habit-icon"
                value={icon}
                onChange={(event) => setIcon(event.target.value)}
                maxLength={16}
                className={`w-full rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-orange-500 ${inputStyle}`}
              />
            </div>
          </div>

          <div>
            <label htmlFor="edit-habit-start-date" className={`mb-2 block text-sm font-medium ${labelStyle}`}>
              Start date
            </label>
            <input
              id="edit-habit-start-date"
              type="date"
              value={startDate}
              max={getToday()}
              onChange={(event) => setStartDate(event.target.value)}
              className={`w-full rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-orange-500 ${inputStyle}`}
            />
            <p className={`mt-1 text-xs ${isDark ? "text-neutral-500" : "text-neutral-400"}`}>
              The backend will reject a start date later than an existing completion.
            </p>
          </div>

          <fieldset>
            <legend className={`mb-3 text-sm font-medium ${labelStyle}`}>
              Scheduled days *
            </legend>
            <div className="grid grid-cols-4 gap-2 sm:grid-cols-7">
              {weekdays.map((day) => {
                const selected = schedule.includes(day.value);
                return (
                  <button
                    key={day.value}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => toggleDay(day.value)}
                    className={`rounded-lg border px-2 py-2.5 text-sm font-medium transition ${
                      selected
                        ? "border-orange-500 bg-orange-500 text-black"
                        : isDark
                          ? "border-[#404040] text-neutral-300 hover:border-orange-500"
                          : "border-neutral-300 text-neutral-600 hover:border-orange-500"
                    }`}
                  >
                    {day.label}
                  </button>
                );
              })}
            </div>
          </fieldset>

          {error && (
            <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-500">
              {error}
            </p>
          )}

          <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className={`rounded-lg border px-4 py-2.5 text-sm font-medium ${inputStyle}`}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-black hover:bg-orange-400 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save changes"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
