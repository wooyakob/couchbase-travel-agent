interface Props {
  name: string
  args: Record<string, unknown>
}

function formatVal(v: unknown): string {
  if (typeof v === 'string') return `"${v}"`
  if (Array.isArray(v)) {
    if (v.length === 0) return '[]'
    if (v.length <= 3) return `[${v.map(formatVal).join(', ')}]`
    return `[${v.slice(0, 3).map(formatVal).join(', ')}, +${v.length - 3} more]`
  }
  if (v === null) return 'null'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

export default function ToolCallCard({ name, args }: Props) {
  const entries = Object.entries(args)

  return (
    <div className="tool-call">
      <div className="tool-header">
        <span className="tool-badge">tool</span>
        <span className="tool-name">{name}</span>
      </div>
      {entries.length > 0 && (
        <div className="tool-args">
          {entries.map(([k, v]) => (
            <div key={k} className="tool-arg-row">
              <span className="tool-arg-key">{k}</span>
              <span className="tool-arg-val">{formatVal(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
