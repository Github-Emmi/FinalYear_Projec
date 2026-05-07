"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { UserCheck, Loader2, Search, Plus, Trash2, X, Pencil } from "lucide-react";
import { queryKeys } from "@/lib/query/keys";
import { listStaff, createStaff, updateStaff, deleteStaff } from "@/lib/api/staff";
import type { StaffCreatePayload } from "@/lib/api/staff";
import type { StaffProfileResponse } from "@/types/models";
import { listDepartments } from "@/lib/api/academic";
import { AuthGuard } from "@/components/auth/AuthGuard";

const EMPTY: StaffCreatePayload = {
  username: "", email: "", first_name: "", last_name: "", password: "",
  staff_id: "", department_id: null, designation: null,
  date_of_birth: null, gender: null, phone: null, address: null,
};

const inputCls = "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring";

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
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ opacity: 0, scale: 0.95, y: 8 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: 8 }}
        className="relative z-10 w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-xl max-h-[90vh] overflow-y-auto">
        <button onClick={onClose} className="absolute right-4 top-4 rounded-lg p-1 text-muted-foreground hover:bg-accent">
          <X className="h-4 w-4" />
        </button>
        {children}
      </motion.div>
    </div>
  );
}

export default function AdminStaffPage() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<StaffCreatePayload>(EMPTY);
  const [editTarget, setEditTarget] = useState<StaffProfileResponse | null>(null);
  const [editForm, setEditForm] = useState<{ designation?: string | null; department_id?: string | null; phone?: string | null }>({});
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

  // Debounce search — fire query 300ms after user stops typing
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.staff.all({ page, size: 20, search: debouncedSearch }),
    queryFn: () => listStaff({ page, size: 20, search: debouncedSearch || undefined }),
  });

  const { data: departments } = useQuery({
    queryKey: queryKeys.academic.departments(),
    queryFn: listDepartments,
    enabled: showCreate || !!editTarget,
  });

  const createMutation = useMutation({
    mutationFn: createStaff,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.staff.all({}) });
      setShowCreate(false);
      setForm(EMPTY);
    },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, string | null | undefined> }) => updateStaff(id, payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: queryKeys.staff.all({}) }); setEditTarget(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteStaff,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.staff.all({}) });
      setDeleteTarget(null);
    },
  });

  const openEdit = (s: StaffProfileResponse) => {
    setEditTarget(s);
    setEditForm({ designation: s.designation ?? "", department_id: s.department?.id ?? "", phone: s.phone ?? "" });
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(form);
  };

  return (
    <AuthGuard allowedRoles={["admin"]}>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Staff</h1>
            <p className="mt-1 text-sm text-muted-foreground">View and manage teaching and administrative staff</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            Add Staff
          </button>
        </div>

        <div className="flex flex-wrap gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search staff…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-card shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Name</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Email</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Department</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Designation</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(!data?.items || data.items.length === 0) && (
                  <tr>
                    <td colSpan={6} className="py-12 text-center">
                      <UserCheck className="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
                      <p className="text-sm text-muted-foreground">No staff found</p>
                    </td>
                  </tr>
                )}
                {data?.items.map((s) => (
                  <motion.tr key={s.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                    className="transition-colors hover:bg-muted/50">
                    <td className="px-4 py-3 font-medium text-foreground">
                      {s.user ? `${s.user.first_name} ${s.user.last_name}` : "—"}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{s.user?.email ?? "—"}</td>
                    <td className="px-4 py-3 text-muted-foreground">{s.department?.name ?? "—"}</td>
                    <td className="px-4 py-3 text-muted-foreground">{s.designation ?? "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        s.is_active
                          ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                          : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                      }`}>
                        {s.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => openEdit(s)}
                          className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground" title="Edit staff">
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => setDeleteTarget({ id: s.id, name: s.user ? `${s.user.first_name} ${s.user.last_name}` : s.id })}
                          className="rounded p-1 text-muted-foreground hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
                          title="Delete staff"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && data.total > data.size && (
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Showing {(page - 1) * data.size + 1}–{Math.min(page * data.size, data.total)} of {data.total}</span>
            <div className="flex gap-2">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                className="rounded-lg border border-border px-3 py-1.5 text-xs disabled:opacity-40 hover:bg-accent">Previous</button>
              <button onClick={() => setPage((p) => p + 1)} disabled={page * data.size >= data.total}
                className="rounded-lg border border-border px-3 py-1.5 text-xs disabled:opacity-40 hover:bg-accent">Next</button>
            </div>
          </div>
        )}
      </div>

      {/* ── Create Staff Modal ── */}
      <AnimatePresence>
        {showCreate && (
          <Modal onClose={() => { setShowCreate(false); setForm(EMPTY); }}>
            <h2 className="mb-5 text-lg font-semibold text-foreground">Add Staff Member</h2>
            <form onSubmit={handleCreate} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Field label="First Name"><input required value={form.first_name} onChange={(e) => setForm((p) => ({ ...p, first_name: e.target.value }))} className={inputCls} /></Field>
                <Field label="Last Name"><input required value={form.last_name} onChange={(e) => setForm((p) => ({ ...p, last_name: e.target.value }))} className={inputCls} /></Field>
              </div>
              <Field label="Username"><input required value={form.username} onChange={(e) => setForm((p) => ({ ...p, username: e.target.value }))} className={inputCls} /></Field>
              <Field label="Email"><input required type="email" value={form.email} onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))} className={inputCls} /></Field>
              <Field label="Password"><input required type="password" minLength={8} value={form.password} onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))} className={inputCls} /></Field>
              <Field label="Designation"><input value={form.designation ?? ""} onChange={(e) => setForm((p) => ({ ...p, designation: e.target.value || null }))} className={inputCls} placeholder="e.g. Lecturer" /></Field>
              <Field label="Department">
                <select value={form.department_id ?? ""} onChange={(e) => setForm((p) => ({ ...p, department_id: e.target.value || null }))} className={inputCls}>
                  <option value="">No department</option>
                  {departments?.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </Field>
              <Field label="Phone"><input type="tel" value={form.phone ?? ""} onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value || null }))} className={inputCls} /></Field>
              {createMutation.error && (
                <p className="text-xs text-red-600">{(createMutation.error as Error).message}</p>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => { setShowCreate(false); setForm(EMPTY); }} className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-accent">Cancel</button>
                <button type="submit" disabled={createMutation.isPending} className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                  {createMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Create
                </button>
              </div>
            </form>
          </Modal>
        )}
      </AnimatePresence>

      {/* ── Edit Staff Modal ── */}
      <AnimatePresence>
        {editTarget && (
          <Modal onClose={() => setEditTarget(null)}>
            <h2 className="mb-5 text-lg font-semibold text-foreground">Edit Staff Member</h2>
            <form onSubmit={(e) => { e.preventDefault(); editMutation.mutate({ id: editTarget.id, payload: editForm }); }} className="space-y-4">
              <Field label="Designation">
                <input value={editForm.designation ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, designation: e.target.value || null }))} className={inputCls} placeholder="e.g. Lecturer" />
              </Field>
              <Field label="Department">
                <select value={editForm.department_id ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, department_id: e.target.value || null }))} className={inputCls}>
                  <option value="">No department</option>
                  {departments?.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </Field>
              <Field label="Phone">
                <input type="tel" value={editForm.phone ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, phone: e.target.value || null }))} className={inputCls} />
              </Field>
              {editMutation.error && <p className="text-xs text-red-600">{(editMutation.error as Error).message}</p>}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setEditTarget(null)} className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-accent">Cancel</button>
                <button type="submit" disabled={editMutation.isPending} className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50">
                  {editMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}Save Changes
                </button>
              </div>
            </form>
          </Modal>
        )}
      </AnimatePresence>

      {/* ── Delete Confirm Modal ── */}
      <AnimatePresence>
        {deleteTarget && (
          <Modal onClose={() => setDeleteTarget(null)}>
            <h2 className="mb-2 text-lg font-semibold text-foreground">Delete Staff Member</h2>
            <p className="mb-5 text-sm text-muted-foreground">
              Are you sure you want to delete <strong>{deleteTarget.name}</strong>?
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteTarget(null)} className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-accent">Cancel</button>
              <button onClick={() => deleteMutation.mutate(deleteTarget.id)} disabled={deleteMutation.isPending}
                className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50">
                {deleteMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Delete
              </button>
            </div>
          </Modal>
        )}
      </AnimatePresence>
    </AuthGuard>
  );
}


