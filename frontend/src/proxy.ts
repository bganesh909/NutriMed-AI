import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const protectedPaths = [
  "/dashboard",
  "/upload-report",
  "/suggestions",
  "/report-analysis",
  "/diet-plan",
  "/workout-plan",
  "/progress",
  "/settings",
  "/admin",
];

// Signed-in users are sent on to the dashboard from these. /reset-password is
// deliberately absent: a reset link must work whatever the session state.
const publicPaths = ["/login", "/register", "/forgot-password"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get("token")?.value;

  const isProtected = protectedPaths.some((path) =>
    pathname.startsWith(path)
  );
  const isPublic = publicPaths.some((path) => pathname.startsWith(path));

  if (isProtected && !token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // The landing page is for visitors; signed-in users go straight to the app.
  if ((isPublic || pathname === "/") && token) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/",
    "/dashboard/:path*",
    "/upload-report/:path*",
    "/suggestions/:path*",
    "/report-analysis/:path*",
    "/diet-plan/:path*",
    "/workout-plan/:path*",
    "/progress/:path*",
    "/settings/:path*",
    "/admin/:path*",
    "/login",
    "/register",
    "/forgot-password",
  ],
};
