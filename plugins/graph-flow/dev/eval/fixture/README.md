# textkit fixture

Python 3.9 standard library only. All helpers are pure and their docstrings
specify the contracts that evaluation tasks may later modify. Import from
`textkit.words`, `textkit.config`, or `textkit.sequences`.

Run the visible tests from the repository root without creating bytecode:

```sh
python3 -I -S -B -m unittest discover -s plugins/graph-flow/dev/eval/fixture/tests -t plugins/graph-flow/dev/eval/fixture
```

No installation, network access, or external data is required.
