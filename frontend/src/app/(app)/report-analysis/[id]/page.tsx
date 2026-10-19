"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { BiomarkerCard } from "@/components/biomarker-card";
import { RiskBadge } from "@/components/risk-badge";
import { BiomarkerChart } from "@/components/charts/biomarker-chart";
import {
  useAnalyzeReport,
  useDeleteReport,
  useReport,
  useReportAnalysis,
} from "@/hooks/use-reports";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { MedicalDisclaimer } from "@/components/medical-disclaimer";
import { apiErrorMessage } from "@/lib/api-error";
import { formatApiDate } from "@/lib/dates";
import { downloadFromApi } from "@/lib/download";
import { reportStatusMeta } from "@/lib/report-status";
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
  Download,
  Trash2,
} from "lucide-react";
import { toBiomarkers, unclassifiedMarkers } from "@/lib/biomarkers";
import { SuggestionsView } from "@/components/suggestions-view";
import {
  useReportSuggestions,
  useRequestPlan,
} from "@/hooks/use-suggestions";
import { toast } from "sonner";

export default function ReportAnalysisPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const { data: report, isLoading } = useReport(id);
  const { data: analysis, isLoading: analysisLoading } = useReportAnalysis(id);
  // The analysis query polls while the pipeline runs, so its status is the
  // freshest; the report itself is fetched once. The status also gates the
  // suggestions query: a report never sent for analysis (or one that failed)
  // will not get suggestions, so polling for them would be wasted requests.
  const status = analysis?.status ?? report?.status;
  const statusMeta = reportStatusMeta(status);
  const { data: suggestions } = useReportSuggestions(
    id,
    statusMeta.inFlight || status === "completed",
    statusMeta.inFlight
  );
  const analyzeMutation = useAnalyzeReport();
  const requestDiet = useRequestPlan("diet");
  const requestWorkout = useRequestPlan("workout");
  const deleteMutation = useDeleteReport();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const downloadPdf = async () => {
    setDownloading(true);
    try {
      await downloadFromApi(`/pdf/reports/${id}/pdf`, `nutrimed_report_${id}.pdf`);
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not create the PDF. Please try again."));
    } finally {
      setDownloading(false);
    }
  };

  const deleteReport = async () => {
    try {
      await deleteMutation.mutateAsync(id);
      toast.success("Report deleted.");
      router.push("/upload-report");
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not delete the report."));
    }
  };

  const askForPlan = async (
    kind: "diet" | "workout",
    mutation: typeof requestDiet
  ) => {
    try {
      const result = await mutation.mutateAsync(id);
      toast.success(result.message);
      // Carry the report id so the plan page can poll for this build.
      router.push(
        `${kind === "diet" ? "/diet-plan" : "/workout-plan"}?report=${id}`
      );
    } catch {
      toast.error(
        `Could not start ${kind} plan generation. Please try again shortly.`
      );
    }
  };

  const biomarkers = toBiomarkers(analysis?.biomarkers);
  const unclassified = unclassifiedMarkers(analysis?.biomarkers);
  const abnormalCount = biomarkers.filter((b) => b.status !== "Normal").length;

  const isProcessing = statusMeta.inFlight;
  const isComplete = status === "completed";
  const loading = isLoading || analysisLoading;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-50">Report Analysis</h2>
          <p className="text-slate-400 mt-1">
            Detailed analysis of your medical report.
          </p>
        </div>
        {report && (
          <div className="flex flex-wrap gap-2">
            {isComplete && (
              <Button
                variant="outline"
                className="border-slate-700 bg-transparent text-slate-200 hover:bg-slate-800"
                onClick={downloadPdf}
                disabled={downloading}
              >
                {downloading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Download className="mr-2 h-4 w-4" />
                )}
                {downloading ? "Preparing PDF..." : "Download PDF"}
              </Button>
            )}
            {!isProcessing && (
              <Button
                className="bg-blue-600 hover:bg-blue-700 text-white"
                onClick={() =>
                  analyzeMutation.mutate(id, {
                    onError: (error) =>
                      toast.error(apiErrorMessage(error, "Could not start the analysis. Please try again.")),
                  })
                }
                disabled={analyzeMutation.isPending}
              >
                {analyzeMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : isComplete ? (
                  "Re-run Analysis"
                ) : (
                  "Analyze Report"
                )}
              </Button>
            )}
            <Button
              variant="outline"
              className="border-red-500/40 bg-transparent text-red-400 hover:bg-red-500/10 hover:text-red-300"
              onClick={() => setConfirmDelete(true)}
              aria-label="Delete report"
            >
              <Trash2 className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">Delete</span>
            </Button>
          </div>
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
                {report?.original_filename || "Medical Report"}
              </h3>
              <div className="flex flex-wrap gap-4 mt-1 text-sm text-slate-400">
                <span className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" />
                  {formatApiDate(report?.uploaded_at, "MMMM dd, yyyy", "Recent")}
                </span>
                <span>{report?.report_type || "General Health Checkup"}</span>
              </div>
            </div>
            <Badge variant="outline" className={statusMeta.badgeClass}>
              {isProcessing && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
              {statusMeta.label}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {(isComplete || suggestions) && <MedicalDisclaimer variant="callout" />}

      {suggestions && (
        <SuggestionsView
          suggestions={suggestions}
          onRequestDietPlan={() => askForPlan("diet", requestDiet)}
          onRequestWorkoutPlan={() => askForPlan("workout", requestWorkout)}
          dietPlanPending={requestDiet.isPending}
          workoutPlanPending={requestWorkout.isPending}
        />
      )}

      <div>
        <h3 className="text-lg font-semibold text-slate-200">Your biomarkers</h3>
        <p className="text-sm text-slate-400">
          The measurements the suggestions above are based on.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? (
          <>
            <BiomarkerCardSkeleton />
            <BiomarkerCardSkeleton />
            <BiomarkerCardSkeleton />
            <BiomarkerCardSkeleton />
          </>
        ) : biomarkers.length === 0 ? (
          <p className="col-span-full text-sm text-slate-400 py-4">
            {isProcessing
              ? "Extracting biomarkers from your report..."
              : "No biomarkers extracted from this report yet."}
          </p>
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
            {(analysis?.risk_factors?.length ?? 0) === 0 &&
            (analysis?.warnings?.length ?? 0) === 0 ? (
              <p className="text-sm text-slate-400 text-center py-4">
                {isComplete
                  ? "No risk factors identified in this report."
                  : "Risk factors appear once analysis completes."}
              </p>
            ) : (
              <>
                {analysis?.risk_factors?.map((risk, index) => (
                  <div
                    key={`risk-${index}`}
                    className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50"
                  >
                    <AlertTriangle className="h-5 w-5 mt-0.5 flex-shrink-0 text-red-400" />
                    <div className="flex-1 flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-200">
                        {risk}
                      </span>
                      <RiskBadge level="high" label="Risk" />
                    </div>
                  </div>
                ))}
                {analysis?.warnings?.map((warning, index) => (
                  <div
                    key={`warn-${index}`}
                    className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50"
                  >
                    <AlertTriangle className="h-5 w-5 mt-0.5 flex-shrink-0 text-amber-400" />
                    <div className="flex-1 flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-200">
                        {warning}
                      </span>
                      <RiskBadge level="medium" label="Watch" />
                    </div>
                  </div>
                ))}
              </>
            )}
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-200">Deficiencies</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(analysis?.deficiencies?.length ?? 0) === 0 ? (
              <p className="text-sm text-slate-400 text-center py-4">
                {isComplete
                  ? "No significant deficiencies detected."
                  : "Deficiencies appear once analysis completes."}
              </p>
            ) : (
              analysis?.deficiencies?.map((def, index) => (
                <div
                  key={index}
                  className="p-3 rounded-lg bg-slate-800/50 flex items-center justify-between gap-2"
                >
                  <span className="text-sm font-medium text-slate-200">
                    {def}
                  </span>
                  <RiskBadge level="high" label="Deficient" />
                </div>
              ))
            )}

            {(analysis?.supplement_suggestions?.length ?? 0) > 0 && (
              <div className="pt-2 space-y-2">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Suggested supplements
                </p>
                {analysis?.supplement_suggestions?.map((supp, index) => (
                  <div key={index} className="p-3 rounded-lg bg-slate-800/50 space-y-1">
                    <span className="text-sm font-medium text-slate-200">
                      {supp.name}
                    </span>
                    <div className="flex flex-wrap gap-x-4 text-xs text-slate-400">
                      {supp.dosage && <span>Dose: {supp.dosage}</span>}
                      {supp.timing && <span>When: {supp.timing}</span>}
                    </div>
                    {supp.notes && (
                      <p className="text-xs text-slate-400">{supp.notes}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Biomarker Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <ChartSkeleton />
          ) : biomarkers.length === 0 ? (
            <p className="text-sm text-slate-400 py-4">
              No biomarker data to chart yet.
            </p>
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
          {!isComplete ? (
            <p className="text-sm text-slate-400">
              {isProcessing
                ? "Analysis is still running. This page updates automatically when it finishes."
                : status === "failed"
                  ? "Analysis failed for this report. Try running it again, or re-upload the file."
                  : "Run the analysis to see an interpretation of this report."}
            </p>
          ) : abnormalCount === 0 &&
            (analysis?.deficiencies?.length ?? 0) === 0 &&
            (analysis?.risk_factors?.length ?? 0) === 0 ? (
            <p className="text-sm text-slate-300 leading-relaxed">
              All {biomarkers.length} measured biomarkers fall within their
              reference ranges, and no deficiencies or risk factors were
              identified.
            </p>
          ) : (
            <p className="text-sm text-slate-300 leading-relaxed">
              {abnormalCount} of {biomarkers.length} measured biomarkers fall
              outside their reference range
              {(analysis?.deficiencies?.length ?? 0) > 0 &&
                `, indicating ${analysis?.deficiencies?.length} deficiency finding(s)`}
              {(analysis?.risk_factors?.length ?? 0) > 0 &&
                ` and ${analysis?.risk_factors?.length} risk factor(s)`}
              . Review the panels above for detail.
            </p>
          )}

          {unclassified.length > 0 && (
            <p className="text-xs text-slate-500">
              Not classified:{" "}
              {unclassified
                .map(
                  (m) =>
                    `${m.label} ${m.value}${m.unit ? ` ${m.unit}` : ""} (${m.note ?? "no reference range available"})`
                )
                .join("; ")}
              .
            </p>
          )}

          <p className="text-xs text-slate-500">
            This summary is generated from your report and is not a medical
            diagnosis. Discuss results with a qualified clinician.
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
      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete this report?"
        description="The uploaded file, its biomarkers, analysis, suggestions and any plans built from it will be permanently deleted."
        confirmLabel="Delete report"
        destructive
        pending={deleteMutation.isPending}
        onConfirm={deleteReport}
      />
    </div>
  );
}
