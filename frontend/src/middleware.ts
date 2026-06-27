import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const protectedPaths = [
  "/dashboard",
  "/upload-report",
  "/report-analysis",
  "/diet-plan",
  "/workout-plan",
  "/progress",
  "/settings",
];

const publicPaths = ["/login", "/register"];

export function middleware(request: NextRequest) {
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

  if (isPublic && token) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/upload-report/:path*",
    "/report-analysis/:path*",
    "/diet-plan/:path*",
    "/workout-plan/:path*",
    "/progress/:path*",
    "/settings/:path*",
    "/login",
    "/register",
  ],
};
