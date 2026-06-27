"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  selectedFile: File | null;
  onClear: () => void;
  accept?: Record<string, string[]>;
  className?: string;
}

export function FileUpload({
  onFileSelect,
  selectedFile,
  onClear,
  accept = {
    "application/pdf": [".pdf"],
    "image/*": [".png", ".jpg", ".jpeg"],
  },
  className,
}: FileUploadProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        onFileSelect(acceptedFiles[0]);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    multiple: false,
  });

  if (selectedFile) {
    return (
      <div
        className={cn(
          "border border-slate-800 rounded-lg p-6 bg-slate-900",
          className
        )}
      >
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-lg bg-blue-600/10">
            <FileText className="h-6 w-6 text-blue-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-200 truncate">
              {selectedFile.name}
            </p>
            <p className="text-xs text-slate-400">
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={(e) => {
              e.stopPropagation();
              onClear();
            }}
            className="text-slate-400 hover:text-red-400"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={cn(
        "border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors",
        isDragActive
          ? "border-blue-500 bg-blue-500/5"
          : "border-slate-700 hover:border-slate-600 bg-slate-900/50",
        className
      )}
    >
      <input {...getInputProps()} />
      <Upload className="h-10 w-10 text-slate-500 mx-auto mb-4" />
      <p className="text-sm font-medium text-slate-300 mb-1">
        {isDragActive ? "Drop file here" : "Drag & drop your report here"}
      </p>
      <p className="text-xs text-slate-500">
        Supports PDF, PNG, JPG up to 10MB
      </p>
    </div>
  );
}
