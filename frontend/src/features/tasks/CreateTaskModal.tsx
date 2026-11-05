
import { useState, type FormEvent } from "react";
import { apiRequest } from "../../api/client";
import type { CreateTaskResponse } from "../../api/types";
import { useTheme } from "../theme/ThemeContext";

interface CreateTaskModalProps {
  onClose: () => void;
  onCreated: () => void;
  initialDate?: string;
}

function getLocalDateString(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

export default function CreateTaskModal({
  onClose,
  onCreated,
  initialDate,
}: CreateTaskModalProps) {
  const { isDark } = useTheme();

  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [date, setDate] = useState(initialDate || getLocalDateString());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inputStyle = isDark
    ? "border-[#404040] bg-[#202020] text-white placeholder:text-neutral-500"
    : "border-neutral-300 bg-white text-neutral-900 placeholder:text-neutral-400";

  const labelStyle = isDark ? "text-neutral-300" : "text-neutral-700";

  const panelStyle = isDark
    ? "border-[#383838] bg-[#1b1b1b] text-white"
    : "border-neutral-200 bg-white text-neutral-900";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const cleanTitle = title.trim();

    if (!cleanTitle) {
      setError("Task title is required.");
      return;
    }

    if (!date) {
      setError("Please select a task date.");
      return;
    }

    setSaving(true);

    try {
      await apiRequest<CreateTaskResponse>("/api/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: cleanTitle,
          notes: notes.trim(),
          date,
        }),
      });

      onCreated();
      onClose();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not create the task. Please try again."
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
        aria-labelledby="create-task-title"
        className={`my-auto w-full max-w-lg rounded-2xl border p-6 shadow-2xl ${panelStyle}`}
      >
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 id="create-task-title" className="text-xl font-bold">
              Create a task
            </h2>
            <p
              className={`mt-1 text-sm ${
                isDark ? "text-neutral-400" : "text-neutral-500"
              }`}
            >
              Add something you want to get done.
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
            <label
              htmlFor="task-title"
              className={`mb-2 block text-sm font-medium ${labelStyle}`}
            >
              Task title *
            </label>

            <input
              id="task-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              maxLength={200}
              required
              autoFocus
              placeholder="e.g. Complete Python assignment"
              className={`w-full rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-orange-500 ${inputStyle}`}
            />

            <p
              className={`mt-1 text-right text-xs ${
                isDark ? "text-neutral-500" : "text-neutral-400"
              }`}
            >
              {title.length}/200
            </p>
          </div>

          <div>
            <label
              htmlFor="task-notes"
              className={`mb-2 block text-sm font-medium ${labelStyle}`}
            >
              Notes
            </label>

            <textarea
              id="task-notes"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              maxLength={1000}
              rows={4}
              placeholder="Add extra details (optional)..."
              className={`w-full resize-y rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-orange-500 ${inputStyle}`}
            />

            <p
              className={`mt-1 text-right text-xs ${
                isDark ? "text-neutral-500" : "text-neutral-400"
              }`}
            >
              {notes.length}/1000
            </p>
          </div>

          <div>
            <label
              htmlFor="task-date"
              className={`mb-2 block text-sm font-medium ${labelStyle}`}
            >
              Task date *
            </label>

            <input
              id="task-date"
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              required
              className={`w-full rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-orange-500 ${inputStyle}`}
            />
          </div>

          {error && (
            <p
              role="alert"
              className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-500"
            >
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
              {saving ? "Creating..." : "Create task"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
