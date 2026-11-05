import { apiRequest } from "./client";
import type { ProgressReport } from "./types";

export function getWeeklyReport(weekStart: string) {
  return apiRequest<ProgressReport>(
    `/api/reports/weekly?week_start=${weekStart}`,
  );
}

export function getMonthlyReport(month: string) {
  return apiRequest<ProgressReport>(
    `/api/reports/monthly?month=${month}`,
  );
}
