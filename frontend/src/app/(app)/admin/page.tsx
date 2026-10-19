"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { OptionSelect } from "@/components/option-select";
import { StatsCard } from "@/components/stats-card";
import { StatsCardSkeleton, TableSkeleton } from "@/components/loading-skeleton";
import { useAdminDeleteUser, useAdminStats, useAdminUsers, useUpdateUserRole } from "@/hooks/use-admin";
import { useAuthStore } from "@/stores/auth-store";
import { apiErrorMessage } from "@/lib/api-error";
import { formatApiDate } from "@/lib/dates";
import { reportStatusMeta } from "@/lib/report-status";
import type { AdminUser, UserRole } from "@/types";
import { Dumbbell, FileText, LineChart, Loader2, Search, ShieldAlert, Trash2, Users } from "lucide-react";
import { toast } from "sonner";

const ROLE_OPTIONS = [
  { value: "user", label: "User" },
  { value: "admin", label: "Admin" },
];

type PendingAction =
  | { kind: "role"; user: AdminUser; role: UserRole }
  | { kind: "delete"; user: AdminUser };

export default function AdminPage() {
  const me = useAuthStore((s) => s.user);
  const isAdmin = me?.role === "admin";

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [pending, setPending] = useState<PendingAction | null>(null);

  const { data: stats, isLoading: statsLoading } = useAdminStats(isAdmin);
  const { data: users, isLoading: usersLoading, isFetching } = useAdminUsers(search, isAdmin);
  const updateRole = useUpdateUserRole();
  const deleteUser = useAdminDeleteUser();

  if (!isAdmin) {
    return (
      <Card className="bg-slate-900 border-slate-800 max-w-lg">
        <CardContent className="flex items-start gap-3 p-6">
          <ShieldAlert className="h-5 w-5 shrink-0 text-amber-400" />
          <div>
            <p className="font-medium text-slate-200">Admins only</p>
            <p className="mt-1 text-sm text-slate-400">You don&apos;t have access to the admin console.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const confirmPending = async () => {
    if (!pending) return;
    try {
      if (pending.kind === "role") {
        await updateRole.mutateAsync({ id: pending.user.id, role: pending.role });
        toast.success(`${pending.user.name} is now ${pending.role === "admin" ? "an admin" : "a regular user"}.`);
      } else {
        await deleteUser.mutateAsync(pending.user.id);
        toast.success(`${pending.user.name}'s account was deleted.`);
      }
      setPending(null);
    } catch (error) {
      toast.error(apiErrorMessage(error, "The change could not be saved."));
    }
  };

  const statusCounts = Object.entries(stats?.reports_by_status ?? {}).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-50">Admin console</h2>
        <p className="text-slate-400 mt-1">Platform activity and user accounts. Report contents are never shown here.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statsLoading || !stats ? (
          <>
            <StatsCardSkeleton />
            <StatsCardSkeleton />
            <StatsCardSkeleton />
            <StatsCardSkeleton />
          </>
        ) : (
          <>
            <StatsCard label="Users" value={stats.users} subtitle={`+${stats.new_users_7d} in the last 7 days`} icon={Users} />
            <StatsCard label="Reports" value={stats.reports} subtitle={`+${stats.reports_7d} in the last 7 days`} icon={FileText} />
            <StatsCard
              label="Plans generated"
              value={stats.diet_plans + stats.workout_plans}
              subtitle={`${stats.diet_plans} diet · ${stats.workout_plans} workout`}
              icon={Dumbbell}
            />
            <StatsCard label="Progress entries" value={stats.progress_entries} subtitle="Logged by users" icon={LineChart} />
          </>
        )}
      </div>

      {statusCounts.length > 0 && (
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="flex flex-wrap items-center gap-2 p-4">
            <span className="mr-2 text-sm text-slate-400">Reports by status</span>
            {statusCounts.map(([status, count]) => (
              <Badge key={status} variant="outline" className={reportStatusMeta(status).badgeClass}>
                {reportStatusMeta(status).label}: {count}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="text-slate-200">Users</CardTitle>
          <form
            className="flex w-full gap-2 sm:w-auto"
            onSubmit={(e) => {
              e.preventDefault();
              setSearch(searchInput.trim());
            }}
          >
            <Input
              type="search"
              placeholder="Search name or email"
              aria-label="Search users"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500 sm:w-64"
            />
            <Button type="submit" variant="outline" className="border-slate-700 bg-transparent text-slate-200 hover:bg-slate-800">
              {isFetching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              <span className="sr-only">Search</span>
            </Button>
          </form>
        </CardHeader>
        <CardContent>
          {usersLoading ? (
            <TableSkeleton rows={5} />
          ) : !users || users.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-400">
              {search ? `No users match "${search}".` : "No users yet."}
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800 hover:bg-transparent">
                  <TableHead className="text-slate-400">Name</TableHead>
                  <TableHead className="text-slate-400">Email</TableHead>
                  <TableHead className="text-slate-400">Role</TableHead>
                  <TableHead className="text-slate-400 text-right">Reports</TableHead>
                  <TableHead className="text-slate-400">Joined</TableHead>
                  <TableHead className="text-slate-400 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((u) => {
                  const isMe = u.id === me?.id;
                  return (
                    <TableRow key={u.id} className="border-slate-800 hover:bg-slate-800/50">
                      <TableCell className="font-medium text-slate-200">
                        {u.name}
                        {isMe && <span className="ml-2 text-xs text-slate-500">(you)</span>}
                      </TableCell>
                      <TableCell className="text-slate-300">{u.email}</TableCell>
                      <TableCell className="w-36">
                        <OptionSelect
                          value={u.role}
                          onChange={(role) => role !== u.role && setPending({ kind: "role", user: u, role: role as UserRole })}
                          options={ROLE_OPTIONS}
                          placeholder="Role"
                          disabled={isMe}
                          className="h-8"
                        />
                      </TableCell>
                      <TableCell className="text-right text-slate-300 tabular-nums">{u.report_count}</TableCell>
                      <TableCell className="text-slate-400">{formatApiDate(u.created_at, "MMM d, yyyy")}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className="text-slate-500 hover:text-red-400 hover:bg-red-500/10"
                          onClick={() => setPending({ kind: "delete", user: u })}
                          disabled={isMe}
                          aria-label={`Delete ${u.name}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={!!pending}
        onOpenChange={(open) => !open && setPending(null)}
        title={
          pending?.kind === "delete"
            ? `Delete ${pending.user.name}?`
            : pending?.role === "admin"
              ? `Make ${pending?.user.name} an admin?`
              : `Remove admin access from ${pending?.user.name}?`
        }
        description={
          pending?.kind === "delete"
            ? "Their account, reports, analyses, plans and progress will be permanently deleted."
            : pending?.role === "admin"
              ? "Admins can see every user account and change roles."
              : "They will lose access to the admin console."
        }
        confirmLabel={pending?.kind === "delete" ? "Delete user" : "Confirm"}
        destructive={pending?.kind === "delete"}
        pending={updateRole.isPending || deleteUser.isPending}
        onConfirm={confirmPending}
      />
    </div>
  );
}
