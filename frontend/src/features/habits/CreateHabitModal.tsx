
import { useState, type FormEvent } from "react";
import { apiRequest } from "../../api/client";
import { useTheme } from "../theme/ThemeContext";

interface CreateHabitModalProps {
  onClose: () => void;
  onCreated: () => void;
}

interface CreateHabitResponse {
  habit: {
    id: string;
    name: string;
  };
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

function getLocalDateString(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

export default function CreateHabitModal({
  onClose,
  onCreated,
}: CreateHabitModalProps) {
  const { isDark } = useTheme();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [icon, setIcon] = useState("");
  const [startDate, setStartDate] = useState(getLocalDateString());
  const [schedule, setSchedule] = useState<number[]>([0, 1, 2, 3, 4, 5, 6]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inputStyle = isDark
    ? "border-[#404040] bg-[#202020] text-white placeholder:text-neutral-500"
    : "border-neutral-300 bg-white text-neutral-900 placeholder:text-neutral-400";

  const labelStyle = isDark ? "text-neutral-300" : "text-neutral-700";

  const panelStyle = isDark
    ? "border-[#383838] bg-[#1b1b1b] text-white"
    : "border-neutral-200 bg-white text-neutral-900";

  function toggleWeekday(day: number) {
    setSchedule((current) =>
      current.includes(day)
        ? current.filter((value) => value !== day)
        : [...current, day].sort((a, b) => a - b)
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const cleanName = name.trim();

    if (!cleanName) {
      setError("Habit name is required.");
      return;
    }

    if (schedule.length === 0) {
      setError("Select at least one scheduled day.");
      return;
    }

    setSaving(true);

    try {
      await apiRequest<CreateHabitResponse>("/api/habits", {
        method: "POST",
        body: JSON.stringify({
          name: cleanName,
          description: description.trim(),
          category: category.trim() || null,
          icon: icon.trim() || null,
          start_date: startDate || null,
          schedule,
        }),
      });

      onCreated();
      onClose();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not create the habit. Please try again."
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
        aria-labelledby="create-habit-title"
        className={`my-auto w-full max-w-xl rounded-2xl border p-6 shadow-2xl ${panelStyle}`}
      >
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 id="create-habit-title" className="text-xl font-bold">
              Create a habit
            </h2>
            <p className={`mt-1 text-sm ${isDark ? "text-neutral-400" : "text-neutral-500"}`}>
              Set a habit and choose the days you want to follow it.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            aria-label="Close"
            className="rounded-lg px-3 py-1 text-xl text-neutral-500 hover:bg-neutral-500/10 disabled:opacity-50"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="habit-name" className={`mb-2 block text-sm font-medium ${labelStyle}`}>
              Habit name *
            </label>
            <input
              id="habit-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={100}
              required
              autoFocus
              placeholder="e.g. Read for 30 minutes"
              className={`w-full rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-orange-500 ${inputStyle}`}
            />
            <p className={`mt-1 text-right text-xs ${isDark ? "text-neutral-500" : "text-neutral-400"}`}>
              {name.length}/100
            </p>
          </div>

          <div>
            <label htmlFor="habit-description" className={`mb-2 block text-sm font-medium ${labelStyle}`}>
              Description
            </label>
            <textarea
              id="habit-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={500}
              rows={2}
              placeholder="Why is this habit important to you?"
              className={`w-full resize-y rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-orange-500 ${inputStyle}`}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="habit-category" className={`mb-2 block text-sm font-medium ${labelStyle}`}>
                Category
              </label>
              <input
                id="habit-category"
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                maxLength={50}
                placeholder="e.g. Health, Study"
                className={`w-full rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-orange-500 ${inputStyle}`}
              />
            </div>

            <div>
              <label htmlFor="habit-icon" className={`mb-2 block text-sm font-medium ${labelStyle}`}>
                Icon (optional)
              </label>
              <input
                id="habit-icon"
                value={icon}
                onChange={(event) => setIcon(event.target.value)}
                maxLength={16}
                placeholder="e.g. 📚"
                className={`w-full rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-orange-500 ${inputStyle}`}
              />
            </div>
          </div>

          <div>
            <label htmlFor="habit-start-date" className={`mb-2 block text-sm font-medium ${labelStyle}`}>
              Start date
            </label>
            <input
              id="habit-start-date"
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              max={getLocalDateString()}
              className={`w-full rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-orange-500 ${inputStyle}`}
            />
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
                    onClick={() => toggleWeekday(day.value)}
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
              className={`rounded-lg border px-4 py-2.5 text-sm font-medium disabled:opacity-50 ${inputStyle}`}
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-black transition hover:bg-orange-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? "Creating..." : "Create habit"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
