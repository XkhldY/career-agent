"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse-soft rounded-md bg-[var(--border)]/60", className)}
      {...props}
    />
  );
}

export function JobCardSkeleton() {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-solid)]/80 backdrop-blur-sm p-4 flex justify-between items-start gap-4 shadow-[var(--shadow-xs)]">
      <div className="min-w-0 flex-1 space-y-2">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
      <Skeleton className="h-10 w-20 shrink-0 rounded-lg" />
    </div>
  );
}

export function ChatBubbleSkeleton() {
  return (
    <div className="mr-8 flex gap-2 rounded-2xl bg-[var(--bg-card)]/80 p-4 border border-[var(--border)]">
      <Skeleton className="h-4 w-4 shrink-0 rounded-full" />
      <div className="space-y-2 flex-1">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-4/5" />
        <Skeleton className="h-3 w-2/3" />
      </div>
    </div>
  );
}
