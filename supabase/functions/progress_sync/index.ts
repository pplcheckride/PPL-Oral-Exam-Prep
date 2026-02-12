import { createClient } from "npm:@supabase/supabase-js@2";
import { corsHeaders, jsonResponse } from "../_shared/cors.ts";
import { requirePublishableKey } from "../_shared/api_key.ts";
import { verifyLicenseJwt } from "../_shared/jwt.ts";
import { resolveOrCreateUserId } from "../_shared/user_identity.ts";

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

type AppRating = "correct" | "unsure" | "wrong";
type LegacyRating = "mastered" | "review" | "practice";
type AnyRating = AppRating | LegacyRating;

function normalizeRating(value: unknown): AnyRating | null {
  if (typeof value !== "string") return null;
  const rating = value.trim().toLowerCase();
  if (rating === "correct" || rating === "unsure" || rating === "wrong") return rating;
  if (rating === "mastered" || rating === "review" || rating === "practice") return rating;
  return null;
}

function toAppRating(rating: AnyRating): AppRating {
  if (rating === "mastered") return "correct";
  if (rating === "review") return "unsure";
  if (rating === "practice") return "wrong";
  return rating;
}

function toLegacyRating(rating: AnyRating): LegacyRating {
  if (rating === "correct") return "mastered";
  if (rating === "unsure") return "review";
  if (rating === "wrong") return "practice";
  return rating;
}

function isRatingConstraintError(message: string | undefined): boolean {
  const m = (message || "").toLowerCase();
  return m.includes("user_progress_rating_check") || (m.includes("violates check constraint") && m.includes("rating"));
}

function isMissingConflictConstraintError(message: string | undefined): boolean {
  const m = (message || "").toLowerCase();
  return m.includes("no unique or exclusion constraint matching the on conflict specification");
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
    const userId = await resolveOrCreateUserId({
      supabase,
      licenseKeyHash,
      userTier: "paid",
      occurredAt: new Date().toISOString(),
    });

    if (req.method === "GET") {
      let { data, error } = await supabase
        .from("user_progress")
        .select("question_id,rating,attempts,updated_at")
        .eq("user_id", userId);

      if (error) return jsonResponse({ error: error.message }, { status: 500 });

      if (!Array.isArray(data) || data.length === 0) {
        const legacy = await supabase
          .from("user_progress")
          .select("question_id,rating,attempts,updated_at")
          .eq("license_key_hash", licenseKeyHash);

        if (legacy.error) return jsonResponse({ error: legacy.error.message }, { status: 500 });
        data = legacy.data ?? [];

        await supabase
          .from("user_progress")
          .update({ user_id: userId })
          .eq("license_key_hash", licenseKeyHash)
          .is("user_id", null);
      }

      const normalized = (data ?? []).map((row: any) => {
        const parsed = normalizeRating(row?.rating);
        return {
          ...row,
          rating: parsed ? toAppRating(parsed) : row?.rating,
        };
      });
      return jsonResponse(normalized);
    }

    if (req.method === "POST") {
      const body = await req.json().catch(() => ({}));
      const rows = Array.isArray(body?.progress) ? body.progress : [];

      const upserts = rows
        .map((r: any) => {
          if (!r || typeof r.question_id !== "string") return null;
          const parsed = normalizeRating(r.rating);
          if (!parsed) return null;
          return {
            user_id: userId,
            license_key_hash: licenseKeyHash,
            question_id: r.question_id,
            rating: toAppRating(parsed),
            attempts: typeof r.attempts === "number" ? r.attempts : 0,
            updated_at: r.updated_at ?? undefined,
          };
        })
        .filter(Boolean);

      if (upserts.length === 0) return jsonResponse({ ok: true, upserted: 0 });

      let conflictKey = "user_id,question_id";
      let firstAttempt = await supabase
        .from("user_progress")
        .upsert(upserts as any[], { onConflict: conflictKey });

      if (firstAttempt.error && isMissingConflictConstraintError(firstAttempt.error.message)) {
        conflictKey = "license_key_hash,question_id";
        firstAttempt = await supabase
          .from("user_progress")
          .upsert(upserts as any[], { onConflict: conflictKey });
      }

      if (!firstAttempt.error) {
        return jsonResponse({ ok: true, upserted: upserts.length, schemaMode: "app", conflictKey });
      }

      if (!isRatingConstraintError(firstAttempt.error.message)) {
        return jsonResponse({ error: firstAttempt.error.message }, { status: 500 });
      }

      const legacyUpserts = (upserts as any[]).map((row) => ({
        ...row,
        rating: toLegacyRating(row.rating),
      }));

      let legacyAttempt = await supabase
        .from("user_progress")
        .upsert(legacyUpserts, { onConflict: conflictKey });

      if (legacyAttempt.error && isMissingConflictConstraintError(legacyAttempt.error.message) && conflictKey !== "license_key_hash,question_id") {
        conflictKey = "license_key_hash,question_id";
        legacyAttempt = await supabase
          .from("user_progress")
          .upsert(legacyUpserts, { onConflict: conflictKey });
      }

      if (legacyAttempt.error) {
        return jsonResponse({
          error: legacyAttempt.error.message,
          firstError: firstAttempt.error.message,
        }, { status: 500 });
      }

      return jsonResponse({ ok: true, upserted: upserts.length, schemaMode: "legacy", conflictKey });
    }

    return jsonResponse({ error: "Method not allowed" }, { status: 405 });
  } catch (e) {
    const msg = (e as Error).message || "Unknown error";
    const status = msg.toLowerCase().includes("token") ? 401 : 500;
    return jsonResponse({ error: msg }, { status });
  }
});
