import { shortenHomePath } from '../../domain/format'
import type { IndexedFolder } from '../../domain/indexing'
import { Button } from '../shared/Button'

interface FolderListProps {
  folders: IndexedFolder[]
  onToggle: (id: string, enabled: boolean) => void
  onRemove: (id: string) => void
}

/**
 * The folders that feed the index, each with the switch that stops it.
 *
 * Turning a folder off leaves its files indexed and stops watching it, so the
 * row says what the state means rather than only showing a switch. A user
 * turning something off wants to know what they just did to their results.
 */
export function FolderList({ folders, onToggle, onRemove }: FolderListProps) {
  if (folders.length === 0) {
    return <p className="mt-3 text-sm text-ink-muted">No folder is indexed yet.</p>
  }

  return (
    <ul className="mt-3">
      {folders.map((folder) => (
        <li key={folder.id} className="flex items-center gap-3 border-t border-border py-2 first:border-t-0">
          <Switch
            checked={folder.enabled}
            label={`Index ${shortenHomePath(folder.path)}`}
            onChange={(next) => onToggle(folder.id, next)}
          />
          <span
            className={`min-w-0 flex-1 truncate font-mono text-xs ${folder.enabled ? 'text-ink' : 'text-ink-muted line-through'}`}
            title={folder.path}
          >
            {shortenHomePath(folder.path)}
          </span>
          <Button className="px-2 py-1 text-xs" onClick={() => onRemove(folder.id)}>
            Remove
          </Button>
        </li>
      ))}
    </ul>
  )
}

interface SwitchProps {
  checked: boolean
  label: string
  onChange: (checked: boolean) => void
}

function Switch({ checked, label, onChange }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative h-5 w-9 shrink-0 rounded-full border transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
        checked ? 'border-accent bg-accent' : 'border-border bg-border/40'
      }`}
    >
      <span
        className={`absolute top-0.5 h-3.5 w-3.5 rounded-full bg-surface transition-[left] ${
          checked ? 'left-[1.125rem]' : 'left-0.5'
        }`}
      />
    </button>
  )
}
