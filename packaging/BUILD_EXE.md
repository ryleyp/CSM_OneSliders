# Building a double-click .exe (no Python needed to run it)

This turns EA Slide Builder into a folder containing **`EA Slide Builder.exe`**
that teammates can run with a double-click — no Python, no pip, no setup.

## Important notes up front

- **Build on the target OS.** A Windows `.exe` must be built **on Windows**
  (PyInstaller cannot cross-compile). A Mac build works the same way on macOS
  (it produces a Unix executable there).
- The build machine needs Python + the repo; the machines that *run* the exe
  need neither.
- **Screenshot OCR still needs Tesseract** installed on each machine that uses
  it (the app works without it — fields can be typed manually).
- Streamlit inside PyInstaller is officially unsupported territory; the spec
  here includes the known-required metadata/data hooks, but if a build fails,
  send the error output and it can usually be fixed by adding a missing module
  to the spec.

## Build steps (Windows)

1. Clone the repo on the Windows machine (see the WALKTHROUGH).
2. Double-click **`packaging\build_exe.bat`** (or run it from a terminal in the
   project root). It creates the venv, installs dependencies + PyInstaller, and
   builds from `packaging/ea-slide-builder.spec`.
3. When it finishes, the result is the folder **`dist\EA Slide Builder\`**.

## Distributing

- Copy the whole `dist\EA Slide Builder\` folder to the target machine
  (zip it, shared drive, USB — it's self-contained).
- Teammates double-click **`EA Slide Builder.exe`** inside it. A console window
  opens (that's the server — keep it open), and the browser opens to
  `http://localhost:8501`.
- It runs **private** (localhost only) and fully offline, same as the script
  version. Each user's saved profiles live in a `profiles/` folder next to the
  exe and stay on that machine.

## Verifying a build

From the project root on the build machine:

```
python -m tests.run_all
```

should pass before you build, and the built exe should open the app in a
browser with the System check expander showing all packages present.
