"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { useUploadReport, useReports } from "@/hooks/use-reports";
import { toast } from "sonner";
import { format } from "date-fns";
import { Loader2 } from "lucide-react";

const reportTypes = [
  "Complete Blood Count (CBC)",
  "Lipid Panel",
  "Metabolic Panel",
  "Thyroid Panel",
  "Vitamin Panel",
  "Liver Function",
  "Kidney Function",
  "General Health Checkup",
  "Other",
];

const statusBadgeClass: Record<string, string> = {
  uploaded: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  processing: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  analyzed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  error: "bg-red-500/10 text-red-400 border-red-500/20",
};

export default function UploadReportPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [reportType, setReportType] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const router = useRouter();

  const uploadMutation = useUploadReport();
  const { data: reports, isLoading: reportsLoading } = useReports();

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
    } catch {
      clearInterval(interval);
      setUploadProgress(0);
      toast.error("Failed to upload report. Please try again.");
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
            <label className="text-sm font-medium text-slate-300">
              Report Type
            </label>
            <Select value={reportType} onValueChange={(v) => v && setReportType(v)}>
              <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                <SelectValue placeholder="Select report type" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                {reportTypes.map((type) => (
                  <SelectItem
                    key={type}
                    value={type}
                    className="text-slate-200 focus:bg-slate-700 focus:text-slate-100"
                  >
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
                {reports.map((report) => (
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
                        disabled={report.status !== "analyzed"}
                      >
                        {report.status === "analyzed" ? "View" : "Pending"}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-slate-400">
              No reports uploaded yet.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
