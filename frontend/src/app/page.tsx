"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Send, ExternalLink, Loader2 } from "lucide-react";
import {
  listJobs,
  runCrawl,
  postChat,
  type Job,
  type CrawlResponse,
  type Citation,
  type ChatResponse,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/Toaster";
import { cn } from "@/lib/utils";

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
};

function JobRow({ job }: { job: Job }) {
  return (
    <a
      href={job.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-baseline justify-between gap-4 py-3 border-b border-[var(--border-subtle)] last:border-0 group focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--accent)]"
    >
      <div className="min-w-0">
        <span className="font-medium text-[var(--text)] group-hover:text-[var(--accent)] transition-colors block truncate">
          {job.title || "Untitled"}
        </span>
        {job.company && (
          <span className="text-sm text-[var(--text-muted)]">
            {job.company}
          </span>
        )}
      </div>
      <ExternalLink className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)] group-hover:text-[var(--accent)] transition-colors" />
    </a>
  );
}

function CitationLink({ citation }: { citation: Citation }) {
  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block py-1.5 text-sm text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--accent)]"
    >
      {citation.title || "Job"}
      {citation.company && ` · ${citation.company}`}
    </a>
  );
}

function JobRowSkeleton() {
  return (
    <div className="flex items-baseline justify-between gap-4 py-3 border-b border-[var(--border-subtle)] animate-pulse">
      <div className="space-y-1">
        <div className="h-4 w-3/4 rounded bg-[var(--border)]" />
        <div className="h-3 w-1/2 rounded bg-[var(--border)]" />
      </div>
    </div>
  );
}

export default function Home() {
  const { user, loading: authLoading, logout } = useAuth();
  const router = useRouter();
  const toast = useToast();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [crawling, setCrawling] = useState(false);
  const [query, setQuery] = useState("software engineer jobs");
  const [maxJobs, setMaxJobs] = useState(10);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listJobs(20);
      setJobs(data.jobs);
    } catch {
      setJobs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const isAdmin = user?.is_admin ?? false;

  useEffect(() => {
    if (user && isAdmin) fetchJobs();
  }, [user, isAdmin, fetchJobs]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, chatLoading]);

  async function handleCrawl(e: React.FormEvent) {
    e.preventDefault();
    setCrawling(true);
    try {
      const data: CrawlResponse = await runCrawl(
        query.trim() || "software engineer jobs",
        maxJobs,
      );
      setJobs(data.jobs);
      if (data.jobs.length > 0)
        toast.success(data.message, "Crawl finished");
      else toast.info(data.message);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Crawl failed",
        "Crawl failed",
      );
    } finally {
      setCrawling(false);
    }
  }

  async function handleChatSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = chatInput.trim();
    if (!text || chatLoading) return;
    setChatMessages((prev) => [...prev, { role: "user", text }]);
    setChatInput("");
    setChatLoading(true);
    try {
      const data: ChatResponse = await postChat(text);
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", text: data.reply, citations: data.citations },
      ]);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Chat failed",
        "Chat error",
      );
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Sorry, I couldn't process that. Try again.",
        } as ChatMessage,
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  if (authLoading || !user) return null;

  return (
    <div className="flex flex-col h-screen">
      {/* Top bar */}
      <header className="h-12 shrink-0 flex items-center justify-between px-4 border-b border-[var(--border)] bg-[var(--bg-panel)]">
        <span className="text-sm font-semibold tracking-tight text-[var(--text)]">
          Agentics
        </span>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-[var(--text-muted)] hidden sm:inline">
            {user.email}
          </span>
          <button
            onClick={logout}
            className="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Split panels: Jobs + Crawl only for admin; Chat for everyone */}
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row">
        {/* Left: Jobs + Crawler (admin only) */}
        {isAdmin && (
          <section className="flex-1 lg:flex-none lg:w-2/5 min-w-0 border-b lg:border-b-0 lg:border-r border-[var(--border)] flex flex-col">
            <div className="px-4 sm:px-6 py-3 border-b border-[var(--border)]">
              <span className="text-xs font-medium uppercase tracking-wide text-[var(--text-muted)]">
                Jobs
              </span>
            </div>

            <div className="p-4 sm:p-6 flex-1 flex flex-col min-h-0">
              <form
                onSubmit={handleCrawl}
                className="flex flex-col sm:flex-row gap-3 sm:gap-2 mb-4"
              >
                <div className="flex-1 min-w-0 flex gap-2">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search query"
                    aria-label="Search query"
                    className="flex-1 min-w-0 rounded border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
                  />
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={maxJobs}
                    onChange={(e) => setMaxJobs(Number(e.target.value) || 10)}
                    aria-label="Max jobs"
                    className="w-14 rounded border border-[var(--border)] bg-[var(--bg-elevated)] px-2 py-2 text-sm text-[var(--text)] focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
                  />
                </div>
                <button
                  type="submit"
                  disabled={crawling}
                  className="inline-flex items-center justify-center gap-2 rounded border-0 bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]"
                >
                  {crawling ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                  {crawling ? "Running…" : "Crawl"}
                </button>
              </form>

              <div className="flex-1 min-h-0 overflow-y-auto">
                {loading ? (
                  <div className="space-y-0">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <JobRowSkeleton key={i} />
                    ))}
                  </div>
                ) : jobs.length === 0 ? (
                  <p className="text-sm text-[var(--text-muted)] py-8">
                    No jobs yet. Run a crawl to get started.
                  </p>
                ) : (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.15 }}
                    className="space-y-0"
                  >
                    {jobs.map((job) => (
                      <JobRow key={job.id} job={job} />
                    ))}
                  </motion.div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* Right: Chat */}
        <section className="flex-1 min-w-0 flex flex-col">
          <div className="px-4 sm:px-6 py-3 border-b border-[var(--border)]">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--text-muted)]">
              Chat
            </span>
          </div>

          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
              {chatMessages.length === 0 && !chatLoading ? (
                <p className="text-sm text-[var(--text-muted)] py-8">
                  Ask about jobs in the store. Run a crawl first if the list is
                  empty.
                </p>
              ) : (
                <>
                  <AnimatePresence initial={false}>
                    {chatMessages.map((msg, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.15 }}
                        className={cn(
                          "max-w-[85%] rounded px-3 py-2 text-sm",
                          msg.role === "user"
                            ? "ml-auto bg-[var(--accent-muted)] text-[var(--text)] border border-[var(--accent)]/20"
                            : "mr-auto bg-[var(--bg-elevated)] text-[var(--text)] border border-[var(--border-subtle)]",
                        )}
                      >
                        <div className="whitespace-pre-wrap leading-relaxed">
                          {msg.text}
                        </div>
                        {msg.role === "assistant" &&
                          msg.citations &&
                          msg.citations.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
                              <p className="text-xs text-[var(--text-muted)] mb-1.5">
                                Sources
                              </p>
                              {msg.citations.map((c, j) => (
                                <CitationLink key={j} citation={c} />
                              ))}
                            </div>
                          )}
                      </motion.div>
                    ))}
                  </AnimatePresence>
                  {chatLoading && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="mr-auto max-w-[85%] rounded px-3 py-2 text-sm bg-[var(--bg-elevated)] border border-[var(--border-subtle)] flex items-center gap-2 text-[var(--text-muted)]"
                    >
                      <Loader2 className="h-4 w-4 animate-spin shrink-0" />
                      Thinking…
                    </motion.div>
                  )}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

            <form
              onSubmit={handleChatSubmit}
              className="p-4 sm:p-6 border-t border-[var(--border)] bg-[var(--bg-panel)]"
            >
              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask about jobs…"
                  disabled={chatLoading}
                  aria-label="Chat message"
                  className="flex-1 min-w-0 rounded border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)] disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={chatLoading || !chatInput.trim()}
                  className="shrink-0 inline-flex items-center justify-center rounded bg-[var(--accent)] p-2 text-white hover:bg-[var(--accent-hover)] disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]"
                  aria-label="Send"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}
