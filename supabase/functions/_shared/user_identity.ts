export type UserTier = "free" | "paid";

type ResolveOrCreateUserIdArgs = {
  supabase: any;
  anonId?: string | null;
  licenseKeyHash?: string | null;
  userTier?: UserTier;
  occurredAt?: string | null;
  eventName?: string | null;
};

type IdentityMapRow = {
  user_id: string;
};

type UserRow = {
  user_id: string;
  is_premium: boolean;
  first_seen_free_at: string | null;
  first_seen_paid_at: string | null;
  purchase_timestamp: string | null;
};

function normalizeIso(value: string | null | undefined): string {
  if (!value) return new Date().toISOString();
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return new Date().toISOString();
  return new Date(parsed).toISOString();
}

function pickEarliest(existing: string | null | undefined, candidate: string | null | undefined): string | null {
  if (!existing && !candidate) return null;
  if (!existing) return candidate || null;
  if (!candidate) return existing;
  const existingTs = Date.parse(existing);
  const candidateTs = Date.parse(candidate);
  if (!Number.isFinite(existingTs)) return candidate;
  if (!Number.isFinite(candidateTs)) return existing;
  return candidateTs < existingTs ? candidate : existing;
}

function isMissingRowError(message: string | undefined): boolean {
  const text = (message || "").toLowerCase();
  return text.includes("no rows") || text.includes("pgrst116");
}

async function findIdentityMapping(
  supabase: any,
  identityType: "anon_id" | "license_key_hash",
  identityValue: string | null | undefined,
): Promise<IdentityMapRow | null> {
  if (!identityValue) return null;

  const { data, error } = await supabase
    .from("user_identity_map")
    .select("user_id")
    .eq("identity_type", identityType)
    .eq("identity_value", identityValue)
    .maybeSingle();

  if (error && !isMissingRowError(error.message)) {
    throw new Error(`identity lookup failed (${identityType}): ${error.message}`);
  }

  return (data || null) as IdentityMapRow | null;
}

async function loadUser(supabase: any, userId: string): Promise<UserRow | null> {
  const { data, error } = await supabase
    .from("users")
    .select("user_id,is_premium,first_seen_free_at,first_seen_paid_at,purchase_timestamp")
    .eq("user_id", userId)
    .maybeSingle();

  if (error && !isMissingRowError(error.message)) {
    throw new Error(`users lookup failed: ${error.message}`);
  }

  return (data || null) as UserRow | null;
}

async function saveUserLifecycle(args: {
  supabase: any;
  userId: string;
  existingUser: UserRow | null;
  userTier: UserTier;
  occurredAtIso: string;
  eventName?: string | null;
  hasLicenseIdentity: boolean;
}): Promise<void> {
  const { supabase, userId, existingUser, userTier, occurredAtIso, eventName, hasLicenseIdentity } = args;

  const freeCandidate = userTier === "free" ? occurredAtIso : null;
  const paidCandidate = userTier === "paid" ? occurredAtIso : null;
  const purchaseCandidate = eventName === "license_exchange_success" ? occurredAtIso : null;
  const nextIsPremium = Boolean(existingUser?.is_premium || hasLicenseIdentity || userTier === "paid");

  if (!existingUser) {
    const insertPayload = {
      user_id: userId,
      is_premium: nextIsPremium,
      first_seen_free_at: freeCandidate,
      first_seen_paid_at: paidCandidate,
      purchase_timestamp: purchaseCandidate,
    };

    const { error } = await supabase.from("users").insert(insertPayload);
    if (error) throw new Error(`users insert failed: ${error.message}`);
    return;
  }

  const updatePayload = {
    is_premium: nextIsPremium,
    first_seen_free_at: pickEarliest(existingUser.first_seen_free_at, freeCandidate),
    first_seen_paid_at: pickEarliest(existingUser.first_seen_paid_at, paidCandidate),
    purchase_timestamp: pickEarliest(existingUser.purchase_timestamp, purchaseCandidate),
  };

  const hasChanges =
    updatePayload.is_premium !== existingUser.is_premium ||
    updatePayload.first_seen_free_at !== existingUser.first_seen_free_at ||
    updatePayload.first_seen_paid_at !== existingUser.first_seen_paid_at ||
    updatePayload.purchase_timestamp !== existingUser.purchase_timestamp;

  if (!hasChanges) return;

  const { error } = await supabase
    .from("users")
    .update(updatePayload)
    .eq("user_id", userId);

  if (error) throw new Error(`users update failed: ${error.message}`);
}

async function upsertIdentityMappings(args: {
  supabase: any;
  userId: string;
  anonId?: string | null;
  licenseKeyHash?: string | null;
}): Promise<void> {
  const { supabase, userId, anonId, licenseKeyHash } = args;
  const mappings: Array<{ identity_type: "anon_id" | "license_key_hash"; identity_value: string; user_id: string }> = [];

  if (anonId) {
    mappings.push({ identity_type: "anon_id", identity_value: anonId, user_id: userId });
  }

  if (licenseKeyHash) {
    mappings.push({ identity_type: "license_key_hash", identity_value: licenseKeyHash, user_id: userId });
  }

  if (mappings.length === 0) return;

  const { error } = await supabase
    .from("user_identity_map")
    .upsert(mappings, { onConflict: "identity_type,identity_value" });

  if (error) throw new Error(`identity map upsert failed: ${error.message}`);
}

async function syncLicenseOwner(args: {
  supabase: any;
  userId: string;
  licenseKeyHash?: string | null;
}): Promise<void> {
  const { supabase, userId, licenseKeyHash } = args;
  if (!licenseKeyHash) return;

  const { error } = await supabase
    .from("licenses")
    .update({ user_id: userId })
    .eq("license_key_hash", licenseKeyHash);

  if (error) throw new Error(`licenses user_id update failed: ${error.message}`);
}

export async function resolveOrCreateUserId(args: ResolveOrCreateUserIdArgs): Promise<string> {
  const { supabase, anonId = null, licenseKeyHash = null } = args;
  const userTier: UserTier = args.userTier || (licenseKeyHash ? "paid" : "free");
  const occurredAtIso = normalizeIso(args.occurredAt);

  const [licenseMap, anonMap] = await Promise.all([
    findIdentityMapping(supabase, "license_key_hash", licenseKeyHash),
    findIdentityMapping(supabase, "anon_id", anonId),
  ]);

  // Paid mapping wins when available so free+paid activity stays unified after upgrade.
  const userId = licenseMap?.user_id || anonMap?.user_id || crypto.randomUUID();

  const existingUser = await loadUser(supabase, userId);
  await saveUserLifecycle({
    supabase,
    userId,
    existingUser,
    userTier,
    occurredAtIso,
    eventName: args.eventName,
    hasLicenseIdentity: Boolean(licenseKeyHash),
  });

  await upsertIdentityMappings({ supabase, userId, anonId, licenseKeyHash });
  await syncLicenseOwner({ supabase, userId, licenseKeyHash });

  return userId;
}
