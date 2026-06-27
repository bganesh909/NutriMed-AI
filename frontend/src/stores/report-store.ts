import { create } from "zustand";
import type { Report, Biomarker } from "@/types";

interface ReportState {
  reports: Report[];
  currentReport: Report | null;
  biomarkers: Biomarker[];
  setReports: (reports: Report[]) => void;
  setCurrentReport: (report: Report | null) => void;
  setBiomarkers: (biomarkers: Biomarker[]) => void;
}

export const useReportStore = create<ReportState>((set) => ({
  reports: [],
  currentReport: null,
  biomarkers: [],

  setReports: (reports: Report[]) => set({ reports }),
  setCurrentReport: (report: Report | null) => set({ currentReport: report }),
  setBiomarkers: (biomarkers: Biomarker[]) => set({ biomarkers }),
}));
