export const STATUS_META = {
  composed:  { label: 'Composed',  c: 'ok' },
  attached:  { label: 'Attached',  c: 'warn' },
  skipped:   { label: 'Skipped',   c: 'muted' },
  vocab_gap: { label: 'Vocab gap', c: 'bad' },
};

export function StatusDot({ status }) {
  const m = STATUS_META[status] || { c: 'muted', label: status };
  return <span className={`status-dot status-${m.c}`} title={m.label} />;
}
