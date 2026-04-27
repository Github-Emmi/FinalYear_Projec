import { z } from "zod";
import { toApiDatetime } from "@/lib/utils/dates";

export const assignmentCreateSchema = z.object({
  title: z.string().min(1, "Title is required").max(255),
  description: z.string().optional(),
  subject_id: z.string().uuid("Must be a valid subject"),
  due_date: z.coerce
    .date({ errorMap: () => ({ message: "Invalid due date" }) })
    .refine((d) => d > new Date(), { message: "Due date must be in the future" })
    .transform((d) => toApiDatetime(d)),
  max_score: z
    .number({ invalid_type_error: "Max score must be a number" })
    .int()
    .min(1)
    .max(1000)
    .default(100),
  allow_late: z.boolean().default(false),
});

export type AssignmentCreateInput = z.infer<typeof assignmentCreateSchema>;

export const submissionCreateSchema = z.object({
  content: z.string().min(1, "Submission content is required"),
});

export type SubmissionCreateInput = z.infer<typeof submissionCreateSchema>;
