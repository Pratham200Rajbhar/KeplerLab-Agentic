'use client';

export default function SkeletonLoader() {
  return (
    <div className="w-full space-y-3 animate-pulse">
      <div className="h-3 w-4/5 rounded-full bg-text-muted/10" />
      <div className="h-3 w-2/3 rounded-full bg-text-muted/10" />
      <div className="h-3 w-3/4 rounded-full bg-text-muted/10" />
      <div className="h-3 w-1/2 rounded-full bg-text-muted/10" />
    </div>
  );
}
