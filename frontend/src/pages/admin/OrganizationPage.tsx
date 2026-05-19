import { useState, useEffect } from "react";
import { adminApi } from "../../services/admin";
import styles from "./Admin.module.css";

interface Department {
  id: string;
  name: string;
  description: string | null;
  parent_id: string | null;
  team_count: number;
}

interface Team {
  id: string;
  name: string;
  department_id: string;
  leader_id: string | null;
  member_count: number;
}

export function OrganizationPage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"departments" | "teams">("departments");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [deptData, teamData] = await Promise.all([
        adminApi.getDepartments(),
        adminApi.getTeams(),
      ]);
      setDepartments(deptData);
      setTeams(teamData);
    } catch (err: any) {
      setError(err.message || "Failed to load organization data");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Organization</h1>
        <button
          className={styles.buttonPrimary}
          onClick={() => {
            const name = prompt("Department name:");
            if (name) adminApi.createDepartment({ name }).then(loadData);
          }}
        >
          Add Department
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === "departments" ? styles.tabActive : ""}`}
          onClick={() => setActiveTab("departments")}
        >
          Departments
        </button>
        <button
          className={`${styles.tab} ${activeTab === "teams" ? styles.tabActive : ""}`}
          onClick={() => setActiveTab("teams")}
        >
          Teams
        </button>
      </div>

      {loading ? (
        <div className={styles.loading}>Loading...</div>
      ) : (
        <div className={styles.tableContainer}>
          {activeTab === "departments" ? (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Description</th>
                  <th>Teams</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {departments.map(dept => (
                  <tr key={dept.id}>
                    <td>{dept.name}</td>
                    <td>{dept.description || "-"}</td>
                    <td>{dept.team_count}</td>
                    <td>
                      <button className={styles.buttonSmall}>Edit</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Department</th>
                  <th>Members</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {teams.map(team => (
                  <tr key={team.id}>
                    <td>{team.name}</td>
                    <td>{departments.find(d => d.id === team.department_id)?.name || "-"}</td>
                    <td>{team.member_count}</td>
                    <td>
                      <button className={styles.buttonSmall}>Edit</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}