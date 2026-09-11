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

The download button is `/Local-file-search.dmg` so the browser sees that name.
Vercel redirects it to the `latest` GitHub release asset
`Local-file-search-arm64.dmg`. The asset name has no version in it so the
link survives the next release.

The hero video is `assets/launch.mp4`, copied from `docs/launch.mp4` on this
machine. Neither file is in git. Copy it before a Vercel deploy.
