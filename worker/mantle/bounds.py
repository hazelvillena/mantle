"""Recipe limits. Change them here, not in the modeling calls."""

WALL_MM = 2.6
GAP_MM = 3.0
MIN_SOLID_MM3 = 500.0
INTERFERENCE_MM3 = 8.0
# A passing gap can be a little under the design gap. The loft is an approximation.
MIN_CLEARANCE_MM = 1.6

FULLNESS_MM = {"close": 1.6, "balanced": 6.0, "generous": 13.0}
END_MM = {"short": -8.0, "standard": 4.0, "long": 28.0}
SEAM_MM = {"tight": 0.8, "shadow": 2.2, "open": 4.6}
TAPER = {"none": (1.0, 1.0), "toward-end": (1.0, 0.8), "toward-base": (0.8, 1.0)}

# Parent-frame box just past the far end of the link. Long covers reach it.
KEEP_OUT_PAST_MM = 10.0
KEEP_OUT_SIZE_MM = (46.0, 20.0, 26.0)

# Display mesh only. Absolute millimeters, so a long edge is not coarsened.
# The STEP file stays the solid.
PREVIEW_LINEAR_MM = 0.1
PREVIEW_ANGULAR_RAD = 0.08

POSES = (
    {"id": "extended", "label": "Extended", "degrees": 0.0},
    {"id": "folded", "label": "Folded", "degrees": 50.0},
)

RECIPE_ID = "sleeve"
RECIPE_VERSION = "1"
