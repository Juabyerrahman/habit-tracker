
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ReportsPage from "./ReportsPage";
import { getMonthlyReport, getWeeklyReport } from "../api/reports";

vi.mock("../api/reports", () => ({
  getWeeklyReport: vi.fn(),
  getMonthlyReport: vi.fn(),
}));

vi.mock("../features/theme/ThemeContext", () => ({
  useTheme: () => ({ isDark: false }),
}));

const mockReport = {
  period: {
    start: "2026-11-02",
    end: "2026-11-08",
    through: "2026-11-05",
  },
  overview: {
    habit_scheduled: 20,
    habit_completed: 15,
    habit_missed: 3,
    habit_pending: 2,
    habit_completion_rate: 75,
    task_total: 10,
    task_completed: 8,
    task_pending: 2,
    task_carried_forward: 1,
    task_completion_rate: 80,
    overall_total: 30,
    overall_completed: 23,
    overall_completion_rate: 77,
  },
  habits: [
    {
      habit_id: "habit-1",
      habit_name: "Reading",
      scheduled_days: 7,
      completed_days: 6,
      missed_days: 1,
      pending_days: 0,
      completion_rate: 86,
    },
  ],
  strongest_habits: [
    {
      habit_id: "habit-1",
      habit_name: "Reading",
      scheduled_days: 7,
      completed_days: 6,
      missed_days: 1,
      pending_days: 0,
      completion_rate: 86,
    },
  ],
  weakest_habits: [],
  daily_trends: [
    {
      date: "2026-11-02",
      habits_scheduled: 3,
      habits_completed: 3,
      tasks_total: 2,
      tasks_completed: 2,
      overall_total: 5,
      overall_completed: 5,
      overall_completion_rate: 100,
    },
  ],
  best_day: null,
  worst_day: null,
};

describe("ReportsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads and displays the weekly report", async () => {
    vi.mocked(getWeeklyReport).mockResolvedValue(mockReport);

    render(<ReportsPage />);

    expect(
      await screen.findByText("Progress Reports"),
    ).toBeInTheDocument();

    expect(
      await screen.findByText("Overall completion"),
    ).toBeInTheDocument();

    expect(screen.getByText("77%")).toBeInTheDocument();
    expect(screen.getAllByText("Reading")).toHaveLength(2);

    expect(getWeeklyReport).toHaveBeenCalled();
  });

  it("loads the monthly report when Monthly is selected", async () => {
    vi.mocked(getWeeklyReport).mockResolvedValue(mockReport);
    vi.mocked(getMonthlyReport).mockResolvedValue({
      ...mockReport,
      period: {
        start: "2026-11-01",
        end: "2026-11-30",
        through: "2026-11-05",
      },
    });

    render(<ReportsPage />);

    await screen.findByText("Overall completion");

    fireEvent.click(screen.getByRole("button", { name: "monthly" }));

    await waitFor(() => {
      expect(getMonthlyReport).toHaveBeenCalledWith("2026-11");
    });

    expect(screen.getByText("November 2026")).toBeInTheDocument();
  });

  it("displays an error and allows retrying", async () => {
    vi.mocked(getWeeklyReport)
      .mockRejectedValueOnce(new Error("Unable to load report"))
      .mockResolvedValueOnce(mockReport);

    render(<ReportsPage />);

    expect(
      await screen.findByText("Unable to load report"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(
      await screen.findByText("Overall completion"),
    ).toBeInTheDocument();

    expect(getWeeklyReport).toHaveBeenCalledTimes(2);
  });
});
