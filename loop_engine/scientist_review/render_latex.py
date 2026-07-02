from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def _tex_escape(text: Any) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in str(text))


def render_packet_tex(project: str, packet_md: str, dossiers: list[dict[str, Any]]) -> str:
    rows = "\n".join(
        r"{} & {} & {} & {} \\".format(
            _tex_escape(_short_stage(dossier["stage_id"])),
            _tex_escape(dossier["stage_type"]),
            _tex_escape(dossier["verification"]["type"]),
            _tex_escape(dossier["verification"]["gate"]),
        )
        for dossier in dossiers
    )
    caveat = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."
    return rf"""\documentclass[11pt]{{ctexart}}
\usepackage[margin=1in]{{geometry}}
\usepackage{{booktabs,longtable,tcolorbox,hyperref}}
\hypersetup{{colorlinks=true,linkcolor=blue,urlcolor=blue}}
\title{{Scientist Review Packet: {_tex_escape(project)}}}
\date{{2026-07-02}}
\begin{{document}}
\maketitle

\begin{{tcolorbox}}[title=Purpose]
This packet summarizes existing machine evidence for human scientists. It does
not override validation summaries, completion matrices, freeze preconditions,
review debt, or human signoff.
\end{{tcolorbox}}

\begin{{tcolorbox}}[title=Permanent Caveat]
{_tex_escape(caveat)}
\end{{tcolorbox}}

\section*{{Stage Overview}}
\small
\begin{{longtable}}{{p{{0.24\linewidth}}p{{0.23\linewidth}}p{{0.26\linewidth}}p{{0.10\linewidth}}}}
\toprule
Stage & Stage type & Verification type & Gate \\
\midrule
{rows}
\bottomrule
\end{{longtable}}
\normalsize

\section*{{Allowed Claims}}
\begin{{itemize}}
\item repo-level loop-engine progress review
\item sigma\_abc raw/provenance/projection/prep audit
\item projection-preserving raw tensorial candidate
\item sector ledger and xxx collapse evidence
\end{{itemize}}

\section*{{Forbidden Claims}}
\begin{{itemize}}
\item full tensorial $\sigma_{{\mu\alpha\beta}}$ correctness
\item direct full tensorial DC-series PASS
\item 012C promotion unless actually frozen
\item Stage 013 unless actually started and approved
\item tensorial IBP unless explicitly run and validated
\item total-derivative reduction unless explicitly validated
\end{{itemize}}

\section*{{Source Markdown}}
The complete Markdown packet is generated next to this TeX file.

\end{{document}}
"""


def _short_stage(stage_id: str) -> str:
    replacements = {
        "sigma_abc_006_tensorial_sector_architecture_review": "006 sector architecture",
        "sigma_abc_007_pair_sector_basis_closure_pilot": "007 pair basis closure",
        "sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision": "008 xxx regression",
    }
    return replacements.get(stage_id, stage_id.replace("sigma_abc_", ""))


def try_compile_pdf(tex_path: Path) -> tuple[Path | None, str | None]:
    if shutil.which("xelatex") is None:
        return None, "xelatex not available"
    result = subprocess.run(
        [
            "xelatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory",
            str(tex_path.parent),
            str(tex_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None, result.stderr[-2000:] or result.stdout[-2000:]
    # Second pass for tables/refs.
    subprocess.run(
        [
            "xelatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory",
            str(tex_path.parent),
            str(tex_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    pdf = tex_path.with_suffix(".pdf")
    return (pdf if pdf.exists() else None, None if pdf.exists() else "pdf not produced")
