import crypto from "crypto";

export type NewsDisruptionItem = {
  id: string;
  impact: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  title: string;
  tags: string[];
  description: string;
  timeline: Array<{ time: string; text: string; muted?: boolean }>;
  source?: string;
  url?: string;
};

/** Call Google Custom Search JSON API; returns parsed data or null. */
async function fetchGoogleSearch(
  query: string,
  num: number = 10
): Promise<{
  items?: Array<{
    title?: string;
    link?: string;
    snippet?: string;
    displayLink?: string;
    pagemap?: { metatags?: Array<Record<string, string>> };
  }>;
} | null> {
  const apiKey = process.env.GOOGLE_SEARCH_API_KEY ?? process.env.GOOGLE_API_KEY;
  const cx = process.env.GOOGLE_SEARCH_ENGINE_ID;
  if (!apiKey || !cx) return null;
  const url = new URL("https://www.googleapis.com/customsearch/v1");
  url.searchParams.set("key", apiKey);
  url.searchParams.set("cx", cx);
  url.searchParams.set("q", query);
  url.searchParams.set("num", String(Math.min(num, 10)));
  try {
    const res = await fetch(url.toString());
    if (!res.ok) return null;
    const data = await res.json();
    return data;
  } catch {
    return null;
  }
}

function hashId(url: string): string {
  return crypto.createHash("sha1").update(url).digest("hex").slice(0, 12);
}

function inferSeverity(
  title: string,
  snippet: string
): "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" {
  const t = `${(title ?? "").toLowerCase()} ${(snippet ?? "").toLowerCase()}`;
  if (/\b(blockade|closed|halt|critical|crisis|war|attack)\b/.test(t)) return "CRITICAL";
  if (/\b(suez|red sea|panama|canal|delay|disruption)\b/.test(t)) return "HIGH";
  if (/\b(slow|congestion|shortage|risk)\b/.test(t)) return "MEDIUM";
  return "LOW";
}

function formatArticleTime(meta: Record<string, string> | undefined): string {
  if (!meta) return new Date().toISOString();
  const v =
    meta["article:published_time"] ??
    meta["datePublished"] ??
    meta["pubdate"] ??
    meta["date"];
  if (v) return v;
  return new Date().toISOString();
}

function formatTime(isoOrDateStr: string): string {
  try {
    const d = new Date(isoOrDateStr);
    return d
      .toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
      .replace(/^24/, "00");
  } catch {
    return isoOrDateStr;
  }
}

/** Fetch real-world disruption articles from Google CSE. Returns empty array if not configured or on error. */
export async function fetchNewsDisruptions(): Promise<NewsDisruptionItem[]> {
  const data = await fetchGoogleSearch("supply chain disruption shipping 2025");
  const items = data?.items ?? [];
  return items.map((it) => {
    const link = it.link ?? "";
    const id = `news-${hashId(link)}`;
    const title = (it.title ?? "").trim() || "Supply chain disruption";
    const snippet = (it.snippet ?? "").trim();
    const meta = it.pagemap?.metatags?.[0];
    const published = formatArticleTime(meta);
    const severity = inferSeverity(title, snippet);
    const tags: string[] = [];
    if (/\bshipping\b/i.test(title + snippet)) tags.push("Shipping");
    if (/\bsuez|red sea|panama|canal\b/i.test(title + snippet)) tags.push("Maritime");
    if (/\bsupply chain\b/i.test(title + snippet)) tags.push("Supply Chain");
    if (tags.length === 0) tags.push("News");
    return {
      id,
      impact: "—",
      severity,
      title: title.length > 70 ? title.slice(0, 70) + "…" : title,
      tags,
      description: snippet || title,
      timeline: [{ time: formatTime(published), text: snippet || title }],
      source: it.displayLink ?? link.slice(0, 50),
      url: link,
    };
  });
}
