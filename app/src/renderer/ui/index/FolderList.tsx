import { shortenHomePath } from '../../domain/format'
import type { IndexedFolder } from '../../domain/indexing'
import { QuietButton } from '../shared/QuietButton'

interface FolderListProps {
  folders: IndexedFolder[]
  onToggle: (id: string, enabled: boolean) => void
  onRemove: (id: string) => void
}

/**
 * The folders that feed the index, each with the switch that stops it.
 *
 * Turning a folder off leaves its files indexed and stops watching it, so the
 * path only dims rather than being struck through: nothing has been removed.
 */
export function FolderList({ folders, onToggle, onRemove }: FolderListProps) {
  if (folders.length === 0) {
    return <p className="mt-3 text-sm text-ink-muted">No folders yet. Add one to start indexing.</p>
  }

  return (
    <ul className="mt-3 divide-y divide-border">
      {folders.map((folder) => {
        const shown = shortenHomePath(folder.path)
        return (
          <li key={folder.id} className="flex items-center gap-3 py-2">
            <Switch checked={folder.enabled} label={`Index ${shown}`} onChange={(next) => onToggle(folder.id, next)} />
            <span
              className={`min-w-0 flex-1 truncate font-mono text-xs ${folder.enabled ? 'text-ink' : 'text-ink-muted'}`}
              title={folder.path}
            >
              {shown}
            </span>
            <QuietButton aria-label={`Remove ${shown}`} onClick={() => onRemove(folder.id)}>
              Remove
            </QuietButton>
          </li>
        )
      })}
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
      className={`focus-ring relative h-5 w-9 shrink-0 rounded-full transition-colors before:absolute before:-inset-2 before:content-[''] ${
        checked ? 'bg-accent' : 'bg-border'
      }`}
    >
      <span
        className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow-control transition-transform ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  )
}
