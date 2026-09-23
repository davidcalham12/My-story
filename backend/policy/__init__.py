"""The forbidden-words guardrail and the audit log it writes to.

Two modules, split along the line that matters: `forbidden` decides, `audit`
records. A detector that writes its own log tends to stop writing it the day
someone calls it from a second place.
"""
