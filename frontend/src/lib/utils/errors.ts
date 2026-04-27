import { AxiosError } from "axios";

export interface APIError {
  message: string;
  detail?: string | Record<string, unknown>;
  status?: number;
}

/** Normalise any thrown value into a displayable APIError. */
export function normaliseError(err: unknown): APIError {
  if (err instanceof AxiosError) {
    const status = err.response?.status;
    const data = err.response?.data as
      | { detail?: string | Record<string, unknown>; message?: string }
      | undefined;

    if (data?.detail) {
      const detail = data.detail;
      if (typeof detail === "string") {
        return { message: detail, status };
      }
      if (Array.isArray(detail)) {
        // FastAPI validation error array → join loc + msg
        const msg = (detail as Array<{ msg: string; loc?: string[] }>)
          .map((e) => `${e.loc?.join(".")} — ${e.msg}`)
          .join("; ");
        return { message: msg, detail, status };
      }
      return {
        message: "Validation error",
        detail: detail as Record<string, unknown>,
        status,
      };
    }

    if (data?.message) {
      return { message: data.message, status };
    }

    if (err.message) {
      return { message: err.message, status };
    }
  }

  if (err instanceof Error) {
    return { message: err.message };
  }

  return { message: "An unexpected error occurred." };
}
