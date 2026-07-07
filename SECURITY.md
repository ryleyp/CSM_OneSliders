# Security and Privacy

EA Slide Builder is designed to run locally. It should not be deployed as a
public web app for real contract or customer data.

## Safe GitHub Use

- Keep this repository for source code only.
- Do not commit real contract screenshots, generated decks, saved profiles,
  exports, spreadsheets, or customer data.
- The app is private by default: Streamlit binds to `127.0.0.1`.
- Saved account profiles live in `profiles/`, which is git-ignored.
- Streamlit telemetry is disabled in `.streamlit/config.toml`.

## Deployment Guidance

For the strictest handling of real customer or contract data, run the app
locally with the provided Mac or Windows launcher. If you connect this
repository to any hosted platform beyond GitHub Pages, treat it as a demo-only
deployment unless your security team explicitly approves the hosting environment
and data handling.

## GitHub Pages Lite

The `docs/` version is static so it can be hosted on GitHub Pages with a smaller
data-handling footprint:

- no backend or server-side processing
- local screenshot selection only; images are read in the browser
- browser-side OCR using vendored same-origin Tesseract.js assets
- PowerPoint generation in the browser using vendored same-origin PptxGenJS/JSZip
- profiles handled as explicit JSON export/import files
- batch decks generated from selected exported profile JSON files
- no external scripts, fonts, CDNs, or APIs
- browser Content Security Policy limited to same-origin static asset loading
- no localStorage or sessionStorage

Entered data remains in the active browser page and is cleared by refresh unless
the user explicitly downloads a profile JSON or PPTX file. Users should still
avoid entering sensitive data on shared or untrusted machines.

## Reporting Issues

If you find a security or privacy issue, fix it in a private branch or report it
through the repository owner's private channel. Do not include customer data,
screenshots, profile JSON, or generated decks in issues or pull requests.
