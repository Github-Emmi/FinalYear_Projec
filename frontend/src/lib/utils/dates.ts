import { format, parseISO, formatDistanceToNow } from "date-fns";

/**
 * Strip trailing "Z" or timezone offset from an ISO string before sending
 * to the backend — the backend stores UTC-naive datetimes and rejects "Z".
 */
export function stripTimezone(isoStr: string): string {
  return isoStr.replace(/Z$/, "").replace(/[+-]\d{2}:\d{2}$/, "");
}

/**
 * Convert a Date object to a UTC-naive ISO string (no trailing Z).
 * Use this when serialising form date inputs to send to the API.
 */
export function toApiDatetime(date: Date): string {
  return stripTimezone(date.toISOString());
}

/** Format an ISO datetime string for display (e.g., "Jan 15, 2025 at 3:45 PM"). */
export function formatDisplay(isoStr: string): string {
  try {
    const d = isoStr.endsWith("Z") ? parseISO(isoStr) : parseISO(isoStr + "Z");
    return format(d, "MMM d, yyyy 'at' h:mm a");
  } catch {
    return isoStr;
  }
}

/** Format an ISO datetime string as a relative time (e.g., "2 hours ago"). */
export function formatRelative(isoStr: string): string {
  try {
    const d = isoStr.endsWith("Z") ? parseISO(isoStr) : parseISO(isoStr + "Z");
    return formatDistanceToNow(d, { addSuffix: true });
  } catch {
    return isoStr;
  }
}

/** Format only the date part (e.g., "Jan 15, 2025"). */
export function formatDate(isoStr: string): string {
  try {
    const d = parseISO(isoStr.split("T")[0]);
    return format(d, "MMM d, yyyy");
  } catch {
    return isoStr;
  }
}
