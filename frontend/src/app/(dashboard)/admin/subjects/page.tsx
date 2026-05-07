"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookOpen,
  Plus,
  Pencil,
  Trash2,
  X,
  Loader2,
  UserCircle,
  Search,
  School,
} from "lucide-react";
import { toast } from "sonner";
import { queryKeys } from "@/lib/query/keys";
import {
  listSubjects,
  listClassrooms,
  createSubject,
  updateSubject,
  deleteSubject,
} from "@/lib/api/academic";
import { listStaff } from "@/lib/api/staff";
import { AuthGuard } from "@/components/auth/AuthGuard";
import type { SubjectResponse, ClassRoomResponse, StaffProfileResponse } from "@/types/models";

// ── Helpers ───────────────────────────────────────────────────────────────────

function staffLabel(s: StaffProfileResponse) {
  return s.user ? `${s.user.first_name} ${s.user.last_name}` : s.id;
}

// ── Subject Form Modal ────────────────────────────────────────────────────────

interface SubjectFormValues {
  name: string;
  classroom_id: string;
  staff_id: string;
}

function SubjectModal({
  mode,
  initial,
  classrooms,
  staff,
  onClose,
}: {
  mode: "create" | "edit";
  initial?: SubjectResponse;
  classrooms: ClassRoomResponse[];
  staff: StaffProfileResponse[];
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState<SubjectFormValues>({
    name: initial?.name ?? "",
    classroom_id: initial?.classroom_id ?? classrooms[0]?.id ?? "",
    staff_id: initial?.staff_id ?? "",
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: form.name.trim(),
        classroom_id: form.classroom_id,
        staff_id: form.staff_id || null,
      };
      return mode === "create"
        ? createSubject(payload)
        : updateSubject(initial!.id, payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["academic", "subjects"] });
      qc.invalidateQueries({ queryKey: queryKeys.analytics.platform() });
      toast.success(mode === "create" ? "Subject created" : "Subject updated");
      onClose();
    },
    onError: () => toast.error(mode === "create" ? "Failed to create subject" : "Failed to update subject"),
  });

  const isValid = form.name.trim().length > 0 && form.classroom_id.length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.15 }}
        className="relative w-full max-w-md rounded-2xl border border-border bg-card shadow-xl mx-4"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-primary" />
            <h2 className="font-semibold text-foreground">
              {mode === "create" ? "New Subject" : "Edit Subject"}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 hover:bg-muted transition-colors text-muted-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-4 px-5 py-5">
          {/* Name */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">
              Subject Name <span className="text-destructive">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. Mathematics"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>

          {/* Classroom */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">
              Classroom <span className="text-destructive">*</span>
            </label>
            <select
              value={form.classroom_id}
              onChange={(e) => setForm((f) => ({ ...f, classroom_id: e.target.value }))}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              {classrooms.length === 0 && (
                <option value="">No classrooms — add one under Academic first</option>
              )}
              {classrooms.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                  {c.grade_level != null ? ` — Grade ${c.grade_level}` : ""}
                  {c.section ? ` ${c.section}` : ""}
                </option>
              ))}
            </select>
          </div>

          {/* Assign Staff */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground flex items-center gap-1.5">
              <UserCircle className="h-4 w-4 text-muted-foreground" />
              Assign Staff
              <span className="text-xs text-muted-foreground font-normal">(optional)</span>
            </label>
            <select
              value={form.staff_id}
              onChange={(e) => setForm((f) => ({ ...f, staff_id: e.target.value }))}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              <option value="">— Unassigned —</option>
              {staff.map((s) => (
                <option key={s.id} value={s.id}>
                  {staffLabel(s)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 border-t border-border px-5 py-4">
          <button
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            disabled={!isValid || mutation.isPending}
            onClick={() => mutation.mutate()}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {mutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : mode === "create" ? (
              <Plus className="h-4 w-4" />
            ) : (
              <Pencil className="h-4 w-4" />
            )}
            {mode === "create" ? "Create" : "Save"}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

// ── Delete Confirm Modal ──────────────────────────────────────────────────────

function DeleteConfirmModal({
  subject,
  onClose,
}: {
  subject: SubjectResponse;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => deleteSubject(subject.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["academic", "subjects"] });
      qc.invalidateQueries({ queryKey: queryKeys.analytics.platform() });
      toast.success("Subject deleted");
      onClose();
    },
    onError: () => toast.error("Failed to delete subject"),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.15 }}
        className="relative w-full max-w-sm rounded-2xl border border-border bg-card shadow-xl mx-4 p-6"
      >
        <div className="flex items-center gap-3 mb-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-destructive/15">
            <Trash2 className="h-5 w-5 text-destructive" />
          </div>
          <h2 className="font-semibold text-foreground">Delete Subject</h2>
        </div>
        <p className="text-sm text-muted-foreground mb-6">
          Are you sure you want to delete{" "}
          <span className="font-medium text-foreground">{subject.name}</span>?
          This action cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
            className="inline-flex items-center gap-1.5 rounded-lg bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            Delete
          </button>
        </div>
      </motion.div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Modal =
  | { type: "create" }
  | { type: "edit"; subject: SubjectResponse }
  | { type: "delete"; subject: SubjectResponse }
  | null;

export default function AdminSubjectsPage() {
  const [modal, setModal] = useState<Modal>(null);
  const [search, setSearch] = useState("");

  const { data: subjectsData, isLoading: loadingSubjects } = useQuery({
    queryKey: queryKeys.academic.subjects({ size: 100 }),
    queryFn: () => listSubjects({ size: 100 }),
  });

  const { data: classroomsData, isLoading: loadingClassrooms } = useQuery({
    queryKey: queryKeys.academic.classrooms({ size: 100 }),
    queryFn: () => listClassrooms({ size: 100 }),
  });

  const { data: staffData, isLoading: loadingStaff } = useQuery({
    queryKey: queryKeys.staff.all({ size: 100 }),
    queryFn: () => listStaff({ size: 100 }),
  });

  const isLoading = loadingSubjects || loadingClassrooms || loadingStaff;

  const subjects = subjectsData ?? [];
  const classrooms = classroomsData?.items ?? [];
  const staff = staffData?.items ?? [];

  const filtered = search.trim()
    ? subjects.filter((s) =>
        s.name.toLowerCase().includes(search.toLowerCase()) ||
        (s.staff?.first_name?.toLowerCase().includes(search.toLowerCase())) ||
        (s.staff?.last_name?.toLowerCase().includes(search.toLowerCase()))
      )
    : subjects;

  return (
    <AuthGuard allowedRoles={["admin"]}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Subjects</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Create, assign, and manage all subjects
            </p>
          </div>
          <button
            onClick={() => setModal({ type: "create" })}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Plus className="h-4 w-4" />
            New Subject
          </button>
        </div>

        {/* Search bar */}
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            placeholder="Search subjects or staff…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-border bg-card pl-9 pr-4 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>

        {/* Table */}
        <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
          {/* Table header */}
          <div className="grid grid-cols-[1fr_1fr_1.5fr_auto] gap-4 border-b border-border bg-muted/40 px-5 py-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <span>Subject</span>
            <span>Classroom</span>
            <span>Assigned Staff</span>
            <span className="text-right">Actions</span>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-muted">
                <BookOpen className="h-6 w-6 text-muted-foreground" />
              </div>
              <p className="font-medium text-foreground">
                {search ? "No subjects match your search" : "No subjects yet"}
              </p>
              {!search && (
                <p className="text-sm text-muted-foreground">
                  Click{" "}
                  <button
                    onClick={() => setModal({ type: "create" })}
                    className="font-medium text-primary hover:underline"
                  >
                    New Subject
                  </button>{" "}
                  to get started.
                </p>
              )}
            </div>
          ) : (
            <div className="divide-y divide-border">
              <AnimatePresence initial={false}>
                {filtered.map((sub, i) => (
                  <motion.div
                    key={sub.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="grid grid-cols-[1fr_1fr_1.5fr_auto] gap-4 items-center px-5 py-3.5 hover:bg-muted/30 transition-colors"
                  >
                    {/* Subject name */}
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-500/15">
                        <BookOpen className="h-4 w-4 text-violet-500" />
                      </div>
                      <span className="truncate text-sm font-medium text-foreground">
                        {sub.name}
                      </span>
                    </div>

                    {/* Classroom */}
                    <div className="flex items-center gap-1.5 min-w-0">
                      <School className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      <span className="truncate text-sm text-muted-foreground">
                        {sub.classroom?.name ?? "—"}
                      </span>
                    </div>

                    {/* Staff */}
                    <div className="flex items-center gap-1.5 min-w-0">
                      {sub.staff ? (
                        <>
                          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-[10px] font-bold text-emerald-600 uppercase">
                            {(sub.staff.first_name?.[0] ?? "") + (sub.staff.last_name?.[0] ?? "")}
                          </div>
                          <span className="truncate text-sm text-foreground">
                            {sub.staff.first_name} {sub.staff.last_name}
                          </span>
                        </>
                      ) : (
                        <span className="text-sm text-muted-foreground italic">Unassigned</span>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setModal({ type: "edit", subject: sub })}
                        className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                        title="Edit"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setModal({ type: "delete", subject: sub })}
                        className="rounded-lg p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}

          {/* Footer count */}
          {!isLoading && filtered.length > 0 && (
            <div className="border-t border-border px-5 py-3 text-xs text-muted-foreground">
              {filtered.length} subject{filtered.length !== 1 ? "s" : ""}
              {search && ` matching "${search}"`}
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      <AnimatePresence>
        {modal?.type === "create" && (
          <SubjectModal
            key="create"
            mode="create"
            classrooms={classrooms}
            staff={staff}
            onClose={() => setModal(null)}
          />
        )}
        {modal?.type === "edit" && (
          <SubjectModal
            key="edit"
            mode="edit"
            initial={modal.subject}
            classrooms={classrooms}
            staff={staff}
            onClose={() => setModal(null)}
          />
        )}
        {modal?.type === "delete" && (
          <DeleteConfirmModal
            key="delete"
            subject={modal.subject}
            onClose={() => setModal(null)}
          />
        )}
      </AnimatePresence>
    </AuthGuard>
  );
}
