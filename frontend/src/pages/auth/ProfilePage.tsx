import { useState, useEffect } from "react";
import { authService } from "../../services/auth";
import styles from "./Auth.module.css";

interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  is_active: boolean;
  is_superuser: boolean;
}

export function ProfilePage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    try {
      const userData = await authService.getMe();
      setUser(userData);
    } catch (err: any) {
      setError(err.message || "Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    window.location.href = "/login";
  };

  if (loading) return <div className={styles.container}>Loading...</div>;
  if (error) return <div className={styles.container}><div className={styles.error}>{error}</div></div>;
  if (!user) return null;

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>Profile</h1>
        <div className={styles.profile}>
          <div className={styles.avatar}>
            {user.avatar_url ? (
              <img src={user.avatar_url} alt={user.username} />
            ) : (
              <div className={styles.avatarPlaceholder}>
                {user.username.charAt(0).toUpperCase()}
              </div>
            )}
          </div>
          <div className={styles.info}>
            <div className={styles.row}>
              <span className={styles.label}>Username:</span>
              <span className={styles.value}>{user.username}</span>
            </div>
            <div className={styles.row}>
              <span className={styles.label}>Email:</span>
              <span className={styles.value}>{user.email}</span>
            </div>
            {user.full_name && (
              <div className={styles.row}>
                <span className={styles.label}>Full Name:</span>
                <span className={styles.value}>{user.full_name}</span>
              </div>
            )}
            <div className={styles.row}>
              <span className={styles.label}>Status:</span>
              <span className={styles.value}>{user.is_active ? "Active" : "Inactive"}</span>
            </div>
            {user.is_superuser && (
              <div className={styles.badge}>Admin</div>
            )}
          </div>
        </div>
        <button onClick={handleLogout} className={styles.buttonSecondary}>
          Sign Out
        </button>
      </div>
    </div>
  );
}