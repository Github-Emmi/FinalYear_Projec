"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { CalendarDays, Loader2, Plus, Trash2, X, Clock } from "lucide-react";
import { queryKeys } from "@/lib/query/keys";
import {
  listTimetable,
  createTimetableEntry,
  deleteTimetableEntry,
  type TimetableEntryCreate,
  type TimetableEntryResponse,
} from "@/lib/api/timetable";
import { listClassrooms, listSessionYears, listSubjects } from "@/lib/api/academic";
import { listStaff } from "@/lib/api/staff";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { cn } from "@/lib/utils/cn";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

const EMPTY: TimetableEntryCreate = {
  classroom_id: "",
  subject_id: "",
  staff_id: "",
  session_year_id: "",
  day_of_week: 0,
  start_time: "08:00",
  end_time: "09:00",
};

const inputCls =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="block text-xs font-medium text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

function Modal({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }} animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        className="relative z-10 w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-xl max-h-[90vh] overflow-y-auto"
      >
        <button onClick={onClose} className="absolute right-4 top-4 rounded-lg p-1 text-muted-foreground hover:bg-accent">
          <X className="h-4 w-4" />
        </button>
        {children}
      </motion.div>
    </div>
  );
}

function EntryCard({
  entry,
  onDelete,
}: {
  entry: TimetableEntryResponse;
  onDelete: (entry: TimetableEntryResponse) => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
      className="group relative rounded-xl border border-border bg-primary/5 p-3 text-xs hover:border-primary/40 hover:bg-primary/10 transition-all"
    >
      <p className="font-semibold text-foreground leading-tight">{entry.subject.name}</p>
      <div className="mt-1 flex items-center gap-1 text-muted-foreground">
        <Clock className="h-3 w-3 shrink-0" />
        <span>{entry.start_time}–{entry.end_time}</span>
      </div>
      <p className="mt-0.5 text-muted-foreground truncate">{entry.staff.name}</p>
      <button
        onClick={() => onDelete(entry)}
        className="absolute right-2 top-2 rounded p-0.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
        title="Delete"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </motion.div>
  );
}

export default function AdminTimetablePage() {
  const qc = useQueryClient();
  const [classroomId, setClassroomId] = useState("");
  const [sessionYearId, setSessionYearId] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<TimetableEntryCreate>(EMPTY);
  const [deleteTarget, setDeleteTarget] = useState<TimetableEntryResponse | null>(null);

  const { data: classrooms } = useQuery({
    queryKey: queryKeys.academic.classrooms({ size: 100 }),
    queryFn: () => listClassrooms({ size: 100 }),
  });

  const { data: sessionYears } = useQuery({
    queryKey: queryKeys.academic.sessionYears(),
    queryFn: listSessionYears,
  });

  const { data: timetableData, isLoading } = useQuery({
    queryKey: queryKeys.timetable.list({ classroom_id: classroomId, session_year_id: sessionYearId }),
    queryFn: () => listTimetable({
      classroom_id: classroomId || undefined,
      session_year_id: sessionYearId || undefined,
    }),
    enabled: !!(classroomId && sessionYearId),
  });

  // Auto-select current session year when data loads
  useEffect(() => {
    if (sessionYears && !sessionYearId) {
      const current = sessionYears.find((y) => y.is_current);
      if (current) setSessionYearId(String(current.id));
    }
  }, [sessionYears, sessionYearId]);

  // Subjects filtered by selected classroom
  const { data: subjects } = useQuery({
    queryKey: queryKeys.academic.subjects({ classroom_id: form.classroom_id || undefined, size: 200 }),
    queryFn: () => listSubjects({ classroom_id: form.classroom_id || undefined, size: 200 }),
    enabled: showCreate,
  });

  const { data: staff } = useQuery({
    queryKey: queryKeys.staff.all({ size: 200 }),
    queryFn: () => listStaff({ size: 200 }),
    enabled: showCreate,
  });

  const createMutation = useMutation({
    mutationFn: createTimetableEntry,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.timetable.list({}) });
      setShowCreate(false);
      setForm(EMPTY);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTimetableEntry,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.timetable.list({}) });
      setDeleteTarget(null);
    },
  });

  const openCreate = () => {
    const currentYear = sessionYears?.find((y) => y.is_current);
    const effectiveSessionYearId = sessionYearId || (currentYear ? String(currentYear.id) : "");
    setForm({ ...EMPTY, classroom_id: classroomId, session_year_id: effectiveSessionYearId });
    setShowCreate(true);
  };

  // Group entries by day_of_week (0-4 = Mon-Fri)
  const byDay = (day: number): TimetableEntryResponse[] =>
    (timetableData?.items ?? [])
      .filter((e) => e.day_of_week === day)
      .sort((a, b) => a.start_time.localeCompare(b.start_time));

  return (
    <AuthGuard allowedRoles={["admin"]}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Timetable</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Manage class schedules by classroom and session year
            </p>
          </div>
          <button
            onClick={openCreate}
            disabled={!classroomId || !sessionYearId}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Plus className="h-4 w-4" />
            Add Entry
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Classroom</label>
            <select
              value={classroomId}
              onChange={(e) => setClassroomId(e.target.value)}
              className="rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Select classroom…</option>
              {classrooms?.items?.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Session Year</label>
            <select
              value={sessionYearId}
              onChange={(e) => setSessionYearId(e.target.value)}
              className="rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Select year…</option>
              {sessionYears?.map((y) => (
                <option key={y.id} value={y.id}>{y.start_year}/{y.end_year}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Timetable Grid */}
        {!classroomId || !sessionYearId ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border py-20 text-center">
            <CalendarDays className="h-10 w-10 text-muted-foreground" />
            <p className="mt-3 font-medium text-foreground">Select a classroom and session year</p>
            <p className="mt-1 text-sm text-muted-foreground">to view and manage the timetable</p>
          </div>
        ) : isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="grid grid-cols-5 gap-3">
            {DAYS.map((day, idx) => {
              const entries = byDay(idx);
              return (
                <div key={day} className="space-y-2">
                  <div className={cn(
                    "rounded-xl border px-3 py-2 text-center text-sm font-semibold",
                    entries.length > 0
                      ? "border-primary/40 bg-primary/10 text-primary"
                      : "border-border bg-muted text-muted-foreground"
                  )}>
                    {day}
                    {entries.length > 0 && (
                      <span className="ml-1.5 text-xs font-normal">({entries.length})</span>
                    )}
                  </div>
                  {entries.length === 0 ? (
                    <div className="rounded-xl border-2 border-dashed border-border py-6 text-center text-xs text-muted-foreground">
                      No classes
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {entries.map((e) => (
                        <EntryCard key={e.id} entry={e} onDelete={setDeleteTarget} />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Modal */}
      <AnimatePresence>
        {showCreate && (
          <Modal onClose={() => { setShowCreate(false); setForm(EMPTY); }}>
            <h2 className="mb-5 text-lg font-semibold text-foreground">Add Timetable Entry</h2>
            <form
              onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form); }}
              className="space-y-3"
            >
              <Field label="Day">
                <select
                  value={form.day_of_week}
                  onChange={(e) => setForm((f) => ({ ...f, day_of_week: Number(e.target.value) }))}
                  className={inputCls}
                >
                  {DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
                </select>
              </Field>

              <div className="grid grid-cols-2 gap-3">
                <Field label="Start Time">
                  <input
                    type="time"
                    required
                    value={form.start_time}
                    onChange={(e) => setForm((f) => ({ ...f, start_time: e.target.value }))}
                    className={inputCls}
                  />
                </Field>
                <Field label="End Time">
                  <input
                    type="time"
                    required
                    value={form.end_time}
                    onChange={(e) => setForm((f) => ({ ...f, end_time: e.target.value }))}
                    className={inputCls}
                  />
                </Field>
              </div>

              <Field label="Subject">
                <select
                  required
                  value={form.subject_id}
                  onChange={(e) => setForm((f) => ({ ...f, subject_id: e.target.value }))}
                  className={inputCls}
                >
                  <option value="">Select subject…</option>
                  {(subjects ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </Field>

              <Field label="Staff">
                <select
                  required
                  value={form.staff_id}
                  onChange={(e) => setForm((f) => ({ ...f, staff_id: e.target.value }))}
                  className={inputCls}
                >
                  <option value="">Select staff member…</option>
                  {staff?.items?.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.user ? `${s.user.first_name} ${s.user.last_name}` : s.id}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label="Session">
                <select
                  required
                  value={form.session_year_id}
                  onChange={(e) => setForm((f) => ({ ...f, session_year_id: e.target.value }))}
                  className={inputCls}
                >
                  <option value="">Select session…</option>
                  {sessionYears?.map((y) => (
                    <option key={y.id} value={y.id}>
                      {y.start_year}/{y.end_year}{y.is_current ? " (Current)" : ""}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label="Notes (optional)">
                <input
                  value={form.notes ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value || null }))}
                  className={inputCls}
                  placeholder="e.g. Lab session"
                />
              </Field>

              {createMutation.error && (
                <p className="text-xs text-red-600">{(createMutation.error as Error).message}</p>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowCreate(false); setForm(EMPTY); }}
                  className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-accent"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {createMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Add Entry
                </button>
              </div>
            </form>
          </Modal>
        )}
      </AnimatePresence>

      {/* Delete Confirm */}
      <AnimatePresence>
        {deleteTarget && (
          <Modal onClose={() => setDeleteTarget(null)}>
            <h2 className="mb-2 text-lg font-semibold text-foreground">Remove Entry</h2>
            <p className="mb-5 text-sm text-muted-foreground">
              Remove <strong>{deleteTarget.subject.name}</strong> on{" "}
              <strong>{DAYS[deleteTarget.day_of_week]}</strong> ({deleteTarget.start_time}–{deleteTarget.end_time})?
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteTarget(null)} className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-accent">Cancel</button>
              <button
                onClick={() => deleteMutation.mutate(deleteTarget.id)}
                disabled={deleteMutation.isPending}
                className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Remove
              </button>
            </div>
          </Modal>
        )}
      </AnimatePresence>
    </AuthGuard>
  );
}
