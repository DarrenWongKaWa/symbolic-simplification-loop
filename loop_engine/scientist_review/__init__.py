"""Human-facing scientist review packet generation.

This package summarizes existing loop evidence for human scientists. It is
read-only with respect to stage trust-stack state: it must not override
validation summaries, completion matrices, freeze preconditions, review debt,
or human signoff.
"""

from .stage_dossier import ScientistReviewPacket, build_scientist_review_packet

__all__ = ["ScientistReviewPacket", "build_scientist_review_packet"]
