import { createClient } from "npm:@supabase/supabase-js@2";
import { corsHeaders, jsonResponse } from "../_shared/cors.ts";
import { verifyLicenseJwt } from "../_shared/jwt.ts";

const MAX_EVENTS_PER_REQUEST = 50;
const MAX_CONTENT_LENGTH_BYTES = 256_000;
const MAX_JSON_BYTES = 4096;
const MAX_ID_LENGTH = 128;
const MAX_LABEL_LENGTH = 64;
const MAX_SCENARIO_ID_LENGTH = 32;

const ALLOWED_EVENT_NAMES = new Set<string>([
  "app_loaded",
  "landing_viewed",
  "start_studying_clicked",
  "onboarding_shown",
  "onboarding_completed",
  "mode_started",
  "scenario_viewed",
  "scenario_answer_revealed",
  "scenario_rated",
  "reference_clicked",
  "review_empty_state_seen",
  "insights_opened",
  "mock_started",
  "mock_completed",
  "mock_exited_early",
  "mock_history_viewed",
  "upgrade_modal_viewed",
  "upgrade_cta_clicked",
  "license_exchange_success",
  "license_exchange_failed",
  "sync_completed",
  "reset_progress_confirmed",
]);

const SENSITIVE_KEYS = new Set<string>([
  "licensekey",
  "license_key",
  "raw_license_key",
  "email",
  "phone",
  "full_name",
  "name",
  "answer_text",
  "raw_answer",
  "scenario_text",
]);

type EventTier = "free" | "paid";

type ValidationError = {
  index: number;
  message: string;
};

type AnalyticsInsert = {
  event_id: string;
  event_name: string;
  occurred_at: string;
  anon_id: string;
  session_id: string;
  user_tier: EventTier;
  license_key_hash: string | null;
  app_version: string | null;
  page_name: string | null;
  mode_name: string | null;
  scenario_id: string | null;
  properties: Record<string, unknown>;
  context: Record<string, unknown>;
};

function getEnv(name: string): string {
  const value = Deno.env.get(name);
  if (!value) throw new Error(`Missing env var: ${name}`);
  return value;
}

function bearerToken(req: Request): string | null {
  const header = req.headers.get("authorization") || req.headers.get("Authorization");
  if (!header) return null;
  const match = header.match(/^Bearer\s+(.+)$/i);
  return match ? match[1] : null;
}

function asRecord(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return value as Record<string, unknown>;
}

function clampString(value: unknown, maxLen: number): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  return trimmed.slice(0, maxLen);
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

function isValidIsoTimestamp(value: string): boolean {
  const ts = Date.parse(value);
  return Number.isFinite(ts);
}

function sanitizeJsonValue(value: unknown, depth = 0): unknown {
  if (depth > 4) return null;

  if (value == null) return null;
  if (typeof value === "number" || typeof value === "boolean") return value;
  if (typeof value === "string") return value.slice(0, 500);

  if (Array.isArray(value)) {
    return value.slice(0, 25).map((item) => sanitizeJsonValue(item, depth + 1));
  }

  if (typeof value === "object") {
    const output: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(value as Record<string, unknown>)) {
      if (SENSITIVE_KEYS.has(key.toLowerCase())) continue;
      output[key] = sanitizeJsonValue(val, depth + 1);
    }
    return output;
  }

  return null;
}

function sanitizeJsonObject(value: unknown, index: number, fieldName: string, errors: ValidationError[]): Record<string, unknown> {
  const inputObj = asRecord(value);
  const sanitized = sanitizeJsonValue(inputObj, 0);
  const safeObj = asRecord(sanitized);

  try {
    const bytes = new TextEncoder().encode(JSON.stringify(safeObj)).length;
    if (bytes > MAX_JSON_BYTES) {
      errors.push({ index, message: `${fieldName} exceeds ${MAX_JSON_BYTES} bytes` });
      return {};
    }
  } catch {
    errors.push({ index, message: `${fieldName} is not serializable` });
    return {};
  }

  return safeObj;
}

function sanitizeEvent(args: {
  rawEvent: unknown;
  index: number;
  userTier: EventTier;
  licenseKeyHash: string | null;
  errors: ValidationError[];
}): AnalyticsInsert | null {
  const { rawEvent, index, userTier, licenseKeyHash, errors } = args;
  const ev = asRecord(rawEvent);

  const eventId = clampString(ev.event_id, MAX_ID_LENGTH);
  if (!eventId || !isUuid(eventId)) {
    errors.push({ index, message: "event_id is required and must be a UUID" });
    return null;
  }

  const eventName = clampString(ev.event_name, MAX_LABEL_LENGTH);
  if (!eventName || !ALLOWED_EVENT_NAMES.has(eventName)) {
    errors.push({ index, message: `event_name is invalid: ${String(ev.event_name ?? "")}` });
    return null;
  }

  const occurredAt = clampString(ev.occurred_at, MAX_ID_LENGTH);
  if (!occurredAt || !isValidIsoTimestamp(occurredAt)) {
    errors.push({ index, message: "occurred_at must be a valid ISO timestamp" });
    return null;
  }

  const anonId = clampString(ev.anon_id, MAX_ID_LENGTH);
  if (!anonId) {
    errors.push({ index, message: "anon_id is required" });
    return null;
  }

  const sessionId = clampString(ev.session_id, MAX_ID_LENGTH);
  if (!sessionId) {
    errors.push({ index, message: "session_id is required" });
    return null;
  }

  const contextInput = asRecord(ev.context);
  const properties = sanitizeJsonObject(ev.properties, index, "properties", errors);
  const context = sanitizeJsonObject(contextInput, index, "context", errors);

  const tierHint = clampString((contextInput.tier_hint ?? ev.tier_hint), 16);
  if (tierHint) context.tier_hint = tierHint;
  context.server_tier = userTier;

  const appVersion = clampString(ev.app_version ?? contextInput.app_version, MAX_LABEL_LENGTH);
  const pageName = clampString(ev.page_name, MAX_LABEL_LENGTH);
  const modeName = clampString(ev.mode_name, MAX_LABEL_LENGTH);
  const scenarioId = clampString(ev.scenario_id, MAX_SCENARIO_ID_LENGTH);

  return {
    event_id: eventId,
    event_name: eventName,
    occurred_at: new Date(occurredAt).toISOString(),
    anon_id: anonId,
    session_id: sessionId,
    user_tier: userTier,
    license_key_hash: userTier === "paid" ? licenseKeyHash : null,
    app_version: appVersion,
    page_name: pageName,
    mode_name: modeName,
    scenario_id: scenarioId,
    properties,
    context,
  };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return jsonResponse({ error: "Method not allowed" }, { status: 405 });

  const contentLength = Number(req.headers.get("content-length") || "0");
  if (Number.isFinite(contentLength) && contentLength > MAX_CONTENT_LENGTH_BYTES) {
    return jsonResponse({ error: `Payload too large (max ${MAX_CONTENT_LENGTH_BYTES} bytes)` }, { status: 413 });
  }

  try {
    const supabaseUrl = getEnv("SUPABASE_URL");
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || Deno.env.get("SERVICE_ROLE_KEY");
    if (!serviceKey) throw new Error("Missing service role key env var (SUPABASE_SERVICE_ROLE_KEY)");

    const token = bearerToken(req);
    const jwtSecret = Deno.env.get("LICENSE_JWT_SECRET");
    let userTier: EventTier = "free";
    let licenseKeyHash: string | null = null;

    if (token && jwtSecret) {
      try {
        const payload = await verifyLicenseJwt({ secret: jwtSecret, token });
        if (payload?.license_key_hash) {
          userTier = "paid";
          licenseKeyHash = payload.license_key_hash;
        }
      } catch {
        userTier = "free";
        licenseKeyHash = null;
      }
    }

    const body = await req.json().catch(() => ({}));
    const rawEvents = Array.isArray(body?.events) ? body.events : null;
    if (!rawEvents) {
      return jsonResponse({ error: "Body must include an events array" }, { status: 400 });
    }

    if (rawEvents.length > MAX_EVENTS_PER_REQUEST) {
      return jsonResponse({
        error: `Maximum ${MAX_EVENTS_PER_REQUEST} events per request`,
      }, { status: 400 });
    }

    const errors: ValidationError[] = [];
    const rows: AnalyticsInsert[] = [];

    rawEvents.forEach((rawEvent, index) => {
      const row = sanitizeEvent({ rawEvent, index, userTier, licenseKeyHash, errors });
      if (row) rows.push(row);
    });

    if (rows.length > 0) {
      const supabase = createClient(supabaseUrl, serviceKey, { auth: { persistSession: false } });
      const { error } = await supabase
        .from("analytics_events")
        .upsert(rows, { onConflict: "event_id", ignoreDuplicates: true });

      if (error) {
        return jsonResponse({ error: error.message }, { status: 500 });
      }
    }

    const response = {
      accepted: rows.length,
      rejected: errors.length,
      errors,
    };

    if (rows.length === 0 && errors.length > 0) {
      return jsonResponse(response, { status: 400 });
    }

    return jsonResponse(response);
  } catch (error) {
    return jsonResponse({ error: (error as Error).message || "Unknown error" }, { status: 500 });
  }
});
