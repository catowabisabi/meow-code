import { useState, useEffect } from "react";
import { adminApi } from "../../services/admin";
import styles from "./Admin.module.css";

interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  email_verified: boolean;
  created_at: string;
}

export function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    loadUsers();
  }, [page]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getUsers(page);
      setUsers(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || "Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (userId: string, currentActive: boolean) => {
    try {
      await adminApi.updateUser(userId, { is_active: !currentActive });
      setUsers(users.map(u => u.id === userId ? { ...u, is_active: !currentActive } : u));
    } catch (err: any) {
      setError(err.message || "Failed to update user");
    }
  };

  const handleDelete = async (userId: string) => {
    if (!confirm("Are you sure you want to delete this user?")) return;
    try {
      await adminApi.deleteUser(userId);
      setUsers(users.filter(u => u.id !== userId));
    } catch (err: any) {
      setError(err.message || "Failed to delete user");
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Users</h1>
        <button className={styles.buttonPrimary}>Add User</button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {loading ? (
        <div className={styles.loading}>Loading...</div>
      ) : (
        <>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Username</th>
                <th>Email</th>
                <th>Full Name</th>
                <th>Status</th>
                <th>Role</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id}>
                  <td>{user.username}</td>
                  <td>{user.email}</td>
                  <td>{user.full_name || "-"}</td>
                  <td>
                    <span className={`${styles.badge} ${user.is_active ? styles.badgeSuccess : styles.badgeDanger}`}>
                      {user.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td>
                    {user.is_superuser && <span className={styles.badgeAdmin}>Admin</span>}
                  </td>
                  <td>
                    <div className={styles.actions}>
                      <button
                        className={styles.buttonSmall}
                        onClick={() => handleToggleActive(user.id, user.is_active)}
                      >
                        {user.is_active ? "Deactivate" : "Activate"}
                      </button>
                      <button
                        className={styles.buttonSmallDanger}
                        onClick={() => handleDelete(user.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className={styles.pagination}>
            <button
              disabled={page <= 1}
              onClick={() => setPage(p => p - 1)}
              className={styles.buttonSmall}
            >
              Previous
            </button>
            <span>Page {page} of {Math.ceil(total / 10)}</span>
            <button
              disabled={page >= Math.ceil(total / 10)}
              onClick={() => setPage(p => p + 1)}
              className={styles.buttonSmall}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}