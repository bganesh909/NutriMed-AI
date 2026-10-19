"use client";

import { useRouter } from "next/navigation";
import { Activity, Droplets, Sun, ShieldAlert, Sparkles, Upload, UtensilsCrossed, Dumbbell } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { StatsCard } from "@/components/stats-card";
import { BiomarkerChart } from "@/components/charts/biomarker-chart";
import { useAuthStore } from "@/stores/auth-store";
import { useReports, useReportAnalysis } from "@/hooks/use-reports";
import { StatsCardSkeleton, ChartSkeleton, TableSkeleton } from "@/components/loading-skeleton";
import { toBiomarkers, markerLabel } from "@/lib/biomarkers";
import { formatApiDate } from "@/lib/dates";
import { reportStatusMeta } from "@/lib/report-status";


export default function DashboardPage() {
  const { user } = useAuthStore();
  const { data: reports, isLoading } = useReports();
  const router = useRouter();

  // Dashboard figures come from the most recent fully-analysed report.
  const latestAnalysed = reports?.find((r) => r.status === "completed");
  const { data: analysis, isLoading: analysisLoading } = useReportAnalysis(
    latestAnalysed?.id ?? ""
  );

  const biomarkers = toBiomarkers(analysis?.biomarkers);
  const details = analysis?.biomarkers ?? null;
  const abnormal = biomarkers.filter((b) => b.status !== "Normal");
  const loadingStats = isLoading || analysisLoading;

  const bmi =
    user?.weight && user?.height
      ? (user.weight / (user.height / 100) ** 2).toFixed(1)
      : "--";

  /** Format one marker for a stat tile, or a placeholder when absent. */
  const stat = (key: string) => {
    const d = details?.[key];
    if (!d || typeof d.value !== "number") {
      return { value: "--", subtitle: "No report data", color: "text-slate-500" };
    }
    const unit = d.unit && d.unit !== "unknown" ? ` ${d.unit}` : "";
    const subtitle =
      d.status === "normal"
        ? "Normal range"
        : d.status === "low"
          ? "Below range"
          : d.status === "high"
            ? "Above range"
            : "Not classified";
    const color =
      d.status === "normal"
        ? "text-emerald-500"
        : d.status === "unknown"
          ? "text-slate-500"
          : "text-amber-500";
    return { value: `${d.value}${unit}`, subtitle, color };
  };

  const hb = stat("hemoglobin");
  const vitD = stat("vitamin_d");
  const riskLabel = !latestAnalysed
    ? "--"
    : abnormal.length === 0
      ? "Low"
      : abnormal.length <= 2
        ? "Moderate"
        : "High";

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-50">
          Welcome back, {user?.name?.split(" ")[0] || "User"}
        </h2>
        <p className="text-slate-400 mt-1">
          Here is an overview of your health metrics and recent activity.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {loadingStats ? (
          <>
            <StatsCardSkeleton />
            <StatsCardSkeleton />
            <StatsCardSkeleton />
            <StatsCardSkeleton />
          </>
        ) : (
          <>
            <StatsCard
              icon={Activity}
              label="BMI"
              value={bmi}
              subtitle="Body Mass Index"
              iconColor="text-blue-500"
            />
            <StatsCard
              icon={Droplets}
              label={markerLabel("hemoglobin")}
              value={hb.value}
              subtitle={hb.subtitle}
              iconColor={hb.color}
            />
            <StatsCard
              icon={Sun}
              label={markerLabel("vitamin_d")}
              value={vitD.value}
              subtitle={vitD.subtitle}
              iconColor={vitD.color}
            />
            <StatsCard
              icon={ShieldAlert}
              label="Risk Score"
              value={riskLabel}
              subtitle={
                latestAnalysed
                  ? `${abnormal.length} marker(s) out of range`
                  : "No analysed report yet"
              }
              iconColor={
                abnormal.length === 0 ? "text-emerald-500" : "text-amber-500"
              }
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-200">Biomarker Overview</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingStats ? (
              <ChartSkeleton />
            ) : biomarkers.length === 0 ? (
              <p className="text-sm text-slate-400 py-8 text-center">
                Upload and analyse a report to see your biomarkers here.
              </p>
            ) : (
              <BiomarkerChart biomarkers={biomarkers} />
            )}
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-200">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              className="w-full justify-start gap-3 bg-blue-600 hover:bg-blue-700 text-white"
              onClick={() => router.push("/upload-report")}
            >
              <Upload className="h-4 w-4" />
              Upload New Report
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start gap-3 border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-slate-100"
              onClick={() => router.push("/suggestions")}
            >
              <Sparkles className="h-4 w-4" />
              Get Suggestions
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start gap-3 border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-slate-100"
              onClick={() => router.push("/diet-plan")}
            >
              <UtensilsCrossed className="h-4 w-4" />
              Generate Diet Plan
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start gap-3 border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-slate-100"
              onClick={() => router.push("/workout-plan")}
            >
              <Dumbbell className="h-4 w-4" />
              Generate Workout Plan
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Recent Reports</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton rows={3} />
          ) : reports && reports.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800 hover:bg-transparent">
                  <TableHead className="text-slate-400">File Name</TableHead>
                  <TableHead className="text-slate-400">Type</TableHead>
                  <TableHead className="text-slate-400">Status</TableHead>
                  <TableHead className="text-slate-400">Uploaded</TableHead>
                  <TableHead className="text-slate-400 text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.slice(0, 5).map((report) => (
                  <TableRow
                    key={report.id}
                    className="border-slate-800 hover:bg-slate-800/50"
                  >
                    <TableCell className="font-medium text-slate-200">
                      {report.original_filename}
                    </TableCell>
                    <TableCell className="text-slate-300">
                      {report.report_type}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={reportStatusMeta(report.status).badgeClass}
                      >
                        {reportStatusMeta(report.status).label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-slate-400">
                      {formatApiDate(report.uploaded_at, "MMM dd, yyyy")}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-blue-400 hover:text-blue-300"
                        onClick={() =>
                          router.push(`/report-analysis/${report.id}`)
                        }
                      >
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8">
              <p className="text-slate-400 mb-4">No reports uploaded yet.</p>
              <Button
                className="bg-blue-600 hover:bg-blue-700"
                onClick={() => router.push("/upload-report")}
              >
                Upload Your First Report
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
