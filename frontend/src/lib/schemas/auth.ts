import { z } from "zod";

/**
 * Auth request/response schemas — the frontend validates forms with these
 * before sending. They match the backend's Pydantic rules in
 * backend/app/modules/auth/schemas.py (keep the two in step).
 */

const email = z
  .string()
  .trim()
  .toLowerCase()
  .pipe(z.email({ message: "Enter a valid email address" }))
  .refine((value) => value.length <= 254, "Email is too long");

// 8–128 chars: long enough to resist guessing, capped so hashing cost stays bounded.
const password = z
  .string()
  .min(8, "Password must be at least 8 characters")
  .max(128, "Password must be at most 128 characters");

export const signUpBody = z.object({
  name: z.string().trim().min(1, "Name is required").max(100, "Name is too long"),
  email,
  password,
});
export type SignUpBody = z.infer<typeof signUpBody>;

export const signInBody = z.object({
  email,
  // No length rules on sign-in: never tell an attacker which passwords are "possible".
  password: z.string().min(1, "Password is required").max(128),
});
export type SignInBody = z.infer<typeof signInBody>;

export const authUser = z.object({
  id: z.uuid(),
  name: z.string(),
  email: z.string(),
  isOnboarded: z.boolean(),
});
export type AuthUser = z.infer<typeof authUser>;

export const authSession = z.object({
  token: z.string(),
  expiresAt: z.iso.datetime(),
  user: authUser,
});
export type AuthSession = z.infer<typeof authSession>;
