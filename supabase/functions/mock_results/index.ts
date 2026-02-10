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
      const url = new URL(req.url);
      const limit = Math.min(Number(url.searchParams.get("limit") || "10") || 10, 50);
      const { data, error } = await supabase
        .from("mock_checkride_results")
        .select("id,score,total_questions,passed,time_spent_seconds,questions_attempted,completed_at")
        .eq("license_key_hash", licenseKeyHash)
        .order("completed_at", { ascending: false })
        .limit(limit);
      if (error) return jsonResponse({ error: error.message }, { status: 500 });
      return jsonResponse(data ?? []);
    }

    if (req.method === "POST") {
      const body = await req.json().catch(() => ({}));
      const score = Number(body?.score);
      const totalQuestions = Number(body?.total_questions);
      const passed = Boolean(body?.passed);
      const timeSpent = body?.time_spent_seconds == null ? null : Number(body.time_spent_seconds);
      const questionsAttempted = body?.questions_attempted ?? null;

      if (!Number.isFinite(score) || !Number.isFinite(totalQuestions)) {
        return jsonResponse({ error: "score and total_questions are required" }, { status: 400 });
      }

      const { error } = await supabase.from("mock_checkride_results").insert({
        license_key_hash: licenseKeyHash,
        score,
        total_questions: totalQuestions,
        passed,
        time_spent_seconds: Number.isFinite(timeSpent as number) ? timeSpent : null,
        questions_attempted: questionsAttempted,
      });
      if (error) return jsonResponse({ error: error.message }, { status: 500 });
      return jsonResponse({ ok: true });
    }

    return jsonResponse({ error: "Method not allowed" }, { status: 405 });
  } catch (e) {
    const msg = (e as Error).message || "Unknown error";
    const status = msg.toLowerCase().includes("token") ? 401 : 500;
    return jsonResponse({ error: msg }, { status });
  }
});
