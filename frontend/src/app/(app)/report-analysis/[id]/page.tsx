"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { BiomarkerCard } from "@/components/biomarker-card";
import { RiskBadge } from "@/components/risk-badge";
import { BiomarkerChart } from "@/components/charts/biomarker-chart";
import { useReport, useAnalyzeReport } from "@/hooks/use-reports";
import {
  BiomarkerCardSkeleton,
  ChartSkeleton,
} from "@/components/loading-skeleton";
import {
  FileText,
  Calendar,
  AlertTriangle,
  ShieldAlert,
  Loader2,
  UtensilsCrossed,
  Dumbbell,
} from "lucide-react";
import { format } from "date-fns";
import type { Biomarker } from "@/types";

const mockBiomarkers: Biomarker[] = [
  { id: "1", report_id: "1", name: "Hemoglobin", value: 14.2, unit: "g/dL", reference_min: 12, reference_max: 17, status: "Normal", category: "Blood" },
  { id: "2", report_id: "1", name: "Vitamin D", value: 18, unit: "ng/mL", reference_min: 30, reference_max: 100, status: "Low", category: "Vitamins" },
  { id: "3", report_id: "1", name: "Blood Sugar (Fasting)", value: 110, unit: "mg/dL", reference_min: 70, reference_max: 100, status: "High", category: "Metabolic" },
  { id: "4", report_id: "1", name: "Total Cholesterol", value: 210, unit: "mg/dL", reference_min: 0, reference_max: 200, status: "High", category: "Lipids" },
  { id: "5", report_id: "1", name: "Iron", value: 80, unit: "ug/dL", reference_min: 60, reference_max: 170, status: "Normal", category: "Minerals" },
  { id: "6", report_id: "1", name: "Vitamin B12", value: 450, unit: "pg/mL", reference_min: 200, reference_max: 900, status: "Normal", category: "Vitamins" },
  { id: "7", report_id: "1", name: "TSH", value: 2.5, unit: "mIU/L", reference_min: 0.4, reference_max: 4.0, status: "Normal", category: "Thyroid" },
  { id: "8", report_id: "1", name: "Creatinine", value: 1.1, unit: "mg/dL", reference_min: 0.6, reference_max: 1.2, status: "Normal", category: "Kidney" },
];

const mockRiskFactors = [
  { name: "Pre-diabetic risk", level: "medium", description: "Fasting blood sugar is slightly elevated at 110 mg/dL." },
  { name: "Cardiovascular risk", level: "medium", description: "Total cholesterol is above the recommended 200 mg/dL threshold." },
  { name: "Vitamin D deficiency", level: "high", description: "Vitamin D at 18 ng/mL is well below the recommended 30 ng/mL minimum." },
];

const mockDeficiencies = [
  { nutrient: "Vitamin D", current: "18 ng/mL", recommended: "30-100 ng/mL", suggestion: "Consider supplementation with 2000-4000 IU daily." },
];

export default function ReportAnalysisPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const { data, isLoading } = useReport(id);
  const analyzeMutation = useAnalyzeReport();

  const report = data?.report;
  const biomarkers = data?.biomarkers || mockBiomarkers;

  const abnormalCount = biomarkers.filter((b) => b.status !== "Normal").length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-50">Report Analysis</h2>
          <p className="text-slate-400 mt-1">
            Detailed analysis of your medical report.
          </p>
        </div>
        {report && report.status !== "analyzed" && (
          <Button
            className="bg-blue-600 hover:bg-blue-700 text-white"
            onClick={() => analyzeMutation.mutate(id)}
            disabled={analyzeMutation.isPending}
          >
            {analyzeMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              "Analyze Report"
            )}
          </Button>
        )}
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-5">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="p-3 rounded-lg bg-blue-600/10">
              <FileText className="h-6 w-6 text-blue-500" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-slate-200">
                {report?.file_name || "Medical Report"}
              </h3>
              <div className="flex flex-wrap gap-4 mt-1 text-sm text-slate-400">
                <span className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" />
                  {report
                    ? format(new Date(report.uploaded_at), "MMMM dd, yyyy")
                    : "Recent"}
                </span>
                <span>{report?.report_type || "General Health Checkup"}</span>
              </div>
            </div>
            <Badge
              variant="outline"
              className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
            >
              {report?.status || "analyzed"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          <>
            <BiomarkerCardSkeleton />
            <BiomarkerCardSkeleton />
            <BiomarkerCardSkeleton />
            <BiomarkerCardSkeleton />
          </>
        ) : (
          biomarkers.map((biomarker) => (
            <BiomarkerCard key={biomarker.id} biomarker={biomarker} />
          ))
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-200 flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-amber-500" />
              Risk Factors
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {mockRiskFactors.map((risk, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50"
              >
                <AlertTriangle
                  className={`h-5 w-5 mt-0.5 flex-shrink-0 ${
                    risk.level === "high"
                      ? "text-red-400"
                      : risk.level === "medium"
                        ? "text-amber-400"
                        : "text-emerald-400"
                  }`}
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-slate-200">
                      {risk.name}
                    </span>
                    <RiskBadge level={risk.level} />
                  </div>
                  <p className="text-xs text-slate-400">{risk.description}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-200">Deficiencies</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {mockDeficiencies.map((def, index) => (
              <div
                key={index}
                className="p-3 rounded-lg bg-slate-800/50 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-200">
                    {def.nutrient}
                  </span>
                  <RiskBadge level="high" label="Deficient" />
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-slate-500">Current: </span>
                    <span className="text-red-400">{def.current}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Recommended: </span>
                    <span className="text-emerald-400">{def.recommended}</span>
                  </div>
                </div>
                <p className="text-xs text-slate-400">{def.suggestion}</p>
              </div>
            ))}

            {abnormalCount === 0 && (
              <p className="text-sm text-slate-400 text-center py-4">
                No significant deficiencies detected.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Biomarker Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <ChartSkeleton />
          ) : (
            <BiomarkerChart biomarkers={biomarkers} />
          )}
        </CardContent>
      </Card>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Interpretation Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-slate-300 leading-relaxed">
            Your overall health profile shows mostly normal values with a few areas of concern.
            Hemoglobin, Iron, B12, TSH, and Creatinine are all within normal reference ranges,
            indicating good blood health, thyroid function, and kidney function.
          </p>
          <p className="text-sm text-slate-300 leading-relaxed">
            However, there are two key areas requiring attention: Vitamin D levels are significantly
            low at 18 ng/mL (minimum recommended is 30 ng/mL), which may affect bone health,
            immunity, and energy levels. Fasting blood sugar at 110 mg/dL and total cholesterol
            at 210 mg/dL are slightly elevated, suggesting early metabolic risk that can be
            addressed through dietary changes and regular exercise.
          </p>

          <Separator className="bg-slate-800 my-4" />

          <div className="flex flex-wrap gap-3">
            <Button
              className="bg-blue-600 hover:bg-blue-700 text-white"
              onClick={() => router.push("/diet-plan")}
            >
              <UtensilsCrossed className="mr-2 h-4 w-4" />
              Get Diet Plan
            </Button>
            <Button
              variant="outline"
              className="border-slate-700 text-slate-300 hover:bg-slate-800"
              onClick={() => router.push("/workout-plan")}
            >
              <Dumbbell className="mr-2 h-4 w-4" />
              Get Workout Plan
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
