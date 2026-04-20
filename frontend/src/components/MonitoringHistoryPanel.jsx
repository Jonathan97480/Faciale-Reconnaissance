export default function MonitoringHistoryPanel({ children, title }) {
  return (
    <section className="history-panel">
      <h3>{title}</h3>
      {children}
    </section>
  );
}
