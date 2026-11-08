#!/usr/bin/env python3
"""Exercise the production answer formatter with malformed and valid values."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = root / 'skills/mac-computer-use/scripts/mac-cu-src'
text = (source / 'Decide.swift').read_text()
zone = text[text.index('struct Zone {'):text.index('/// Limit the size')]
formatter = text[text.index('func answerText('):text.index('\nfunc decideTool(')]
test = r'''
@main struct Checks {
    static func main() {
        let bad: [[String: Any]] = [
            ["type": "predicate", "probability": true], ["type": "predicate", "probability": Double.nan],
            ["type": "choice", "choice": "x", "confidence": 1.0],
            ["type": "choice", "choice": "x", "confidence": true, "probabilities": ["x": 1.0, "y": 0.0]],
            ["type": "choice", "choice": "z", "confidence": 1.0, "probabilities": ["x": 1.0, "y": 0.0]],
            ["type": "score", "score": true, "confidence": 1.0, "probabilities": ["0": 0.0, "1": 1.0]],
            ["type": "score", "score": Double.nan, "confidence": 1.0, "probabilities": ["0": 0.0, "1": 1.0]],
            ["type": "score", "score": 1.0, "confidence": 1.0],
            ["type": "score", "score": 1.0, "confidence": 1.0, "probabilities": ["0": 0.9, "1": 0.1]]
        ]
        for value in bad { precondition(!answerText(value, zone: treeZone).1) }
        precondition(!answerText(["type": "score", "score": 0.25, "confidence": 0.8, "probabilities": ["0": 0.75, "1": 0.25]], zone: treeZone).1)
        print("decision answer self-check passed")
    }
}
'''
with tempfile.TemporaryDirectory() as folder:
    main = Path(folder) / 'check.swift'
    main.write_text('import Foundation\n' + zone + formatter + test)
    binary = Path(folder) / 'check'
    subprocess.run(['swiftc', '-parse-as-library', str(source / 'DecisionService.swift'), str(main), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
