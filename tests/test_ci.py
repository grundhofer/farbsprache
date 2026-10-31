"""CI: Rechte nach dem Muster der offiziellen Pages-Vorlage, Schreibrechte für Pages und
das OIDC-Token nur im Deploy-Job; die Gruppe pages nur am Deployment, damit ein Lauf eines Pull Requests kein wartendes
Deployment von main abbricht. Ohne YAML-Bibliothek: Blöcke nach Einzug."""
import re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows" / "pages.yml"


def blocks(text):
    """Oberste Schlüssel und die Jobs (Einzug 2 unter jobs:) als {name: Text des Blocks}."""
    out, cur, buf, in_jobs = {}, None, [], False
    for line in text.splitlines():
        top, job = re.match(r"^([a-z-]+):", line), re.match(r"^  ([a-z-]+):\s*$", line) if in_jobs else None
        if top or job:
            if cur:
                out[cur] = "\n".join(buf)
            in_jobs = in_jobs if job else top.group(1) == "jobs"
            cur, buf = ("job:" + job.group(1) if job else top.group(1)), []
        else:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf)
    return out


class TestWorkflow(unittest.TestCase):
    def test_rights_and_concurrency(self):
        text = WF.read_text(encoding="utf-8")
        b = blocks(text)
        self.assertEqual(re.findall(r"[a-z-]+: \w+", b["permissions"]), ["contents: read"], "oben nur Leserechte")
        self.assertNotIn("concurrency", b, "keine gemeinsame Gruppe für PR- und main-Läufe")
        deploy, build = b["job:deploy"], b["job:build"]
        for right in ("pages: write", "id-token: write"):
            self.assertEqual(text.count(right), 1, right)
            self.assertIn(right, deploy)
        self.assertNotIn("write", build)
        self.assertRegex(deploy, r"concurrency:\n\s+group: pages\n\s+cancel-in-progress: false")
        self.assertIn("if: github.event_name == 'push' && github.ref == 'refs/heads/main'", deploy)

    def test_tailwind_job_apart(self):
        """Der Tailwind-Job installiert npm-Pakete in fester Version außerhalb des Repos; build und deploy hängen nicht davon ab."""
        b = blocks(WF.read_text(encoding="utf-8"))
        tw = b["job:tailwind"]
        self.assertNotIn("write", tw)
        self.assertNotRegex(b["job:build"], r"\bnpm (install|ci)\b|\bnpx\b")
        self.assertRegex(b["job:deploy"], r"needs: build\n")
        self.assertRegex(tw, r"tailwindcss@4\.\d+\.\d+ @tailwindcss/cli@4\.\d+\.\d+")
        self.assertIn("--ignore-scripts", tw)
        self.assertIn('--prefix "$RUNNER_TEMP/tw"', tw)
        self.assertIn("tools/tailwind_check.py", tw)


if __name__ == "__main__":
    unittest.main()
