import { useState, useEffect } from "react";
import { adminApi } from "../../services/admin";
import styles from "./Admin.module.css";

interface Role {
  id: string;
  name: string;
  description: string | null;
  permissions: string[];
  user_count: number;
}

export function RolesPage() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    loadRoles();
  }, []);

  const loadRoles = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getRoles();
      setRoles(data);
    } catch (err: any) {
      setError(err.message || "Failed to load roles");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRole = async (name: string, description: string, permissions: string[]) => {
    try {
      await adminApi.createRole({ name, description, permissions });
      setShowModal(false);
      loadRoles();
    } catch (err: any) {
      setError(err.message || "Failed to create role");
    }
  };

  const handleDelete = async (roleId: string) => {
    if (!confirm("Are you sure you want to delete this role?")) return;
    try {
      await adminApi.deleteRole(roleId);
      setRoles(roles.filter(r => r.id !== roleId));
    } catch (err: any) {
      setError(err.message || "Failed to delete role");
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Roles</h1>
        <button className={styles.buttonPrimary} onClick={() => setShowModal(true)}>
          Create Role
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {loading ? (
        <div className={styles.loading}>Loading...</div>
      ) : (
        <div className={styles.grid}>
          {roles.map(role => (
            <div key={role.id} className={styles.card}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>{role.name}</h3>
                <span className={styles.badge}>{role.user_count} users</span>
              </div>
              <p className={styles.cardDescription}>{role.description || "No description"}</p>
              <div className={styles.permissions}>
                {role.permissions.slice(0, 3).map(p => (
                  <span key={p} className={styles.permissionTag}>{p}</span>
                ))}
                {role.permissions.length > 3 && (
                  <span className={styles.moreTag}>+{role.permissions.length - 3} more</span>
                )}
              </div>
              <div className={styles.cardActions}>
                <button className={styles.buttonSmall}>Edit</button>
                <button
                  className={styles.buttonSmallDanger}
                  onClick={() => handleDelete(role.id)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <h2 className={styles.modalTitle}>Create Role</h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                handleCreateRole(
                  formData.get("name") as string,
                  formData.get("description") as string,
                  []
                );
              }}
            >
              <div className={styles.field}>
                <label>Name</label>
                <input name="name" type="text" required />
              </div>
              <div className={styles.field}>
                <label>Description</label>
                <textarea name="description" rows={3} />
              </div>
              <div className={styles.modalActions}>
                <button type="button" className={styles.buttonSecondary} onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className={styles.buttonPrimary}>
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}