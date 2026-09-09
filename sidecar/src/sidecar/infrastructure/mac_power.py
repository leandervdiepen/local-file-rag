"""Adapter for the `PowerSource` port, backed by `pmset`.

`pmset -g ps` rather than IOKit through a binding: it is on every Mac, needs
no dependency, and its first line has said the same thing since OS X. Reading
it costs about ten milliseconds and it is read once a minute.
"""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)

AC_POWER = "AC Power"
TIMEOUT_S = 5.0


class MacPowerSource:
    """What `pmset` says the machine is running on."""

    def on_ac_power(self) -> bool:
        """True when plugged in, and when the answer cannot be had.

        A desktop that read as being on battery would never pre-embed
        anything, so an unanswerable question resolves the generous way.
        """
        try:
            result = subprocess.run(
                ["/usr/bin/pmset", "-g", "ps"],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_S,
                check=True,
            )
        except (OSError, subprocess.SubprocessError) as failure:
            logger.warning("cannot read the power source, assuming AC: %s", failure)
            return True
        return AC_POWER in result.stdout.partition("\n")[0]
