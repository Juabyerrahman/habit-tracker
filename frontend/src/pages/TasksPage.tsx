
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { apiRequest } from "../api/client";
import type { Task, TaskListResponse } from "../api/types";
import CreateTaskModal from "../features/tasks/CreateTaskModal";
import { useTheme } from "../features/theme/ThemeContext";

interface TaskResponse {
  task: Task;
}

interface ReorderResponse {
  tasks: Task[];
}

function getLocalDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function shiftDate(dateString: string, amount: number) {
  const [year, month, day] = dateString.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  date.setDate(date.getDate() + amount);
  return getLocalDateString(date);
}

function formatDate(dateString: string) {
  const [year, month, day] = dateString.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}


export default function TasksPage() {
  const { isDark } = useTheme();

  const [selectedDate, setSelectedDate] = useState(getLocalDateString());
  const [tasks, setTasks] = useState<Task[]>([]);
  const [completed, setCompleted] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [carryingTask, setCarryingTask] = useState<Task | null>(null);
  const [carryDate, setCarryDate] = useState("");
  const [busyTaskId, setBusyTaskId] = useState<string | null>(null);

  const [editTitle, setEditTitle] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [editDate, setEditDate] = useState("");
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const pageText = isDark ? "text-white" : "text-neutral-900";
  const mutedText = isDark ? "text-neutral-400" : "text-neutral-500";

  const cardStyle = isDark
    ? "border-[#303030] bg-[#191919]"
    : "border-neutral-200 bg-white";

  const inputStyle = isDark
    ? "border-[#404040] bg-[#202020] text-white"
    : "border-neutral-300 bg-white text-neutral-900";

  const secondaryButton = isDark
    ? "border-[#404040] text-neutral-300 hover:bg-[#292929]"
    : "border-neutral-300 text-neutral-700 hover:bg-neutral-100";

  const loadTasks = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiRequest<TaskListResponse>(
        `/api/tasks?date=${selectedDate}`
      );

      setTasks(response.tasks);
      setCompleted(response.completed);
      setTotal(response.total);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load tasks."
      );
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  useEffect(() => {
    void loadTasks();
  }, [loadTasks]);

  async function toggleTask(task: Task) {
    setBusyTaskId(task.id);
    setError(null);

    try {
      await apiRequest<TaskResponse>(`/api/tasks/${task.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          is_completed: !task.is_completed,
        }),
      });

      await loadTasks();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not update task."
      );
    } finally {
      setBusyTaskId(null);
    }
  }

  function openEdit(task: Task) {
    setEditingTask(task);
    setEditTitle(task.title);
    setEditNotes(task.notes);
    setEditDate(task.date);
    setEditError(null);
  }

  async function saveEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!editingTask) return;

    const cleanTitle = editTitle.trim();

    if (!cleanTitle) {
      setEditError("Task title is required.");
      return;
    }

    const updates: Record<string, string> = {};

    if (cleanTitle !== editingTask.title) {
      updates.title = cleanTitle;
    }

    if (editNotes !== editingTask.notes) {
      updates.notes = editNotes;
    }

    if (editDate !== editingTask.date) {
      updates.date = editDate;
    }

    if (Object.keys(updates).length === 0) {
      setEditingTask(null);
      return;
    }

    setEditSaving(true);
    setEditError(null);

    try {
      await apiRequest<TaskResponse>(`/api/tasks/${editingTask.id}`, {
        method: "PATCH",
        body: JSON.stringify(updates),
      });

      setEditingTask(null);
      await loadTasks();
    } catch (err) {
      setEditError(
        err instanceof Error ? err.message : "Could not update task."
      );
    } finally {
      setEditSaving(false);
    }
  }

  async function deleteTask(task: Task) {
    if (!window.confirm(`Delete "${task.title}"?`)) return;

    setBusyTaskId(task.id);
    setError(null);

    try {
      await apiRequest<void>(`/api/tasks/${task.id}`, {
        method: "DELETE",
      });

      await loadTasks();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not delete task."
      );
    } finally {
      setBusyTaskId(null);
    }
  }

  async function moveTask(task: Task, direction: -1 | 1) {
    const index = tasks.findIndex((item) => item.id === task.id);
    const nextIndex = index + direction;

    if (index < 0 || nextIndex < 0 || nextIndex >= tasks.length) return;

    const reordered = [...tasks];
    [reordered[index], reordered[nextIndex]] = [
      reordered[nextIndex],
      reordered[index],
    ];

    setBusyTaskId(task.id);
    setError(null);

    try {
      const response = await apiRequest<ReorderResponse>(
        "/api/tasks/reorder",
        {
          method: "POST",
          body: JSON.stringify({
            date: selectedDate,
            ordered_ids: reordered.map((item) => item.id),
          }),
        }
      );

      setTasks(response.tasks);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not reorder tasks."
      );
    } finally {
      setBusyTaskId(null);
    }
  }

  function openCarryForward(task: Task) {
    setCarryingTask(task);
    setCarryDate(shiftDate(selectedDate, 1));
  }

  async function confirmCarryForward(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!carryingTask) return;

    if (!carryDate || carryDate === carryingTask.date) {
      setError("Choose a different date.");
      return;
    }

    setBusyTaskId(carryingTask.id);
    setError(null);

    try {
      await apiRequest<TaskResponse>(
        `/api/tasks/${carryingTask.id}/carry-forward`,
        {
          method: "POST",
          body: JSON.stringify({ date: carryDate }),
        }
      );

      setCarryingTask(null);
      await loadTasks();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not carry task forward."
      );
    } finally {
      setBusyTaskId(null);
    }
  }

  const isToday = selectedDate === getLocalDateString();
  const completionRate =
    total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div className={`mx-auto w-full max-w-7xl space-y-7 ${pageText}`}>
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Daily Tasks</h1>
          <p className={`mt-1 text-sm ${mutedText}`}>
            Plan your day, finish important work, and stay consistent.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowCreateModal(true)}
          className="rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-black transition hover:bg-orange-400"
        >
          + Add task
        </button>
      </header>

      <section className={`rounded-xl border p-5 ${cardStyle}`}>
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className={`text-xs font-medium uppercase tracking-wider ${mutedText}`}>
              Selected date
            </p>
            <h2 className="mt-1 text-lg font-semibold">
              {formatDate(selectedDate)}
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setSelectedDate(shiftDate(selectedDate, -1))}
              className={`rounded-lg border px-3 py-2 text-sm ${secondaryButton}`}
            >
              ← Previous
            </button>

            <button
              type="button"
              onClick={() => setSelectedDate(getLocalDateString())}
              disabled={isToday}
              className={`rounded-lg border px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-40 ${secondaryButton}`}
            >
              Today
            </button>

            <button
              type="button"
              onClick={() => setSelectedDate(shiftDate(selectedDate, 1))}
              className={`rounded-lg border px-3 py-2 text-sm ${secondaryButton}`}
            >
              Next →
            </button>
          </div>
        </div>

        <div className="mt-4">
          <label htmlFor="tasks-date" className={`mb-2 block text-xs ${mutedText}`}>
            Jump to date
          </label>
          <input
            id="tasks-date"
            type="date"
            value={selectedDate}
            onChange={(event) => setSelectedDate(event.target.value)}
            className={`rounded-lg border px-3 py-2 text-sm ${inputStyle}`}
          />
        </div>
      </section>

      <section className={`rounded-xl border p-5 ${cardStyle}`}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className={`text-sm ${mutedText}`}>Daily completion</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">
              {completed} <span className={`text-base font-normal ${mutedText}`}>/ {total} tasks</span>
            </p>
          </div>

          <p className="text-2xl font-bold tabular-nums text-orange-500">
            {completionRate}%
          </p>
        </div>

        <div className={`mt-4 h-2 overflow-hidden rounded-full ${isDark ? "bg-[#303030]" : "bg-neutral-100"}`}>
          <div
            className="h-full rounded-full bg-orange-500 transition-all"
            style={{ width: `${completionRate}%` }}
          />
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
            onClick={() => void loadTasks()}
            className="ml-3 font-semibold underline"
          >
            Retry
          </button>
        </div>
      )}

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Your tasks</h2>
            <p className={`mt-1 text-xs ${mutedText}`}>
              Use the arrows to change task order.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadTasks()}
            className={`text-sm ${mutedText} hover:text-orange-500`}
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <div className={`py-14 text-center text-sm ${mutedText}`}>
            Loading tasks...
          </div>
        ) : tasks.length === 0 ? (
          <div className={`rounded-xl border px-5 py-14 text-center ${cardStyle}`}>
            <div className="text-3xl">☑</div>
            <h3 className="mt-3 font-semibold">Nothing planned for this day</h3>
            <p className={`mt-2 text-sm ${mutedText}`}>
              Add a task and give your day some direction.
            </p>
            <button
              type="button"
              onClick={() => setShowCreateModal(true)}
              className="mt-5 rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-black hover:bg-orange-400"
            >
              Add your first task
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((task, index) => {
              const isBusy = busyTaskId === task.id;

              return (
                <article
                  key={task.id}
                  className={`rounded-xl border p-4 transition ${cardStyle} ${
                    task.is_completed ? "opacity-70" : ""
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <button
                      type="button"
                      aria-label={task.is_completed ? "Mark incomplete" : "Mark complete"}
                      aria-pressed={task.is_completed}
                      disabled={isBusy}
                      onClick={() => void toggleTask(task)}
                      className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border text-sm transition ${
                        task.is_completed
                          ? "border-orange-500 bg-orange-500 text-black"
                          : isDark
                            ? "border-neutral-600 hover:border-orange-500"
                            : "border-neutral-300 hover:border-orange-500"
                      }`}
                    >
                      {task.is_completed ? "✓" : ""}
                    </button>

                    <div className="min-w-0 flex-1">
                      <h3 className={`break-words font-medium ${
                        task.is_completed ? "text-neutral-500 line-through" : ""
                      }`}>
                        {task.title}
                      </h3>

                      {task.notes && (
                        <p className={`mt-1 whitespace-pre-wrap break-words text-sm ${mutedText}`}>
                          {task.notes}
                        </p>
                      )}

                      {task.carried_from_task_id && (
                        <p className="mt-2 text-xs text-orange-500">
                          Carried forward from an earlier date
                        </p>
                      )}

                      {task.completed_at && task.is_completed && (
                        <p className={`mt-2 text-xs ${mutedText}`}>
                          Completed
                        </p>
                      )}

                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <button
                          type="button"
                          disabled={isBusy}
                          onClick={() => openEdit(task)}
                          className={`rounded-md border px-3 py-1.5 text-xs font-medium ${secondaryButton}`}
                        >
                          Edit
                        </button>

                        {!task.is_completed && (
                          <button
                            type="button"
                            disabled={isBusy}
                            onClick={() => openCarryForward(task)}
                            className={`rounded-md border px-3 py-1.5 text-xs font-medium ${secondaryButton}`}
                          >
                            Carry forward
                          </button>
                        )}

                        <button
                          type="button"
                          disabled={isBusy}
                          onClick={() => void deleteTask(task)}
                          className="rounded-md border border-red-500/30 px-3 py-1.5 text-xs font-medium text-red-500 hover:bg-red-500/10"
                        >
                          Delete
                        </button>
                      </div>
                    </div>

                    <div className="flex shrink-0 flex-col gap-1">
                      <button
                        type="button"
                        aria-label="Move task up"
                        title="Move up"
                        disabled={index === 0 || isBusy || task.is_completed}
                        onClick={() => void moveTask(task, -1)}
                        className={`rounded-md border px-2 py-1 text-xs ${secondaryButton} disabled:opacity-30`}
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        aria-label="Move task down"
                        title="Move down"
                        disabled={index === tasks.length - 1 || isBusy || task.is_completed}
                        onClick={() => void moveTask(task, 1)}
                        className={`rounded-md border px-2 py-1 text-xs ${secondaryButton} disabled:opacity-30`}
                      >
                        ↓
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {showCreateModal && (
        <CreateTaskModal
          initialDate={selectedDate}
          onClose={() => setShowCreateModal(false)}
          onCreated={() => void loadTasks()}
        />
      )}

      {editingTask && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-black/60 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !editSaving) {
              setEditingTask(null);
            }
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-task-title"
            className={`my-auto w-full max-w-lg rounded-2xl border p-6 shadow-2xl ${cardStyle}`}
          >
            <h2 id="edit-task-title" className="text-xl font-bold">
              Edit task
            </h2>

            <form onSubmit={saveEdit} className="mt-5 space-y-4">
              <div>
                <label htmlFor="edit-task-title-input" className={`mb-2 block text-sm ${mutedText}`}>
                  Task title
                </label>
                <input
                  id="edit-task-title-input"
                  value={editTitle}
                  onChange={(event) => setEditTitle(event.target.value)}
                  maxLength={200}
                  required
                  className={`w-full rounded-lg border px-3 py-2.5 text-sm ${inputStyle}`}
                />
              </div>

              <div>
                <label htmlFor="edit-task-notes" className={`mb-2 block text-sm ${mutedText}`}>
                  Notes
                </label>
                <textarea
                  id="edit-task-notes"
                  value={editNotes}
                  onChange={(event) => setEditNotes(event.target.value)}
                  maxLength={1000}
                  rows={4}
                  className={`w-full rounded-lg border px-3 py-2.5 text-sm ${inputStyle}`}
                />
              </div>

              <div>
                <label htmlFor="edit-task-date" className={`mb-2 block text-sm ${mutedText}`}>
                  Task date
                </label>
                <input
                  id="edit-task-date"
                  type="date"
                  value={editDate}
                  onChange={(event) => setEditDate(event.target.value)}
                  required
                  className={`w-full rounded-lg border px-3 py-2.5 text-sm ${inputStyle}`}
                />
              </div>

              {editError && (
                <p role="alert" className="rounded-lg bg-red-500/10 p-3 text-sm text-red-500">
                  {editError}
                </p>
              )}

              <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  disabled={editSaving}
                  onClick={() => setEditingTask(null)}
                  className={`rounded-lg border px-4 py-2.5 text-sm ${secondaryButton}`}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editSaving}
                  className="rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-black hover:bg-orange-400 disabled:opacity-50"
                >
                  {editSaving ? "Saving..." : "Save changes"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {carryingTask && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !busyTaskId) {
              setCarryingTask(null);
            }
          }}
        >
          <section className={`w-full max-w-md rounded-2xl border p-6 shadow-2xl ${cardStyle}`}>
            <h2 className="text-xl font-bold">Carry task forward</h2>
            <p className={`mt-2 text-sm ${mutedText}`}>
              Create a copy of "{carryingTask.title}" on another date. The original task will remain unchanged.
            </p>

            <form onSubmit={confirmCarryForward} className="mt-5 space-y-4">
              <div>
                <label htmlFor="carry-date" className={`mb-2 block text-sm ${mutedText}`}>
                  New task date
                </label>
                <input
                  id="carry-date"
                  type="date"
                  value={carryDate}
                  min={shiftDate(carryingTask.date, 1)}
                  onChange={(event) => setCarryDate(event.target.value)}
                  required
                  className={`w-full rounded-lg border px-3 py-2.5 text-sm ${inputStyle}`}
                />
              </div>

              <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  disabled={busyTaskId !== null}
                  onClick={() => setCarryingTask(null)}
                  className={`rounded-lg border px-4 py-2.5 text-sm ${secondaryButton}`}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={busyTaskId !== null}
                  className="rounded-lg bg-orange-500 px-5 py-2.5 text-sm font-semibold text-black hover:bg-orange-400 disabled:opacity-50"
                >
                  Carry forward
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
