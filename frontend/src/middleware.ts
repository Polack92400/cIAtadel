import { NextResponse, type NextRequest } from "next/server";

// UX only: send visitors without a session hint to /login. Authorization is
// enforced exclusively by Django on every API call.
export function middleware(req: NextRequest) {
  if (!req.cookies.get("ciatadel_session")) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(req.nextUrl.pathname)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  // Never run on /api (keeps uploads streaming through the rewrite untouched).
  matcher: ["/((?!api|_next|login|favicon.ico).*)"],
};
