import { z } from "zod";

export const studentCreateSchema = z.object({
  username: z.string().min(3, "Username must be at least 3 characters"),
  email: z.string().email("Invalid email address"),
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  student_id: z.string().min(1, "Student ID is required"),
  classroom_id: z.string().uuid("Must be a valid classroom"),
  session_year_id: z.string().uuid("Must be a valid session year"),
  date_of_birth: z.string().optional().nullable(),
  gender: z.enum(["male", "female", "other"]).optional().nullable(),
  phone: z.string().optional().nullable(),
  address: z.string().optional().nullable(),
  guardian_name: z.string().optional().nullable(),
  guardian_phone: z.string().optional().nullable(),
});

export type StudentCreateInput = z.infer<typeof studentCreateSchema>;
