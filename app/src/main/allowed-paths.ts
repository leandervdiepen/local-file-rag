import path from 'node:path'

/**
 * True when `targetPath` sits inside one of `allowedRoots`.
 *
 * Compares resolved paths only, so a symlink inside an allowed root that
 * points outside it still passes. Closing that needs the real path of the
 * target, which costs a filesystem call on a check that runs per click.
 *
 * An empty root list allows nothing, which is what makes it safe to call
 * before the sidecar can say what is indexed.
 */
export function isPathAllowed(targetPath: string, allowedRoots: readonly string[]): boolean {
  const resolvedTarget = path.resolve(targetPath)
  return allowedRoots.some((root) => {
    const resolvedRoot = path.resolve(root)
    return resolvedTarget === resolvedRoot || resolvedTarget.startsWith(resolvedRoot + path.sep)
  })
}
