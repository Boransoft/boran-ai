type Props = {
  title: string;
  value: string;
};

export default function InfoCard({ title, value }: Props) {
  return (
    <section className="card">
      <h3>{title}</h3>
      <p>{value || "No data yet."}</p>
    </section>
  );
}
