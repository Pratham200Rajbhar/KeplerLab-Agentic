import { NextResponse } from 'next/server';

/**
 * Edge middleware: checks for the refresh cookie on protected routes.
 * If missing, redirect to /auth. The cookie name must match whatever
 * the backend sets (commonly "refresh_token").
 */
export function middleware(request) {
  const { pathname } = request.nextUrl;

  // Public routes that don't require auth
  const publicPaths = ['/auth', '/view', '/api'];
  if (publicPaths.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Static assets and Next.js internals
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/favicon') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  // Check for refresh token cookie (HttpOnly, set by backend)
  const refreshToken = request.cookies.get('refresh_token');
  if (!refreshToken?.value) {
    const loginUrl = new URL('/auth', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
