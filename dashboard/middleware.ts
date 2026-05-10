// Edge middleware: gates every page on a Supabase Google session whose email
// matches ALLOWED_EMAIL. Anyone else is bounced to /login (or /403 for the
// "wrong account" case).

import { NextResponse, type NextRequest } from "next/server";
import { createServerClient } from "@supabase/ssr";

const PUBLIC_PATHS = ["/login", "/auth/callback", "/_next", "/favicon.ico", "/403"];

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  let response = NextResponse.next({ request: req });
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return req.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => req.cookies.set(name, value));
          response = NextResponse.next({ request: req });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  const allowed = process.env.ALLOWED_EMAIL?.toLowerCase();
  if (allowed && user.email?.toLowerCase() !== allowed) {
    const url = req.nextUrl.clone();
    url.pathname = "/403";
    return NextResponse.redirect(url);
  }

  return response;
}

export const config = {
  matcher: [
    // Run on all routes EXCEPT the listed static paths.
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
