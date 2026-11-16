import { type LookupAddress, lookup } from "node:dns";

// The only schemes we can fetch. Anything else (javascript:, data:, ftp:, file:) is rejected — the route
// spawns a local binary to fetch the URL, so a data: URI would never reach yt-dlp anyway.
const ALLOWED = new Set(["http:", "https:"]);

// IP ranges that must never be reachable from the server: loopback, private, link-local, multicast,
// broadcast, unspecified, CGNAT (RFC 6598), documentation (2001:db8::/32), 6to4 (2002::/16), and
// IPv4-mapped IPv6 that folds back to a blocked v4 address. Resolving the host before spawning
// yt-dlp closes the classic SSRF-by-redirect: a DNS name can point at 127.0.0.1.
function expandIPv6(ip: string): number[] | null {
  const parts = ip.split(":");
  if (parts.length === 8) {
    const nums = parts.map((p) => parseInt(p, 16));
    return nums.some((n) => !Number.isFinite(n) || n < 0 || n > 0xffff) ? null : nums;
  }
  const emptyIdx = parts.indexOf("");
  if (emptyIdx === -1) return null;
  const before = parts.slice(0, emptyIdx).map((p) => parseInt(p, 16));
  const after = parts.slice(emptyIdx + 1).map((p) => parseInt(p, 16));
  if (before.some(isNaN) || after.some(isNaN)) return null;
  const fill = 8 - before.length - after.length;
  if (fill < 0) return null;
  return [...before, ...new Array<number>(fill).fill(0), ...after];
}

function isBlocked(ip: string): boolean {
  // IPv4-mapped IPv6 (::ffff:a.b.c.d) — fold it down and check as v4.
  const v4Match = ip.match(/^::ffff:(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/i);
  if (v4Match) ip = `${v4Match[1]}.${v4Match[2]}.${v4Match[3]}.${v4Match[4]}`;

  if (ip.includes(".")) {
    const parts = ip.split(".");
    if (parts.length !== 4) return true;
    const nums = parts.map((p) => Number(p));
    if (nums.some((n) => !Number.isFinite(n) || n < 0 || n > 255)) return true;
    const [a, b] = nums;
    return (
      a === 0 || // 0.0.0.0/8 current network
      a === 10 || // 10.0.0.0/8 private
      a === 127 || // loopback
      (a === 169 && b === 254) || // link-local
      (a === 172 && b >= 16 && b <= 31) || // private
      (a === 192 && b === 168) || // private
      (a === 100 && b >= 64 && b <= 127) || // CGNAT
      (a === 198 && (b === 18 || b === 19)) || // 198.18.0.0/15 benchmarking, 198.19.0.0/16
      a >= 224 || // multicast 224.0.0.0/4
      a === 255 // broadcast 255.255.255.255/32
    );
  }

  if (!ip.includes(":")) return true;
  const w = expandIPv6(ip);
  if (!w) return true;
  return (
    w.every((p) => p === 0) || // :: unspecified
    (w[7] === 1 && w.slice(0, 7).every((p) => p === 0)) || // ::1 loopback
    (w[0] & 0xffc0) === 0xfe80 || // fe80::/10 link-local
    (w[0] & 0xfe00) === 0xfc00 || // fc00::/7 unique local (covers fc00:: and fd00::)
    (w[0] & 0xff00) === 0xff00 || // ff00::/8 multicast
    (w[0] === 0x2001 && w[1] === 0xdb8) || // 2001:db8::/32 documentation
    w[0] === 0x2002 // 2002::/16 6to4
  );
}

export type UrlResult =
  | { ok: true; url: string }
  | { ok: false; code: "bad_url" | "blocked_url"; message: string };

/**
 * Validate that a pasted URL is a fetchable video link.
 *
 * The default resolver uses the system resolver, so a host pointing at a private IP is rejected —
 * but the resolver is injectable for tests, which must never hit the network.
 */
export function validateVideoUrl(raw: string, resolver: (host: string) => Promise<string[]> = defaultResolver): Promise<UrlResult> {
  if (typeof raw !== "string" || raw.trim().length === 0) {
    return Promise.resolve({ ok: false, code: "bad_url", message: "Paste a link to a video." });
  }
  const trimmed = raw.trim();
  // A bare hostname like "example.com/watch" parses as a relative path, so require the scheme separator
  // before handing it to the URL parser. Only suggest the hint for something that looks like a host.
  if (!trimmed.includes("://") && trimmed.includes(".")) {
    return Promise.resolve({ ok: false, code: "bad_url", message: "Include the https:// — e.g. https://www.youtube.com/watch?v=..." });
  }
  let u: URL;
  try {
    u = new URL(trimmed);
  } catch {
    return Promise.resolve({ ok: false, code: "bad_url", message: "That isn't a valid URL." });
  }
  if (!ALLOWED.has(u.protocol)) {
    return Promise.resolve({ ok: false, code: "bad_url", message: "Only http and https links are supported." });
  }
  if (!u.hostname) {
    return Promise.resolve({ ok: false, code: "bad_url", message: "That URL has no host." });
  }
  return resolver(u.hostname).then((ips) => {
    if (ips.length === 0) {
      return { ok: false, code: "blocked_url", message: "That host doesn't resolve to a public address." };
    }
    for (const ip of ips) {
      if (isBlocked(ip)) {
        return { ok: false, code: "blocked_url", message: "That link points at a private address." };
      }
    }
    return { ok: true, url: u.toString() };
  });
}

function defaultResolver(host: string): Promise<string[]> {
  return new Promise((resolve) => {
    lookup(host, { all: true }, (err, addresses: LookupAddress[]) => {
      if (err) resolve([]);
      else resolve(addresses.map((a) => a.address));
    });
  });
}

/** Strip the query string and fragment before anything is written to a log or filename. */
export function redactUrl(url: string): string {
  try {
    const u = new URL(url);
    return `${u.origin}${u.pathname}`;
  } catch {
    return "[url]";
  }
}