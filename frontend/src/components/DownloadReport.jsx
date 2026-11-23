import React, { useState } from "react";
import { api } from "../lib.js";
import { printReport } from "../reportDoc.js";
import { Icon } from "./ui.jsx";

/** Button that builds the printable report for one capture (with its saved brief) and opens "Save as PDF". */
export default function DownloadReport({ capture, className = "btn-ghost" }) {
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true);
    try {
      let brief = capture.brief;
      // The stored brief is returned at once; it is only written (by the language model) if this report has none yet.
      if (capture.summary.opinions) brief = await api.brief(capture.id).catch(() => brief);
      printReport({ ...capture, brief });
    } catch (e) {
      window.alert(`Could not build the report: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };
  return (
    <button className={className} onClick={run} disabled={busy} title="Opens the print dialog; choose Save as PDF">
      <Icon name="download" className="h-4 w-4" />{busy ? "Preparing…" : "Download report"}
    </button>
  );
}
