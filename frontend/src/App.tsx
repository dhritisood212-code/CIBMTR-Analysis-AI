import { useEffect, useState } from "react";
import { api, parseMatchReport, url } from "./api";
import { DEMO_MATCH_REPORT, DEMO_RUN, DEMO_SCRIPT, DEMO_STUDY } from "./fixtures";
import { ArtifactBundle } from "./components/ArtifactBundle";
import { ComplianceGate, type StartOpts } from "./components/ComplianceGate";
import { MatchReportView } from "./components/MatchReportView";
import { RunProgress } from "./components/RunProgress";
import { StudyCatalog } from "./components/StudyCatalog";
import type { MatchReport, RunState, RunStatus, StudyCatalogEntry } from "./types";

type Screen = "catalog" | "setup" | "run";
const TERMINAL: RunStatus[] = ["passed", "partial", "failed", "error"];

export default function App() {
  const [studies, setStudies] = useState<StudyCatalogEntry[]>([]);
  const [demo, setDemo] = useState(false);
  const [screen, setScreen] = useState<Screen>("catalog");
  const [picked, setPicked] = useState<StudyCatalogEntry | null>(null);
  const [run, setRun] = useState<RunState | null>(null);
  const [report, setReport] = useState<MatchReport | null>(null);
  const [script, setScript] = useState<string>("");

  // On load: try the live API; if unreachable, drop into demo mode with the bundled fixtures.
  useEffect(() => {
    api
      .listStudies()
      .then(setStudies)
      .catch(() => {
        setDemo(true);
        setStudies([DEMO_STUDY]);
      });
  }, []);

  // Live mode: poll the run until it reaches a terminal state, then load its artifacts.
  useEffect(() => {
    if (demo || !run || TERMINAL.includes(run.status)) return;
    const id = setInterval(async () => {
      const next = await api.getRun(run.run_id);
      setRun(next);
      if (TERMINAL.includes(next.status)) {
        clearInterval(id);
        if (next.artifacts.includes("match-report.md")) {
          setReport(parseMatchReport(await api.getArtifact(next.run_id, "match-report.md")));
        }
        const rfile = next.artifacts.find((a) => a.endsWith(".R"));
        if (rfile) setScript(await api.getArtifact(next.run_id, rfile));
      }
    }, 1200);
    return () => clearInterval(id);
  }, [demo, run]);

  function pick(s: StudyCatalogEntry) {
    setPicked(s);
    setScreen("setup");
  }

  async function start({ tc, endpoint, dataset, dictionary }: StartOpts) {
    if (!picked) return;
    setScreen("run");
    if (demo) {
      setRun(DEMO_RUN);
      setReport(DEMO_MATCH_REPORT);
      setScript(DEMO_SCRIPT);
      return;
    }
    const started = await api.startRun({
      study_id: picked.study_id,
      tc_confirmed: tc,
      primary_endpoint: endpoint,
      dataset,
      dictionary,
    });
    setRun(started);
  }

  function download(name: string) {
    if (demo || !run) return alert(`In live mode this downloads ${name} from the run bundle.`);
    window.open(url(`/runs/${run.run_id}/artifacts/${name}`), "_blank");
  }

  const done = run && TERMINAL.includes(run.status);

  return (
    <div className="app">
      <div className="masthead">
        <h1>CIBMTR Reproduction Panel</h1>
        <span className="tag">artifact viewer{demo ? " · demo mode (no backend)" : ""}</span>
      </div>
      <div className="disclaimer">
        Research/educational secondary-analysis tool. Not medical advice, not a clinical or
        regulatory instrument. Outputs are drafts for expert review. The app stores only study
        metadata and links; it never hosts CIBMTR datasets. CIBMTR did not review or endorse any
        analysis produced here.
      </div>

      {screen === "catalog" && <StudyCatalog studies={studies} onPick={pick} />}

      {screen === "setup" && picked && (
        <ComplianceGate study={picked} onStart={start} onBack={() => setScreen("catalog")} />
      )}

      {screen === "run" && run && (
        <>
          <RunProgress run={run} />
          {done && report && <MatchReportView report={report} />}
          {done && <ArtifactBundle run={run} script={script} onDownload={download} />}
          {done && (
            <button className="secondary" onClick={() => { setScreen("catalog"); setRun(null); setReport(null); }}>
              ← New reproduction
            </button>
          )}
        </>
      )}
    </div>
  );
}
