"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
import { Progress } from "@/components/ui/progress";
import { FileUpload } from "@/components/file-upload";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { OptionSelect } from "@/components/option-select";
import { useDeleteReport, useUploadReport, useReports } from "@/hooks/use-reports";
import { apiErrorMessage } from "@/lib/api-error";
import { formatApiDate } from "@/lib/dates";
import { reportStatusMeta } from "@/lib/report-status";
import type { Report } from "@/types";
import { toast } from "sonner";
import { Loader2, Trash2 } from "lucide-react";

// `value` must match the backend ReportType enum (app/models/report.py).
const reportTypes: { value: string; label: string }[] = [
  { value: "CBC", label: "Complete Blood Count (CBC)" },
  { value: "LIPID", label: "Lipid Panel" },
  { value: "DIABETES", label: "Metabolic Panel" },
  { value: "THYROID", label: "Thyroid Panel" },
  { value: "VITAMIN", label: "Vitamin Panel" },
  { value: "LFT", label: "Liver Function" },
  { value: "KFT", label: "Kidney Function" },
  { value: "GENERAL", label: "General Health Checkup" },
];

const reportTypeLabel = (value: string) =>
  reportTypes.find((t) => t.value === value)?.label ?? value;

export default function UploadReportPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [reportType, setReportType] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const router = useRouter();

  const uploadMutation = useUploadReport();
  const { data: reports, isLoading: reportsLoading } = useReports();
  const deleteMutation = useDeleteReport();
  const [toDelete, setToDelete] = useState<Report | null>(null);

  const confirmDelete = async () => {
    if (!toDelete) return;
    try {
      await deleteMutation.mutateAsync(toDelete.id);
      toast.success("Report deleted.");
      setToDelete(null);
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not delete the report."));
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !reportType) {
      toast.error("Please select a file and report type.");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("report_type", reportType);

    setUploadProgress(0);
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 90) {
          clearInterval(interval);
          return 90;
        }
        return prev + 10;
      });
    }, 200);

    try {
      const result = await uploadMutation.mutateAsync(formData);
      clearInterval(interval);
      setUploadProgress(100);
      toast.success("Report uploaded successfully!");
      setSelectedFile(null);
      setReportType("");
      setTimeout(() => {
        setUploadProgress(0);
        router.push(`/report-analysis/${result.id}`);
      }, 1000);
    } catch (error) {
      clearInterval(interval);
      setUploadProgress(0);
      toast.error(apiErrorMessage(error, "Failed to upload report. Please try again."));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-50">Upload Report</h2>
        <p className="text-slate-400 mt-1">
          Upload your medical reports for AI-powered analysis.
        </p>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">New Report</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <FileUpload
            onFileSelect={setSelectedFile}
            selectedFile={selectedFile}
            onClear={() => setSelectedFile(null)}
          />

          <div className="space-y-2">
            <label htmlFor="report-type" className="text-sm font-medium text-slate-300">
              Report Type
            </label>
            <OptionSelect
              id="report-type"
              value={reportType}
              onChange={setReportType}
              placeholder="Select report type"
              options={reportTypes}
            />
          </div>

          {uploadProgress > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Uploading...</span>
                <span className="text-slate-400">{uploadProgress}%</span>
              </div>
              <Progress value={uploadProgress} className="h-2" />
            </div>
          )}

          <Button
            className="w-full bg-blue-600 hover:bg-blue-700 text-white"
            onClick={handleUpload}
            disabled={!selectedFile || !reportType || uploadMutation.isPending}
          >
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              "Upload Report"
            )}
          </Button>
        </CardContent>
      </Card>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Recent Uploads</CardTitle>
        </CardHeader>
        <CardContent>
          {reportsLoading ? (
            <div className="text-center py-8 text-slate-400">Loading...</div>
          ) : reports && reports.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800 hover:bg-transparent">
                  <TableHead className="text-slate-400">File Name</TableHead>
                  <TableHead className="text-slate-400">Type</TableHead>
                  <TableHead className="text-slate-400">Status</TableHead>
                  <TableHead className="text-slate-400">Date</TableHead>
                  <TableHead className="text-slate-400 text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.map((report) => {
                  const meta = reportStatusMeta(report.status);
                  return (
                    <TableRow
                      key={report.id}
                      className="border-slate-800 hover:bg-slate-800/50"
                    >
                      <TableCell className="font-medium text-slate-200 max-w-[16rem] truncate">
                        {report.original_filename}
                      </TableCell>
                      <TableCell className="text-slate-300">
                        {reportTypeLabel(report.report_type)}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={meta.badgeClass}>
                          {meta.inFlight && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                          {meta.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-400">
                        {formatApiDate(report.uploaded_at, "MMM dd, yyyy")}
                      </TableCell>
                      <TableCell className="text-right whitespace-nowrap">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-blue-400 hover:text-blue-300"
                          onClick={() => router.push(`/report-analysis/${report.id}`)}
                        >
                          {report.status === "completed" ? "View" : "Open"}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className="ml-1 text-slate-500 hover:text-red-400 hover:bg-red-500/10"
                          onClick={() => setToDelete(report)}
                          aria-label={`Delete ${report.original_filename}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-slate-400">
              No reports uploaded yet.
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(open) => !open && setToDelete(null)}
        title="Delete this report?"
        description={
          <>
            <span className="font-medium text-slate-200">{toDelete?.original_filename}</span> and its biomarkers,
            analysis, suggestions and any plans built from it will be permanently deleted.
          </>
        }
        confirmLabel="Delete report"
        destructive
        pending={deleteMutation.isPending}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
