Keep an optional append-only record of calls, arguments and touched content.
The log preserves evidence for auditing silent or partial successes, while
its own failures are isolated so logging can never break a store operation.
