# Contributing

Thanks for looking. labunits is a small, single-purpose tool; these
house rules keep changes easy to review.

> **Research / educational tool. Not a medical device.** Conversion
> only: no reference ranges, no flagging, no interpretation.

## Run the tests

```console
$ python3 run_tests.py
```

All tests must pass before a change is considered. Add tests in `tests/`
for any new behaviour.

## House rules

- Keep the tool single-purpose and dependency-free (standard library
  only).
- **A new analyte ships only when its factor verifies against two
  independent authorities**, with both recorded in
  `labunits/analytes.py` the way the existing entries record theirs.
  The molar-mass re-derivation test must pass for molar factors.
  One-source factors will not be accepted — that rule is the product.
- Refusals stay refusals: an analyte whose published factors disagree,
  or whose conversion is method-dependent, belongs in the refused
  table with its reason, not in the shipped table.
- The README's Honest limits section is a promise. If a change alters
  a documented limit or behaviour, update the README in the same pull
  request — and SKILL.md too if the CLI, its flags or its exit codes
  changed.
- Plain words in docs and messages. No marketing language.

## Claiming an issue

Comment on the issue saying you are taking it, then open a pull request
that mentions the issue number.
