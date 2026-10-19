/**
 * Turn an API error into a message a user can act on.
 *
 * FastAPI returns `{"detail": "..."}` for handled errors and
 * `{"detail": [{"loc": [...], "msg": "..."}]}` for validation errors.
 */

interface ValidationIssue {
  loc?: (string | number)[];
  msg?: string;
}

interface ErrorShape {
  response?: { status?: number; data?: { detail?: unknown } };
}

export function apiErrorMessage(error: unknown, fallback: string): string {
  const response = (error as ErrorShape | null)?.response;
  if (!response) return fallback;

  if (response.status === 429) return "Too many attempts. Please wait a minute and try again.";

  const detail = response.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as ValidationIssue;
    const field = first.loc?.filter((part) => part !== "body").join(".");
    if (first.msg) {
      // "Value error, ..." is pydantic's prefix for custom validator messages.
      const msg = first.msg.replace(/^Value error, /, "");
      return field ? `${humanise(String(field))}: ${msg}` : msg;
    }
  }
  return fallback;
}

function humanise(field: string): string {
  const text = field.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}
