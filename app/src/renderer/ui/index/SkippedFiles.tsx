import { shortenHomePath } from '../../domain/format'
import { explainSkip, type IndexedFileRow } from '../../domain/skip-reasons'

interface SkippedFilesProps {
  files: IndexedFileRow[]
}

/** Every file that was left out, with the reason said as what the file is. */
export function SkippedFiles({ files }: SkippedFilesProps) {
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
        </tr>
      </thead>
      <tbody>
        {files.map((file) => (
          <tr key={file.id} className="border-t border-border">
            <td className="max-w-xs truncate py-2 pr-6 font-mono text-ink" title={file.path}>
              {shortenHomePath(file.path)}
            </td>
            <td className="py-2 text-ink-muted">{explainSkip(file.skipReason)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
