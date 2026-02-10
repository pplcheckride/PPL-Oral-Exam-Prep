function getHeader(req: Request, name: string): string | null {
  // Headers are case-insensitive but the API is not; normalize by checking common variants.
  return req.headers.get(name) || req.headers.get(name.toLowerCase()) || req.headers.get(name.toUpperCase());
}

export function requirePublishableKey(req: Request): { ok: true } | { ok: false; error: string } {
  const expected =
    Deno.env.get("SUPABASE_ANON_KEY") ||
    Deno.env.get("SUPABASE_PUBLISHABLE_KEY") ||
    Deno.env.get("PUBLISHABLE_KEY");

  // If no expected key is configured, skip the check (useful for local dev).
  if (!expected) return { ok: true };

  const provided = getHeader(req, "apikey") || getHeader(req, "x-supabase-anon-key");
  if (!provided) return { ok: false, error: "Missing apikey header" };
  if (provided !== expected) return { ok: false, error: "Invalid apikey" };
  return { ok: true };
}

