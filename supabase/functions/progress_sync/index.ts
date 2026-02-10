import { createClient } from "npm:@supabase/supabase-js@2";
import { corsHeaders, jsonResponse } from "../_shared/cors.ts";
import { requirePublishableKey } from "../_shared/api_key.ts";
import { verifyLicenseJwt } from "../_shared/jwt.ts";

function getEnv(name: string): string {
  const v = Deno.env.get(name);
  if (!v) throw new Error(`Missing env var: ${name}`);
  return v;
}

function bearerToken(req: Request): string | null {
  const h = req.headers.get("authorization") || req.headers.get("Authorization");
  if (!h) return null;
  const m = h.match(/^Bearer\s+(.+)$/i);
  return m ? m[1] : null;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  const keyCheck = requirePublishableKey(req);
  if (!keyCheck.ok) return jsonResponse({ error: keyCheck.error }, { status: 401 });

  const token = bearerToken(req);
  if (!token) return jsonResponse({ error: "Missing Authorization" }, { status: 401 });

  try {
    const supabaseUrl = getEnv("SUPABASE_URL");
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || Deno.env.get("SERVICE_ROLE_KEY");
    if (!serviceKey) throw new Error("Missing service role key env var (SUPABASE_SERVICE_ROLE_KEY)");
    const jwtSecret = getEnv("LICENSE_JWT_SECRET");

    const payload = await verifyLicenseJwt({ secret: jwtSecret, token });
    const licenseKeyHash = payload.license_key_hash;

    const supabase = createClient(supabaseUrl, serviceKey, { auth: { persistSession: false } });

    if (req.method === "GET") {
      const { data, error } = await supabase
        .from("user_progress")
        .select("question_id,rating,attempts,updated_at")
        .eq("license_key_hash", licenseKeyHash);
      if (error) return jsonResponse({ error: error.message }, { status: 500 });
      return jsonResponse(data ?? []);
    }

    if (req.method === "POST") {
      const body = await req.json().catch(() => ({}));
      const rows = Array.isArray(body?.progress) ? body.progress : [];

      const upserts = rows
        .filter((r: any) => r && typeof r.question_id === "string" && typeof r.rating === "string")
        .map((r: any) => ({
          license_key_hash: licenseKeyHash,
          question_id: r.question_id,
          rating: r.rating,
          attempts: typeof r.attempts === "number" ? r.attempts : 0,
          updated_at: r.updated_at ?? undefined,
        }));

      if (upserts.length === 0) return jsonResponse({ ok: true, upserted: 0 });

      const { error } = await supabase
        .from("user_progress")
        .upsert(upserts, { onConflict: "license_key_hash,question_id" });
      if (error) return jsonResponse({ error: error.message }, { status: 500 });

      return jsonResponse({ ok: true, upserted: upserts.length });
    }

    return jsonResponse({ error: "Method not allowed" }, { status: 405 });
  } catch (e) {
    const msg = (e as Error).message || "Unknown error";
    const status = msg.toLowerCase().includes("token") ? 401 : 500;
    return jsonResponse({ error: msg }, { status });
  }
});
