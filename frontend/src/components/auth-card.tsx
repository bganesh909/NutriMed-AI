import Link from "next/link";
import { Heart } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/** The centred card shared by the sign-in, sign-up and password pages. */
export function AuthCard({
  title,
  subtitle,
  children,
  wide = false,
}: {
  title: string;
  subtitle: React.ReactNode;
  children: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
      <Card className={cn("w-full bg-slate-900 border-slate-800", wide ? "max-w-lg" : "max-w-md")}>
        <CardHeader className="text-center space-y-4">
          <Link href="/" className="flex justify-center" aria-label="NutriMed AI home">
            <span className="p-3 rounded-xl bg-blue-600/10">
              <Heart className="h-8 w-8 text-blue-600" />
            </span>
          </Link>
          <div>
            <CardTitle className="text-2xl text-slate-50">{title}</CardTitle>
            <p className="text-sm text-slate-400 mt-1">{subtitle}</p>
          </div>
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </div>
  );
}

export const authInputClass = "bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500";
