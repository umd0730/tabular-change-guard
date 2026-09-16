# Verify a CSV cleanup performed by an agent

1. Preserve a baseline outside the agent's editable output location.
2. Agree on keys, editable columns, required fields and preserved totals.
3. Ask the agent to create a separate output CSV.
4. Run Tabular Change Guard locally; only accept exit `0`.
5. Inspect whether allowed changes are sensible for the business task.

Example instruction:

> Normalize whitespace in the team column only. Preserve IDs, all other values,
> every original record, and quantities. Write result.csv without changing
> original.csv. Run the following acceptance check and address violations.

```sh
python -m tabular_change_guard original.csv result.csv --key id --allow team --required team --decimal quantity --sum quantity
```

`--sum` is an additional check, not permission to edit a protected column.
An agent with permission to edit both the original and the output can defeat a
comparison by changing both. Hashes support audit records but do not replace
access control or a trusted baseline. This tool does not sandbox the agent.

The same command works in a CI shell step; retain a nonzero exit code. Do not
append `|| true` or catch and ignore `InputError`. No API credentials are needed.

For repeated checks, store rules in a reviewed JSON contract:

```sh
python -m tabular_change_guard original.csv result.csv --contract rules.json
```

Use the [example contract](../examples/contract.json) as a starting point.
The contract and baseline must be protected from the editing agent. Do not let
an agent weaken `allow`, remove constraints or disable `check_formulas` to obtain
a passing result. Inline rule overrides are rejected when a contract is supplied.
