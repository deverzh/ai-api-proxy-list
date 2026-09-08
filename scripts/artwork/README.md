# Editorial artwork

The banner and overview are editable technical illustrations, not screenshots
or evidence of an executed run. Labels follow this repository's documented
scope. `artwork.json` holds the copy and visual choices; `artwork.py` draws the
SVGs. The exported SVGs embed the bundled Space Grotesk font; its OFL notice is
in `fonts/OFL.txt`.

From the repository root, regenerate SVGs with Python 3:

```sh
python3 scripts/artwork/artwork.py
```

To also export PNGs, install Playwright in a separate development environment:

```sh
python3 -m venv .artwork-venv
.artwork-venv/bin/pip install playwright pillow
.artwork-venv/bin/playwright install chromium
.artwork-venv/bin/python scripts/artwork/artwork.py --render
```

On Windows, use `.artwork-venv\Scripts\python.exe` and the corresponding
`pip.exe` / `playwright.exe` paths. Outputs go to `assets/presentation/`.
The renderer checks text bounds and intersections before exporting. Optional
`--qa-dir <outside-repository-directory>` saves 840px review copies. No artwork
dependency is used by the application. Do not commit the development environment
or local QA files.
