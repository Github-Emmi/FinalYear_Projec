import { z } from "zod";

export const leaveRequestSchema = z.object({
  leave_type: z.string().min(1, "Leave type is required"),
  start_date: z
    .string()
    .min(1, "Start date is required")
    .refine((d) => !isNaN(Date.parse(d)), { message: "Invalid start date" }),
  end_date: z
    .string()
    .min(1, "End date is required")
    .refine((d) => !isNaN(Date.parse(d)), { message: "Invalid end date" }),
  reason: z.string().min(10, "Please provide a reason (min 10 characters)"),
}).refine(
  (data) => new Date(data.end_date) >= new Date(data.start_date),
  {
    message: "End date must be on or after start date",
    path: ["end_date"],
  }
);

export type LeaveRequestInput = z.infer<typeof leaveRequestSchema>;
