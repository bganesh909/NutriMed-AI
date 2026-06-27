"use client";

import { useRouter } from "next/navigation";
import { LogOut, User, ChevronDown } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MobileSidebar } from "./sidebar";

interface HeaderProps {
  title?: string;
}

export function Header({ title }: HeaderProps) {
  const { user, logout } = useAuthStore();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm">
      <div className="flex h-16 items-center gap-4 px-4 sm:px-6">
        <MobileSidebar />

        <h1 className="text-lg font-semibold text-slate-100 flex-1">
          {title || "Dashboard"}
        </h1>

        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button
                variant="ghost"
                className="flex items-center gap-2 text-slate-300 hover:text-slate-100"
              />
            }
          >
            <Avatar className="h-7 w-7">
              <AvatarFallback className="bg-blue-600 text-white text-xs">
                {user?.name
                  ?.split(" ")
                  .map((n) => n[0])
                  .join("")
                  .toUpperCase() || "U"}
              </AvatarFallback>
            </Avatar>
            <span className="hidden sm:inline text-sm">{user?.name || "User"}</span>
            <ChevronDown className="h-4 w-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="w-48 bg-slate-900 border-slate-800"
          >
            <DropdownMenuItem
              onClick={() => router.push("/settings")}
              className="cursor-pointer text-slate-300 focus:text-slate-100 focus:bg-slate-800"
            >
              <User className="mr-2 h-4 w-4" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuSeparator className="bg-slate-800" />
            <DropdownMenuItem
              onClick={handleLogout}
              className="cursor-pointer text-red-400 focus:text-red-300 focus:bg-slate-800"
            >
              <LogOut className="mr-2 h-4 w-4" />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
