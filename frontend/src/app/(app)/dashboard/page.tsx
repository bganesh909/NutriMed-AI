"use client";

import { useRouter } from "next/navigation";
import { Activity, Droplets, Sun, ShieldAlert, Upload, UtensilsCrossed, Dumbbell } from "lucide-react";
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
import { useReports } from "@/hooks/use-reports";
import { StatsCardSkeleton, ChartSkeleton, TableSkeleton } from "@/components/loading-skeleton";
import { format } from "date-fns";
import type { Biomarker } from "@/types";

const mockBiomarkers: Biomarker[] = [
  { id: "1", report_id: "1", name: "Hemoglobin", value: 14.2, unit: "g/dL", reference_min: 12, reference_max: 17, status: "Normal", category: "Blood" },
  { id: "2", report_id: "1", name: "Vitamin D", value: 18, unit: "ng/mL", reference_min: 30, reference_max: 100, status: "Low", category: "Vitamins" },
  { id: "3", report_id: "1", name: "Blood Sugar", value: 110, unit: "mg/dL", reference_min: 70, reference_max: 100, status: "High", category: "Metabolic" },
  { id: "4", report_id: "1", name: "Cholesterol", value: 210, unit: "mg/dL", reference_min: 0, reference_max: 200, status: "High", category: "Lipids" },
  { id: "5", report_id: "1", name: "Iron", value: 80, unit: "ug/dL", reference_min: 60, reference_max: 170, status: "Normal", category: "Minerals" },
  { id: "6", report_id: "1", name: "B12", value: 450, unit: "pg/mL", reference_min: 200, reference_max: 900, status: "Normal", category: "Vitamins" },
];

const statusBadgeClass: Record<string, string> = {
  uploaded: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  processing: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  analyzed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  error: "bg-red-500/10 text-red-400 border-red-500/20",
};

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { data: reports, isLoading } = useReports();
  const router = useRouter();

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
        {isLoading ? (
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
              value={user ? (user.weight / ((user.height / 100) ** 2)).toFixed(1) : "--"}
              subtitle="Body Mass Index"
              iconColor="text-blue-500"
            />
            <StatsCard
              icon={Droplets}
              label="Hemoglobin"
              value="14.2 g/dL"
              subtitle="Normal range"
              iconColor="text-emerald-500"
            />
            <StatsCard
              icon={Sun}
              label="Vitamin D"
              value="18 ng/mL"
              subtitle="Below optimal"
              iconColor="text-amber-500"
            />
            <StatsCard
              icon={ShieldAlert}
              label="Risk Score"
              value="Low"
              subtitle="Based on latest report"
              iconColor="text-emerald-500"
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
            {isLoading ? (
              <ChartSkeleton />
            ) : (
              <BiomarkerChart biomarkers={mockBiomarkers} />
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
                      {report.file_name}
                    </TableCell>
                    <TableCell className="text-slate-300">
                      {report.report_type}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={statusBadgeClass[report.status]}
                      >
                        {report.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-slate-400">
                      {format(new Date(report.uploaded_at), "MMM dd, yyyy")}
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
