import { z } from "zod";

const questionTypes = ["mcq", "essay", "short_answer"] as const;

export const questionCreateSchema = z.object({
  question_text: z.string().min(1, "Question text is required"),
  question_type: z.enum(questionTypes),
  options: z.record(z.string()).optional(),
  correct_answer: z.string().optional(),
  marks: z.number().int().min(1).default(1),
  order: z.number().int().min(1).default(1),
});

export const quizCreateSchema = z.object({
  title: z.string().min(1, "Title is required").max(255),
  description: z.string().optional(),
  subject_id: z.string().uuid("Must be a valid subject"),
  time_limit_minutes: z
    .number()
    .int()
    .min(1)
    .max(300)
    .optional()
    .nullable(),
  max_attempts: z.number().int().min(1).max(10).default(1),
  is_published: z.boolean().default(false),
  questions: z.array(questionCreateSchema).optional(),
});

export type QuizCreateInput = z.infer<typeof quizCreateSchema>;
export type QuestionCreateInput = z.infer<typeof questionCreateSchema>;
