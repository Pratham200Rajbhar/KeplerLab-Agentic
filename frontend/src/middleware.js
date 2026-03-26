import { NextResponse } from 'next/server';


const PUBLIC_PREFIXES = ['/auth', '/view', '/api'];
const STATIC_EXT = /\.(ico|png|jpg|jpeg|gif|svg|webp|woff2?|ttf|eot|css|js|map|json|txt|xml|webmanifest)$/i;

export function middleware(request) {
  const { pathname } = request.nextUrl;

  if (pathname === '/' || PUBLIC_PREFIXES.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  
  if (pathname.startsWith('/_next') || pathname.startsWith('/favicon') || STATIC_EXT.test(pathname)) {
    return NextResponse.next();
  }

  
  const refreshToken = request.cookies.get('refresh_token');
  if (!refreshToken?.value) {
    const loginUrl = new URL('/auth', request.url);
    if (pathname !== '/') loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
