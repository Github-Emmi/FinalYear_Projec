"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Users, Loader2, Search, Plus, Trash2, Pencil, X } from "lucide-react";
import { queryKeys } from "@/lib/query/keys";
import { listUsers, createUser, deactivateUser, updateUser } from "@/lib/api/users";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { cn } from "@/lib/utils/cn";
import type { UserCreatePayload } from "@/lib/api/users";
import type { UserResponse } from "@/types/models";

const EMPTY_FORM: UserCreatePayload = {
  first_name: "",
  last_name: "",
  username: "",
  email: "",
  password: "",
  role: "student",
};

export default function AdminUsersPage() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<UserCreatePayload>(EMPTY_FORM);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [editTarget, setEditTarget] = useState<UserResponse | null>(null);
  const [editForm, setEditForm] = useState<Partial<UserCreatePayload>>({});

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.users.all({ page, size: 20, search, role: roleFilter }),
    queryFn: () =>
      listUsers({ page, size: 20, search: search || undefined, role: roleFilter || undefined }),
  });

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.users.all({}) });
      setShowCreate(false);
      setForm(EMPTY_FORM);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deactivateUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.users.all({}) });
      setDeleteTarget(null);
    },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<UserCreatePayload> }) =>
      updateUser(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.users.all({}) });
      setEditTarget(null);
    },
  });

  const openEdit = (u: UserResponse) => {
    setEditTarget(u);
    setEditForm({
      first_name: u.first_name,
      last_name: u.last_name,
      email: u.email,
      role: u.role as UserCreatePayload["role"],
    });
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(form);
  };

  const handleEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editTarget) return;
    editMutation.mutate({ id: editTarget.id, payload: editForm });
  };

  return (
    <AuthGuard allowedRoles={["admin"]}>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Users</h1>
            <p className="mt-1 text-sm text-muted-foreground">Manage all platform users</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            Add User
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search users…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <select
            value={roleFilter}
            onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
            className="rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">All roles</option>
            <option value="admin">Admin</option>
            <option value="staff">Staff</option>
            <option value="student">Student</option>
          </select>
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
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Username</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Email</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Role</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(!data?.items || data.items.length === 0) && (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-muted-foreground">
                      <Users className="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
                      No users found
                    </td>
                  </tr>
                )}
                {data?.items.map((u) => (
                  <motion.tr
                    key={u.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="transition-colors hover:bg-accent/50"
                  >
                    <td className="px-4 py-3 font-medium text-foreground">
                      {u.first_name} {u.last_name}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{u.username}</td>
                    <td className="px-4 py-3 text-muted-foreground">{u.email}</td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
                        u.role === "admin" ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
                          : u.role === "staff" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                          : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      )}>
                        {u.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium",
                        u.is_active
                          ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                          : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                      )}>
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => openEdit(u)}
                          className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
                          title="Edit user"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => setDeleteTarget({ id: u.id, name: `${u.first_name} ${u.last_name}` })}
                          className="rounded p-1 text-muted-foreground hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
                          title="Delete user"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>

            {data && data.pages > 1 && (
              <div className="flex items-center justify-between border-t border-border px-4 py-3">
                <p className="text-xs text-muted-foreground">
                  Page {data.page} of {data.pages} ({data.total} total)
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                    disabled={page === data.pages}
                    className="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Create User Modal ── */}
      <AnimatePresence>
        {showCreate && (
          <Modal onClose={() => { setShowCreate(false); setForm(EMPTY_FORM); }}>
            <h2 className="mb-5 text-lg font-semibold text-foreground">Add User</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <Field label="First Name">
                  <input required value={form.first_name} onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))} className={inputCls} />
                </Field>
                <Field label="Last Name">
                  <input required value={form.last_name} onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))} className={inputCls} />
                </Field>
              </div>
              <Field label="Username">
                <input required value={form.username} onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))} className={inputCls} />
              </Field>
              <Field label="Email">
                <input required type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} className={inputCls} />
              </Field>
              <Field label="Password">
                <input required type="password" minLength={8} value={form.password} onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} className={inputCls} />
              </Field>
              <Field label="Role">
                <select value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value as UserCreatePayload["role"] }))} className={inputCls}>
                  <option value="student">Student</option>
                  <option value="staff">Staff</option>
                  <option value="admin">Admin</option>
                </select>
              </Field>
              {createMutation.error && (
                <p className="text-xs text-red-600">{(createMutation.error as Error).message}</p>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => { setShowCreate(false); setForm(EMPTY_FORM); }} className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-accent">Cancel</button>
                <button type="submit" disabled={createMutation.isPending} className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                  {createMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Create User
                </button>
              </div>
            </form>
          </Modal>
        )}
      </AnimatePresence>

      {/* ── Edit User Modal ── */}
      <AnimatePresence>
        {editTarget && (
          <Modal onClose={() => setEditTarget(null)}>
            <h2 className="mb-5 text-lg font-semibold text-foreground">Edit User</h2>
            <form onSubmit={handleEdit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <Field label="First Name">
                  <input required value={editForm.first_name ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, first_name: e.target.value }))} className={inputCls} />
                </Field>
                <Field label="Last Name">
                  <input required value={editForm.last_name ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, last_name: e.target.value }))} className={inputCls} />
                </Field>
              </div>
              <Field label="Email">
                <input required type="email" value={editForm.email ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, email: e.target.value }))} className={inputCls} />
              </Field>
              <Field label="Role">
                <select value={editForm.role ?? "student"} onChange={(e) => setEditForm((f) => ({ ...f, role: e.target.value as UserCreatePayload["role"] }))} className={inputCls}>
                  <option value="student">Student</option>
                  <option value="staff">Staff</option>
                  <option value="admin">Admin</option>
                </select>
              </Field>
              {editMutation.error && (
                <p className="text-xs text-red-600">{(editMutation.error as Error).message}</p>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setEditTarget(null)} className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-accent">Cancel</button>
                <button type="submit" disabled={editMutation.isPending} className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                  {editMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Save Changes
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
            <h2 className="mb-2 text-lg font-semibold text-foreground">Delete User</h2>
            <p className="mb-5 text-sm text-muted-foreground">
              Are you sure you want to delete <strong>{deleteTarget.name}</strong>? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteTarget(null)} className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-accent">Cancel</button>
              <button
                onClick={() => deleteMutation.mutate(deleteTarget.id)}
                disabled={deleteMutation.isPending}
                className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
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

// ── Shared primitives ──────────────────────────────────────────────────────────

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
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        className="relative z-10 w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-xl"
      >
        <button onClick={onClose} className="absolute right-4 top-4 rounded-lg p-1 text-muted-foreground hover:bg-accent">
          <X className="h-4 w-4" />
        </button>
        {children}
      </motion.div>
    </div>
  );
}
