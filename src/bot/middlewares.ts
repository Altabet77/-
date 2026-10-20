// Optional Telegram middlewares (Deprecated / Disabled)
import { env, isUserWhitelisted } from "../config/env.js";

export function checkAuth(userId: number): boolean {
  return isUserWhitelisted(userId);
}
