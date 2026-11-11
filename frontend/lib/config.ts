// Mock mode is ON unless NEXT_PUBLIC_USE_MOCK is explicitly "false" (see .env.example).
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";

export const MAX_UPLOAD_MB = 25;
