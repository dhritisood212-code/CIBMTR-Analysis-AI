import { useEffect, useState } from "react";
import { api, parseMatchReport, url } from "./api";
import { DEMO_MATCH_REPORT, DEMO_RUN, DEMO_SCRIPT, DEMO_STUDY } from "./fixtures";
import { ArtifactBundle } from "./components/ArtifactBundle";
import { ComplianceGate } from "./components/ComplianceGate";
import { MatchReportView } from "./components/MatchReportView";
import { RunProgress } from "./components/RunProgress";
import { StudyCatalog } from "./components/StudyCatalog";
import { UploadRun, type LaunchBody } from "./components/UploadRun";
import type { MatchReport, RunState, RunStatus, StudyCatalogEntry } from "./types";

type Tab = "studies" | "upload";
const TERMINAL: RunStatus[] = ["passed", "partial", "failed", "error"];

export default function App() {
  const [studies, setStudies] = useState<StudyCatalogEntry[]>([]);
  const [demo, setDemo] = useState(false);
  const [tab, setTab] = useState<Tab>("studies");
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

  async function launch(body: LaunchBody) {
    if (demo) {
      setRun(DEMO_RUN);
      setReport(DEMO_MATCH_REPORT);
      setScript(DEMO_SCRIPT);
      return;
    }
    setRun(await api.startRun(body));
  }

  function reset() {
    setRun(null);
    setReport(null);
    setScript("");
    setPicked(null);
  }

  function download(name: string) {
    if (demo || !run) return alert(`In live mode this downloads ${name} from the run bundle.`);
    window.open(url(`/runs/${run.run_id}/artifacts/${name}`), "_blank");
  }

  const done = run != null && TERMINAL.includes(run.status);

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

      {run ? (
        <>
          <RunProgress run={run} />
          {done && report && <MatchReportView report={report} />}
          {done && <ArtifactBundle run={run} script={script} onDownload={download} />}
          {done && (
            <button className="secondary" onClick={reset}>← New reproduction</button>
          )}
        </>
      ) : (
        <>
          <div className="topnav">
            <button className={tab === "studies" ? "active" : ""}
                    onClick={() => { setTab("studies"); setPicked(null); }}>
              Studies
            </button>
            <button className={tab === "upload" ? "active" : ""}
                    onClick={() => setTab("upload")}>
              Upload &amp; run
            </button>
          </div>

          {tab === "studies" ? (
            picked ? (
              <ComplianceGate
                study={picked}
                onBack={() => setPicked(null)}
                onStart={(opts) =>
                  launch({
                    study_id: picked.study_id,
                    tc_confirmed: opts.tc,
                    primary_endpoint: opts.endpoint,
                    dataset: opts.dataset,
                    dictionary: opts.dictionary,
                  })
                }
              />
            ) : (
              <StudyCatalog studies={studies} onPick={setPicked} />
            )
          ) : (
            <UploadRun studies={studies} onLaunch={launch} />
          )}
        </>
      )}
    </div>
  );
}
