# Maintained upstream patches

Patch order is lexical. `git apply --check` must pass before every application.
Never silently skip a conflicting patch. Source pins live in `upstreams.json`.

| Patch | Purpose | Validation |
| --- | --- | --- |
| PdfCraft 0001 | Honor `PDFCRAFT_CONFIG_DIR` for settings, recovery and portable data across version-directory changes | Adds `override_directory_survives_version_folder_changes`; run portable module tests in application CI |
| PdfCraft 0002 | Replace restricted ArtCraft artwork with a community-build label/spacing | Packaging test verifies there are no brand `include_bytes!` calls in patched widgets; native UI build |
| PhotoCraft | No application patch required at the initial source pin | Uses existing `PHOTOCRAFT_CONFIG_DIR` |

All updater/launcher changes are part of this repository, not uncommitted edits
in a developer's upstream checkout. Every release records the patch-set digest.
