"""Regenerate docs/screenshots/test_run_output.png from the combined suite (13 tests)."""
import subprocess
import matplotlib.pyplot as plt

res = subprocess.run(
    ["python", "-m", "pytest", "tests/test_suite.py", "tests/test_streamlit_ops.py", "-v"],
    capture_output=True, text=True)
out = res.stdout + res.stderr
lines = out.splitlines()
short = "\n".join(lines[-22:])
fig, ax = plt.subplots(figsize=(10, 6))
ax.axis("off")
ax.set_facecolor("#1e1e1e")
fig.patch.set_facecolor("#1e1e1e")
ax.text(0.02, 0.95, "Automated Pytest Execution Output (API + Streamlit ops):\n\n" + short,
        fontsize=8.5, color="#00ff66", family="monospace", va="top")
plt.savefig("docs/screenshots/test_run_output.png", bbox_inches="tight", dpi=150)
plt.close()
print("wrote test_run_output.png,", len(lines), "lines;", res.returncode)
