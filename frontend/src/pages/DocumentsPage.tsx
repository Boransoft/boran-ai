import { FormEvent, useState } from "react";

import { useAuthGuard } from "../hooks/useAuthGuard";
import { uploadDocument } from "../services/documentService";
import { useAuthStore } from "../store/authStore";

export default function DocumentsPage() {
  useAuthGuard();

  const token = useAuthStore((state) => state.token);

  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState("general");
  const [tags, setTags] = useState("ai,notes");
  const [result, setResult] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!token || !file) return;

    setLoading(true);
    setError("");
    setResult("");

    try {
      const response = await uploadDocument({
        token,
        file,
        category,
        tags,
      });
      setResult(`Uploaded: ${response.file} | chunks: ${response.chunks} | status: ${response.status}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-content">
      <form className="form-stack card" onSubmit={onSubmit}>
        <h3>Upload Document</h3>

        <label>
          File
          <input
            type="file"
            accept=".pdf,.doc,.docx,.txt,.md,.csv,.json,.jsonl,.png,.jpg,.jpeg"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            required
          />
        </label>

        <label>
          Category
          <input value={category} onChange={(e) => setCategory(e.target.value)} />
        </label>

        <label>
          Tags (comma separated)
          <input value={tags} onChange={(e) => setTags(e.target.value)} />
        </label>

        <button className="primary" disabled={loading || !file} type="submit">
          {loading ? "Uploading..." : "Upload"}
        </button>
      </form>

      {result ? <p className="success-text">{result}</p> : null}
      {error ? <p className="error-text">{error}</p> : null}

      <p className="muted">Backend route: /documents/upload</p>
    </section>
  );
}
