"use client";

import { useRouter } from "next/navigation";
import { formatDistanceToNow } from "date-fns";
import { Bell, CheckCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from "@/hooks/use-notifications";
import { parseApiDate } from "@/lib/dates";
import { cn } from "@/lib/utils";
import type { AppNotification } from "@/types";

function timeAgo(iso: string): string {
  const date = parseApiDate(iso);
  return date ? formatDistanceToNow(date, { addSuffix: true }) : "";
}

export function NotificationsMenu() {
  const router = useRouter();
  const { data } = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const items = data?.items ?? [];
  const unread = data?.unread_count ?? 0;

  const open = (n: AppNotification) => {
    if (!n.read) markRead.mutate(n.id);
    if (n.report_id) router.push(`/report-analysis/${n.report_id}`);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            className="relative text-slate-300 hover:text-slate-100"
            aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
          />
        }
      >
        <Bell className="h-5 w-5" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 bg-slate-900 border border-slate-800 p-0">
        <div className="flex items-center justify-between px-3 py-2.5">
          <p className="text-sm font-semibold text-slate-100">Notifications</p>
          {unread > 0 && (
            <DropdownMenuItem
              closeOnClick={false}
              onClick={() => markAllRead.mutate()}
              className="cursor-pointer gap-1 px-2 text-xs text-blue-400 focus:bg-slate-800 focus:text-blue-300"
            >
              <CheckCheck className="h-3.5 w-3.5" />
              Mark all read
            </DropdownMenuItem>
          )}
        </div>
        <DropdownMenuSeparator className="m-0 bg-slate-800" />
        {items.length === 0 ? (
          <p className="px-3 py-8 text-center text-sm text-slate-400">
            You&apos;re all caught up. We&apos;ll let you know when a report has been analysed.
          </p>
        ) : (
          <div className="max-h-96 overflow-y-auto p-1">
            {items.map((n) => (
              <DropdownMenuItem
                key={n.id}
                onClick={() => open(n)}
                className="cursor-pointer items-start gap-2.5 rounded-md px-2.5 py-2 focus:bg-slate-800"
              >
                <span
                  className={cn(
                    "mt-1.5 h-2 w-2 shrink-0 rounded-full",
                    n.read ? "bg-transparent" : "bg-blue-500"
                  )}
                />
                <span className="min-w-0 flex-1">
                  <span
                    className={cn(
                      "block text-sm",
                      n.read ? "text-slate-300" : "font-medium text-slate-100"
                    )}
                  >
                    {n.title}
                  </span>
                  <span className="mt-0.5 block text-xs leading-relaxed text-slate-400 whitespace-normal">
                    {n.message}
                  </span>
                  <span className="mt-1 block text-[11px] text-slate-500">{timeAgo(n.created_at)}</span>
                </span>
              </DropdownMenuItem>
            ))}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
