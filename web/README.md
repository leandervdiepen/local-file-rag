# The landing page

One static page, no build step. Open `index.html` in a browser, or serve the
directory with anything that speaks HTTP.

```sh
python3 -m http.server -d web 8899
```

Deploy:

```sh
cd web && vercel deploy --prod
```

The palette, type ramp and timings are copied from `app/src/renderer/tokens.css`
rather than imported, because the page ships without a build step and the app
ships with Tailwind. When the app's tokens change, change them here too.

The fonts under `assets/fonts` are the same OFL licensed files the app embeds.

The download button points at the `latest` GitHub release and expects the DMG
to be uploaded there as `Local-file-search-arm64.dmg`. The name has no version
in it so the link survives the next release.
