"""
Debug Exercise — HasAuthoredValue
===================================
Distinguish an explicitly authored value from a schema fallback.

TOPIC: attr.Get() returns a value whether the attribute was
explicitly Set() or is just the schema default. HasAuthoredValue()
is the only way to tell which case you are in. Critical for
debugging zeros and defaults that may or may not be intentional.

Run: python debug_authored_value_vs_fallback.py
"""

from pxr import Usd, UsdGeom, Sdf

SEP = "=" * 65

print(f"\n{SEP}")
print("  HasAuthoredValue — Authored value vs schema fallback")
print(SEP)

print("""
SCENARIO:
  Three spheres all show radius = 1.0 from Get().
  But were they explicitly Set() or is that just the schema default?
  HasAuthoredValue() is the ONLY way to tell them apart.
""")

stage = Usd.Stage.CreateInMemory()

# Sphere 1 — never touched, uses schema default
sphere_default = UsdGeom.Sphere.Define(stage, "/Sphere_NeverTouched")
print("  /Sphere_NeverTouched — radius never Set(), using schema default")

# Sphere 2 — explicitly set to 1.0 (same as default)
sphere_authored_default = UsdGeom.Sphere.Define(stage, "/Sphere_SetToDefault")
sphere_authored_default.GetRadiusAttr().Set(1.0)
print("  /Sphere_SetToDefault — radius Set() to 1.0 explicitly")

# Sphere 3 — set to a custom value
sphere_custom = UsdGeom.Sphere.Define(stage, "/Sphere_Custom")
sphere_custom.GetRadiusAttr().Set(3.5)
print("  /Sphere_Custom — radius Set() to 3.5")

# Sphere 4 — show what Block() does
sphere_blocked = UsdGeom.Sphere.Define(stage, "/Sphere_Blocked")
sphere_blocked.GetRadiusAttr().Set(7.0)
sphere_blocked.GetRadiusAttr().Block()
print("  /Sphere_Blocked — radius Set() to 7.0 then Block()'d")

print(f"\n  {'Prim':<30} {'Get()':<12} {'HasAuthoredValue':<18} Meaning")
print("  " + "-" * 75)

cases = [
    ("/Sphere_NeverTouched",    sphere_default,          "Schema fallback — nobody touched this"),
    ("/Sphere_SetToDefault",    sphere_authored_default, "Explicitly Set() to 1.0 — intentional"),
    ("/Sphere_Custom",          sphere_custom,           "Explicitly Set() to 3.5 — intentional"),
    ("/Sphere_Blocked",         sphere_blocked,          "Blocked — attribute made absent"),
]

for path, sphere, meaning in cases:
    attr     = sphere.GetRadiusAttr()
    val      = attr.Get()
    authored = attr.HasAuthoredValue()
    print(f"  {path:<30} {str(val):<12} {str(authored):<18} {meaning}")

print(f"""
WHAT YOU SHOULD SEE:
  /Sphere_NeverTouched   1.0  False  → Schema fallback. radius not in any layer.
  /Sphere_SetToDefault   1.0  True   → Intentionally Set() to 1.0.
  /Sphere_Custom         3.5  True   → Intentionally Set() to 3.5.
  /Sphere_Blocked        None False  → Block() made it absent. Get() = None.

KEY INSIGHT:
  /Sphere_NeverTouched and /Sphere_SetToDefault BOTH return 1.0 from Get().
  They look identical. Only HasAuthoredValue() reveals the difference.

WHY THIS MATTERS FOR DEBUGGING:
  - "Is this 0 because someone set it to 0, or because 0 is the default?"
  - "Was this path intentionally left empty?"
  - "Is this transform identity because it was authored, or never touched?"
  HasAuthoredValue() answers all of these.

RELATED:
  attr.GetPropertyStack() — if no specs → nothing authored → fallback
  If HasAuthoredValue() is False and Get() returns a value → schema default
  If HasAuthoredValue() is False and Get() returns None → no fallback either
""")

# ── USDVIEW EQUIVALENT + EXPORT ──────────────────────────────────────
print("\n" + "=" * 65)
print("  USDVIEW — How to see authored vs fallback visually")
print("=" * 65)
print("""
  usdview shows authored values differently from fallback values
  in its Properties panel.

  1. Open usdview:
     .\\scripts\\usdview.bat debug_authored_value_vs_fallback.usda

  2. Click /Sphere_Default in the Scenegraph

  3. Properties panel → find 'radius'
     Value shows: 1.0
     The value appears in a MUTED/GREY colour
     This means: schema fallback — nobody has Set() this attribute
     HasAuthoredValue() = False

  4. Click /Sphere_Authored in the Scenegraph

  5. Properties panel → find 'radius'
     Value shows: 1.0
     The value appears in a NORMAL/BRIGHT colour
     This means: explicitly authored — someone called Set(1.0)
     HasAuthoredValue() = True

  6. Click /Sphere_Custom in the Scenegraph
     radius = 3.5 in bright colour → explicitly authored

  The colour difference in usdview Properties panel is the
  visual equivalent of HasAuthoredValue().
  Grey/muted = fallback.  Normal = authored.
""")

from pxr import Usd, UsdGeom
import os

# Rebuild stage for export (original stage was in-memory)
export_stage = Usd.Stage.CreateInMemory()
s1 = UsdGeom.Sphere.Define(export_stage, "/Sphere_Default")
s2 = UsdGeom.Sphere.Define(export_stage, "/Sphere_Authored")
s2.GetRadiusAttr().Set(1.0)
s3 = UsdGeom.Sphere.Define(export_stage, "/Sphere_Custom")
s3.GetRadiusAttr().Set(3.5)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(SCRIPT_DIR, "debug_authored_value_vs_fallback.usda")
export_stage.Export(output_path)
print(f"  Saved → {output_path}")
print(f"  Open in usdview:")
print(f"    .\\scripts\\usdview.bat {output_path}")
print(f"\n  In usdview:")
print(f"    1. Click each sphere in Scenegraph")
print(f"    2. Properties panel → radius attribute")
print(f"       /Sphere_Default  → radius grey/muted (fallback)")
print(f"       /Sphere_Authored → radius bright (authored = 1.0)")
print(f"       /Sphere_Custom   → radius bright (authored = 3.5)")