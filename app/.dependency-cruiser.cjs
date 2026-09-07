/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: 'domain-imports-nothing',
      severity: 'error',
      comment: 'renderer/domain is pure: it may only import from within itself.',
      from: { path: '^src/renderer/domain' },
      to: { pathNot: '^src/renderer/domain' },
    },
    {
      name: 'application-not-infrastructure-or-ui',
      severity: 'error',
      comment: 'renderer/application depends on ports, not on their implementations or on components.',
      from: { path: '^src/renderer/application' },
      to: { path: '^src/renderer/(infrastructure|ui)' },
    },
    {
      name: 'infrastructure-not-ui',
      severity: 'error',
      comment: 'renderer/infrastructure implements ports; it does not render anything.',
      from: { path: '^src/renderer/infrastructure' },
      to: { path: '^src/renderer/ui' },
    },
    {
      name: 'main-not-renderer',
      severity: 'error',
      comment: 'main and renderer are separate processes; they never import each other.',
      from: { path: '^src/main' },
      to: { path: '^src/renderer' },
    },
    {
      name: 'renderer-not-main',
      severity: 'error',
      comment: 'main and renderer are separate processes; they never import each other.',
      from: { path: '^src/renderer' },
      to: { path: '^src/main' },
    },
    {
      name: 'no-index-barrels',
      severity: 'error',
      comment: 'Name a file after what is in it. No index.ts or index.tsx barrels.',
      from: {},
      to: { path: '(^|/)index\\.tsx?$' },
    },
    {
      name: 'no-circular',
      severity: 'error',
      comment: 'A cycle between modules means the layer boundaries have collapsed.',
      from: {},
      to: { circular: true },
    },
    {
      name: 'no-orphans',
      severity: 'error',
      comment: 'A file nothing imports and that is not a build entry point is dead code.',
      from: {
        orphan: true,
        pathNot: [
          '\\.d\\.ts$',
          '^src/main/main\\.ts$',
          '^src/preload/bridge\\.ts$',
          '^src/renderer/main\\.tsx$',
          // Nothing imports it yet. The search and index screens will.
          '^src/renderer/domain/format\\.ts$',
        ],
      },
      to: {},
    },
  ],
  options: {
    tsPreCompilationDeps: true,
  },
}
