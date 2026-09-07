import path from 'node:path'

// Filled from the sidecar's indexed folders once GET /folders exists. Empty
// until then, so every path is rejected. The check ships ahead of the data it
// guards on purpose: a boundary added after the feature works is one that gets
// skipped.
const INDEXED_FOLDERS: readonly string[] = []

/** Compares resolved paths only: a symlink pointing out of an allowed root still passes. */
export function isPathAllowed(targetPath: string, allowedRoots: readonly string[] = INDEXED_FOLDERS): boolean {
  const resolvedTarget = path.resolve(targetPath)
  return allowedRoots.some((root) => {
    const resolvedRoot = path.resolve(root)
    return resolvedTarget === resolvedRoot || resolvedTarget.startsWith(resolvedRoot + path.sep)
  })
}
