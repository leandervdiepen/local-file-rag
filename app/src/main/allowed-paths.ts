import path from 'node:path'

// TODO: populate from the sidecar's indexed folders (GET /folders) once that
// exists. Until then the allowlist is empty and every path is rejected, so
// shell.openPath has nothing to act on. The check exists now on purpose:
// adding it later, after there is something to index, is how it gets forgotten.
const INDEXED_FOLDERS: readonly string[] = []

/** True when targetPath is inside one of the allowed roots, symlink tricks aside. */
export function isPathAllowed(targetPath: string, allowedRoots: readonly string[] = INDEXED_FOLDERS): boolean {
  const resolvedTarget = path.resolve(targetPath)
  return allowedRoots.some((root) => {
    const resolvedRoot = path.resolve(root)
    return resolvedTarget === resolvedRoot || resolvedTarget.startsWith(resolvedRoot + path.sep)
  })
}
