import { shortenHomePath } from '../../domain/format'
import { explainSkip, type IndexedFileRow } from '../../domain/skip-reasons'
import { Button } from '../shared/Button'

interface SkippedFilesProps {
  files: IndexedFileRow[]
  onForget: (fileId: string) => void
}

/**
 * Every file that was left out, with the reason said as what the file is.
 *
 * Forget is here rather than only on indexed files because a skipped row is
 * still a line naming one of the user's files on a screen, and someone who
 * does not want this app holding that name has to be able to remove it.
 */
export function SkippedFiles({ files, onForget }: SkippedFilesProps) {
  if (files.length === 0) return null

  return (
    <table className="mt-6 w-full text-left text-xs">
      <thead className="text-ink-muted">
        <tr>
          <th scope="col" className="py-2 font-normal">
            File
          </th>
          <th scope="col" className="py-2 font-normal">
            Why
          </th>
          <th scope="col" className="py-2 font-normal">
            <span className="sr-only">Actions</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {files.map((file) => (
          <tr key={file.id} className="border-t border-border">
            <td className="max-w-xs truncate py-2 pr-6 font-mono text-ink" title={file.path}>
              {shortenHomePath(file.path)}
            </td>
            <td className="py-2 pr-6 text-ink-muted">{explainSkip(file.skipReason)}</td>
            <td className="py-2 text-right">
              <Button
                className="px-2 py-1 text-xs"
                aria-label={`Forget ${shortenHomePath(file.path)}`}
                onClick={() => onForget(file.id)}
              >
                Forget
              </Button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
