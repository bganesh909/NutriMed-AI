"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Loader2 } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: React.ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  /** Red confirm button, for actions that delete data. */
  destructive?: boolean;
  pending?: boolean;
  /** Disable the confirm button, e.g. until a password is typed. */
  confirmDisabled?: boolean;
  /** Extra content between the description and the buttons. */
  children?: React.ReactNode;
}

/** A modal confirmation for irreversible actions (in-app, not window.confirm). */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  onConfirm,
  destructive = false,
  pending = false,
  confirmDisabled = false,
  children,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => !pending && onOpenChange(next)}>
      <DialogContent className="bg-slate-900 text-slate-200 ring-slate-800 sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-slate-50 text-lg">{title}</DialogTitle>
          <DialogDescription className="text-slate-400">{description}</DialogDescription>
        </DialogHeader>
        {children}
        <DialogFooter className="bg-slate-950/40 border-slate-800">
          <Button
            variant="outline"
            className="border-slate-700 bg-transparent text-slate-300 hover:bg-slate-800 hover:text-slate-100"
            onClick={() => onOpenChange(false)}
            disabled={pending}
          >
            Cancel
          </Button>
          <Button
            className={
              destructive
                ? "bg-red-600 hover:bg-red-700 text-white"
                : "bg-blue-600 hover:bg-blue-700 text-white"
            }
            onClick={onConfirm}
            disabled={pending || confirmDisabled}
          >
            {pending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
