---
name: cowork-env-probe
description: >
  Diagnostic skill that reports what Copilot Cowork's execution environment can do: whether
  it can run Python scripts bundled with a skill, which Python packages and command-line tools
  are installed (python-pptx, Pillow, LibreOffice, node, pptxgenjs, browsers), which fonts are
  available, and which paths are writable. Use only when the user says "probe the
  environment", "run the env probe", "what can the sandbox run", or "check installed
  libraries". Do NOT use for normal tasks.
---

# Overview
This skill answers one question: what can a skill actually run inside Cowork? It runs a
read-only inventory script and saves the results as a report, so other skills can be
designed around the tools that really exist.

# Instructions
1. **List your own tools.** Write down the exact names of every tool or function available to you in this session, for example file, code-execution, or Office tools. Copy the names exactly as they appear, without paraphrasing.
2. **Try to run the probe.** Run `scripts/probe_env.py` from this skill's folder with Python 3:
   `python3 scripts/probe_env.py --out cowork-env-report.md`
   - If you have no way to execute code, don't simulate it. Report "NO CODE EXECUTION AVAILABLE" and the reason, then skip to step 4.
   - If the script fails, record the full error message verbatim.
3. **Run two extra checks**, if you can execute code:
   - Run `python3 -c "import pptx, sys; print(pptx.__version__, sys.version)"`.
   - Write a one-slide test deck with python-pptx to `probe-test.pptx`, and report whether it was saved and where.
4. **Save the report.** Combine the tool list, the probe output, the extra checks, and any errors into `cowork-env-report.md`. Save it to `Documents/Cowork/cowork-env-report.md` in OneDrive, or to the session's output folder if you can't write there. Tell the user exactly where it was saved.
5. **Summarize in 5 lines or fewer:**
   - whether code execution is available
   - the Python version
   - whether python-pptx, Pillow, and lxml are installed
   - whether a renderer is installed (LibreOffice, pdftoppm, or a browser)
   - whether node and pptxgenjs are installed

# Guardrails
- Never fabricate results. Report a step you couldn't run as "not run", with the reason.
- Don't install packages or make network calls. This probe is read-only.
- Don't send the report anywhere. Only save it.
