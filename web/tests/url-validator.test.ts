import { describe, expect, it } from "vitest";
import { redactUrl, validateVideoUrl } from "@/lib/url";

// A fake resolver that never touches the network: the validator's real behaviour is in the parsing and
// the blocked-IP list, so tests pin those down deterministically.
const resolveTo = (ips: string[]) => () => Promise.resolve(ips);

describe("validateVideoUrl", () => {
  it("rejects empty and non-strings", async () => {
    expect(await validateVideoUrl("", resolveTo([]))).toEqual({ ok: false, code: "bad_url", message: "Paste a link to a video." });
    expect(await validateVideoUrl("   ", resolveTo([]))).toEqual({ ok: false, code: "bad_url", message: "Paste a link to a video." });
  });

  it("rejects malformed URLs", async () => {
    expect(await validateVideoUrl("not a url", resolveTo([]))).toEqual({ ok: false, code: "bad_url", message: "That isn't a valid URL." });
    expect(await validateVideoUrl("example.com/watch", resolveTo([]))).toEqual({ ok: false, code: "bad_url", message: "Include the https:// — e.g. https://www.youtube.com/watch?v=..." });
  });

  it("rejects non-http schemes", async () => {
    for (const s of ["javascript:alert(1)", "data:text/html,<script>", "file:///etc/passwd", "ftp://example.com/x", "vbscript:msgbox(1)"]) {
      expect(await validateVideoUrl(s, resolveTo([]))).toEqual({ ok: false, code: "bad_url", message: "Only http and https links are supported." });
    }
  });

  it("accepts a normal https URL", async () => {
    const r = await validateVideoUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ", resolveTo(["1.1.1.1"]));
    expect(r).toEqual({ ok: true, url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ" });
  });

  it("accepts http too", async () => {
    expect((await validateVideoUrl("http://example.com/clip.mp4", resolveTo(["8.8.8.8"]))).ok).toBe(true);
  });

  it("rejects loopback", async () => {
    const r = await validateVideoUrl("https://localhost/", resolveTo(["127.0.0.1"]));
    expect(r).toEqual({ ok: false, code: "blocked_url", message: "That link points at a private address." });
    expect((await validateVideoUrl("https://a/", resolveTo(["::1"]))).code).toBe("blocked_url");
  });

  it("rejects private and link-local IPv4", async () => {
    for (const ip of ["10.0.0.1", "192.168.1.1", "172.16.0.1", "172.31.255.255", "169.254.1.1", "0.0.0.1"]) {
      expect((await validateVideoUrl("https://a/", resolveTo([ip]))).code).toBe("blocked_url");
    }
  });

  it("rejects CGNAT and documentation ranges", async () => {
    for (const ip of ["100.64.0.1", "100.127.255.255", "198.18.0.1", "198.19.255.255"]) {
      expect((await validateVideoUrl("https://a/", resolveTo([ip]))).code).toBe("blocked_url");
    }
  });

  it("rejects multicast and broadcast", async () => {
    for (const ip of ["224.0.0.1", "239.255.255.255", "255.255.255.255"]) {
      expect((await validateVideoUrl("https://a/", resolveTo([ip]))).code).toBe("blocked_url");
    }
  });

  it("rejects IPv6 private, multicast and documentation", async () => {
    for (const ip of ["::1", "fe80::1", "fc00::1", "fd00::1", "ff00::1", "2001:db8::1", "2002::1"]) {
      expect((await validateVideoUrl("https://a/", resolveTo([ip]))).code).toBe("blocked_url");
    }
  });

  it("allows normal 2001:: addresses (only 2001:db8::/32 is documentation)", async () => {
    expect((await validateVideoUrl("https://a/", resolveTo(["2001:4860:4860::8888"]))).ok).toBe(true);
  });

  it("rejects IPv4-mapped IPv6 that folds back to loopback", async () => {
    expect((await validateVideoUrl("https://a/", resolveTo(["::ffff:127.0.0.1"]))).code).toBe("blocked_url");
    expect((await validateVideoUrl("https://a/", resolveTo(["::ffff:192.168.0.1"]))).code).toBe("blocked_url");
  });

  it("rejects a host that resolves to nothing", async () => {
    expect((await validateVideoUrl("https://nonexistent.invalid/", resolveTo([]))).code).toBe("blocked_url");
  });

  it("rejects a host that resolves to a mix — the downloader may pick any address", async () => {
    expect((await validateVideoUrl("https://a/", resolveTo(["127.0.0.1", "1.2.3.4"]))).code).toBe("blocked_url");
  });

  it("passes public IPv6", async () => {
    expect((await validateVideoUrl("https://a/", resolveTo(["2606:4700:4700::1111"]))).ok).toBe(true);
  });
});

describe("redactUrl", () => {
  it("drops query and fragment", () => {
    expect(redactUrl("https://www.youtube.com/watch?v=abc&t=10s#section")).toBe("https://www.youtube.com/watch");
  });
  it("handles malformed input", () => {
    expect(redactUrl("garbage")).toBe("[url]");
  });
});