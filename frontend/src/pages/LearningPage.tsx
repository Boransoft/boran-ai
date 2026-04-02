import { useEffect, useState } from "react";

import InfoCard from "../components/InfoCard";
import { useAuthGuard } from "../hooks/useAuthGuard";
import { getLearningSummary, getReflections, ReflectionItem } from "../services/learningService";
import { useAuthStore } from "../store/authStore";
import { formatDateTime, truncate } from "../utils/format";

export default function LearningPage() {
  useAuthGuard();

  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState("");
  const [projectFocus, setProjectFocus] = useState("");
  const [recurringTopics, setRecurringTopics] = useState("");
  const [reflections, setReflections] = useState<ReflectionItem[]>([]);

  useEffect(() => {
    async function run() {
      if (!token || !user?.external_id) return;
      setLoading(true);
      setError("");

      try {
        const [summaryResponse, reflectionsResponse] = await Promise.all([
          getLearningSummary({ token, userId: user.external_id }),
          getReflections({ token, userId: user.external_id, limit: 20 }),
        ]);

        setSummary(summaryResponse.summary);
        setProjectFocus(summaryResponse.project_focus);
        setRecurringTopics(summaryResponse.recurring_topics);
        setReflections(reflectionsResponse);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Learning fetch failed");
      } finally {
        setLoading(false);
      }
    }

    run();
  }, [token, user?.external_id]);

  return (
    <section className="page-content">
      {loading ? <p className="muted">Loading learning insights...</p> : null}
      {error ? <p className="error-text">{error}</p> : null}

      <InfoCard title="Recurring Topics" value={recurringTopics} />
      <InfoCard title="Project Focus" value={projectFocus} />
      <InfoCard title="Recent Learning Summary" value={summary} />

      <section className="card">
        <h3>Reflection Timeline</h3>
        {reflections.length === 0 ? (
          <p>No reflection records yet.</p>
        ) : (
          <div className="list-stack">
            {reflections.map((item) => (
              <article key={item.id} className="list-item">
                <strong>{item.kind}</strong>
                <small>{formatDateTime(item.created_at)}</small>
                <p>{truncate(item.text, 260)}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
