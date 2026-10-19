import {
  Dumbbell,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Upload,
  UtensilsCrossed,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const navItems: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload-report", label: "Upload Report", icon: Upload },
  { href: "/suggestions", label: "Suggestions", icon: Sparkles },
  { href: "/diet-plan", label: "Diet Plan", icon: UtensilsCrossed },
  { href: "/workout-plan", label: "Workout Plan", icon: Dumbbell },
  { href: "/progress", label: "Progress", icon: TrendingUp },
  { href: "/settings", label: "Settings", icon: Settings },
];

/** Shown only to users with the admin role. */
export const adminNavItem: NavItem = { href: "/admin", label: "Admin", icon: ShieldCheck };

/** Pages reached from within others rather than from the sidebar. */
const extraTitles: Record<string, string> = {
  "/report-analysis": "Report Analysis",
};

/** Header title for a pathname, e.g. "/report-analysis/123" → "Report Analysis". */
export function pageTitle(pathname: string): string {
  const all = [...navItems, adminNavItem];
  const item = all.find((i) => pathname === i.href || pathname.startsWith(`${i.href}/`));
  if (item) return item.label;
  const extra = Object.keys(extraTitles).find((p) => pathname === p || pathname.startsWith(`${p}/`));
  return extra ? extraTitles[extra] : "NutriMed AI";
}
