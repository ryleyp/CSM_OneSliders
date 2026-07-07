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

For real customer or contract data, run the app locally with the provided Mac or
Windows launcher. If you connect this repository to any hosted platform, treat it
as a demo-only deployment unless your security team explicitly approves the
hosting environment and data handling.

## Reporting Issues

If you find a security or privacy issue, fix it in a private branch or report it
through the repository owner's private channel. Do not include customer data,
screenshots, profile JSON, or generated decks in issues or pull requests.
