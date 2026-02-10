import { createClient } from "npm:@supabase/supabase-js@2";
import { corsHeaders, jsonResponse } from "../_shared/cors.ts";
import { requirePublishableKey } from "../_shared/api_key.ts";
import { sha256Hex } from "../_shared/sha256.ts";
import { signLicenseJwt } from "../_shared/jwt.ts";

function getEnv(name: string): string {
  const v = Deno.env.get(name);
  if (!v) throw new Error(`Missing env var: ${name}`);
  return v;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return jsonResponse({ error: "Method not allowed" }, { status: 405 });

  try {
    const keyCheck = requirePublishableKey(req);
    if (!keyCheck.ok) return jsonResponse({ error: keyCheck.error }, { status: 401 });

    const { licenseKey } = await req.json();
    if (!licenseKey || typeof licenseKey !== "string") {
      return jsonResponse({ error: "licenseKey is required" }, { status: 400 });
    }

    const supabaseUrl = getEnv("SUPABASE_URL");
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || Deno.env.get("SERVICE_ROLE_KEY");
    if (!serviceKey) throw new Error("Missing service role key env var (SUPABASE_SERVICE_ROLE_KEY)");

    const jwtSecret = Deno.env.get("LICENSE_JWT_SECRET");
    if (!jwtSecret) throw new Error("Missing LICENSE_JWT_SECRET");

    const supabase = createClient(supabaseUrl, serviceKey, { auth: { persistSession: false } });
    const licenseKeyHash = await sha256Hex(licenseKey.trim());

    const { data, error } = await supabase
      .from("licenses")
      .select("license_key_hash,status")
      .eq("license_key_hash", licenseKeyHash)
      .maybeSingle();

    if (error) return jsonResponse({ error: error.message }, { status: 500 });
    if (!data || data.status !== "active") return jsonResponse({ error: "Invalid license" }, { status: 401 });

    const sevenDays = 7 * 24 * 60 * 60;
    const { token, payload } = await signLicenseJwt({
      secret: jwtSecret,
      licenseKeyHash,
      expiresInSeconds: sevenDays,
    });

    return jsonResponse({
      token,
      licenseKeyHash,
      expiresAt: new Date(payload.exp * 1000).toISOString(),
    });
  } catch (e) {
    return jsonResponse({ error: (e as Error).message || "Unknown error" }, { status: 500 });
  }
});
