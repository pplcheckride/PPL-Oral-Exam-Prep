function base64UrlEncode(bytes: Uint8Array): string {
  const b64 = btoa(String.fromCharCode(...bytes));
  return b64.replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}

function base64UrlDecodeToBytes(input: string): Uint8Array {
  const b64 = input.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((input.length + 3) % 4);
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function hmacSha256(secret: string, data: string): Promise<Uint8Array> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(data));
  return new Uint8Array(sig);
}

export type LicenseJwtPayload = {
  license_key_hash: string;
  iat: number;
  exp: number;
};

export async function signLicenseJwt(args: {
  secret: string;
  licenseKeyHash: string;
  expiresInSeconds: number;
}): Promise<{ token: string; payload: LicenseJwtPayload }> {
  const now = Math.floor(Date.now() / 1000);
  const payload: LicenseJwtPayload = {
    license_key_hash: args.licenseKeyHash,
    iat: now,
    exp: now + args.expiresInSeconds,
  };

  const header = { alg: "HS256", typ: "JWT" };
  const headerPart = base64UrlEncode(new TextEncoder().encode(JSON.stringify(header)));
  const payloadPart = base64UrlEncode(new TextEncoder().encode(JSON.stringify(payload)));
  const signingInput = `${headerPart}.${payloadPart}`;
  const signature = await hmacSha256(args.secret, signingInput);
  const sigPart = base64UrlEncode(signature);
  return { token: `${signingInput}.${sigPart}`, payload };
}

export async function verifyLicenseJwt(args: { secret: string; token: string }): Promise<LicenseJwtPayload> {
  const parts = args.token.split(".");
  if (parts.length !== 3) throw new Error("Invalid token format");
  const [headerPart, payloadPart, sigPart] = parts;
  const signingInput = `${headerPart}.${payloadPart}`;
  const expectedSig = await hmacSha256(args.secret, signingInput);
  const actualSig = base64UrlDecodeToBytes(sigPart);

  if (expectedSig.length !== actualSig.length) throw new Error("Invalid signature");
  let diff = 0;
  for (let i = 0; i < expectedSig.length; i++) diff |= expectedSig[i] ^ actualSig[i];
  if (diff !== 0) throw new Error("Invalid signature");

  const payloadJson = new TextDecoder().decode(base64UrlDecodeToBytes(payloadPart));
  const payload = JSON.parse(payloadJson) as LicenseJwtPayload;
  if (!payload.license_key_hash || typeof payload.license_key_hash !== "string") throw new Error("Invalid payload");

  const now = Math.floor(Date.now() / 1000);
  if (typeof payload.exp !== "number" || payload.exp <= now) throw new Error("Token expired");
  return payload;
}

