"""
Debug Exercise — Namespace Collision
=======================================
Reproduce, detect, and fix path collisions between layers.

TOPIC: Namespace/path collision detection and repair
WHEN TO USE: Prims appear at unexpected locations, have wrong values,
             or data from one asset is appearing on a different prim.

SYMPTOM: prim.GetPrimStack() shows specs from two unrelated layers
         at the same path — when you expected only one.

Run: python debug_namespace_collision.py
"""

from pxr import Usd, UsdGeom, Sdf, Gf
import os

SEP = "=" * 65

# ── PART A: REPRODUCE THE COLLISION ────────────────────────────────
print(SEP)
print("  PART A — Reproducing a namespace collision")
print(SEP)
print("""
  SCENARIO:
  Two separate assets both define a prim at /World/Chair.
  Both are sublayered into the same shot. Their opinions compose
  unexpectedly — the stronger layer wins silently.
""")

root         = Sdf.Layer.CreateAnonymous("shot.usda")
office_layer = Sdf.Layer.CreateAnonymous("office_chair_asset.usda")
dining_layer = Sdf.Layer.CreateAnonymous("dining_chair_asset.usda")

# BOTH assets define a prim at THE SAME PATH — collision
root.subLayerPaths = [office_layer.identifier, dining_layer.identifier]
stage = Usd.Stage.Open(root)

# Define /World as Xform so hierarchy is visible in usdview
stage.SetEditTarget(office_layer)
UsdGeom.Xform.Define(stage, "/World")

# Office chair — wooden
stage.SetEditTarget(office_layer)
UsdGeom.Xform.Define(stage, "/World/Chair")
prim = stage.GetPrimAtPath("/World/Chair")
prim.CreateAttribute("chair:material",
                     Sdf.ValueTypeNames.String).Set("wood")
prim.CreateAttribute("chair:height",
                     Sdf.ValueTypeNames.Float).Set(90.0)

# Dining chair — metal — same path = COLLISION
stage.SetEditTarget(dining_layer)
UsdGeom.Xform.Define(stage, "/World/Chair")
prim = stage.GetPrimAtPath("/World/Chair")
prim.CreateAttribute("chair:material",
                     Sdf.ValueTypeNames.String).Set("metal")
prim.CreateAttribute("chair:height",
                     Sdf.ValueTypeNames.Float).Set(75.0)

stage.SetEditTarget(root)
prim = stage.GetPrimAtPath("/World/Chair")

# Read composed values
mat    = prim.GetAttribute("chair:material").Get()
height = prim.GetAttribute("chair:height").Get()

print(f"  Composed material: '{mat}'   (expected to have BOTH chairs)")
print(f"  Composed height:   {height}  (office wins because index 0)")
print(f"  → The dining chair data is SILENTLY OVERRIDDEN")

# ── PART B: DETECT THE COLLISION ────────────────────────────────────
print()
print(SEP)
print("  PART B — Detecting the collision with PrimStack")
print(SEP)

print(f"\n  PrimStack for /World/Chair:")
print(f"  {'Index':<7} {'Layer':<35} Observation")
print("  " + "-" * 65)

for i, spec in enumerate(prim.GetPrimStack()):
    lname = os.path.basename(spec.layer.identifier)
    obs = "← WINS (index 0)" if i == 0 else "← OVERRIDDEN"
    print(f"  [{i}]    {lname:<35} {obs}")

print(f"""
  RED FLAG: Two UNRELATED asset layers contributing to the same path.
  You expected exactly ONE asset at /World/Chair.
  PrimStack shows two — that is the collision.
""")

# Show PropertyStack for material to confirm
attr = prim.GetAttribute("chair:material")
print(f"  PropertyStack for chair:material:")
for i, spec in enumerate(attr.GetPropertyStack(Usd.TimeCode.Default())):
    lname = os.path.basename(spec.layer.identifier)
    winner = " ← this value wins" if i == 0 else ""
    print(f"  [{i}] {lname:<35} value='{spec.default}'{winner}")

# ── PART C: FIX THE COLLISION ────────────────────────────────────────
print()
print(SEP)
print("  PART C — Fixing the collision: unique namespace paths")
print(SEP)
print("""
  FIX: Reference each asset at a DIFFERENT path in the namespace.
  /World/OfficeArea/Chair  ← office_chair_asset.usda
  /World/DiningArea/Chair  ← dining_chair_asset.usda
  Now they are in different namespaces — no collision possible.
""")

root2 = Sdf.Layer.CreateAnonymous("shot_fixed.usda")
stage2 = Usd.Stage.Open(root2)
stage2.SetEditTarget(root2)

# Each asset at a unique path
office = UsdGeom.Xform.Define(stage2, "/World/OfficeArea/Chair")
office.GetPrim().CreateAttribute("chair:material",
    Sdf.ValueTypeNames.String).Set("wood")
office.GetPrim().CreateAttribute("chair:height",
    Sdf.ValueTypeNames.Float).Set(90.0)

dining = UsdGeom.Xform.Define(stage2, "/World/DiningArea/Chair")
dining.GetPrim().CreateAttribute("chair:material",
    Sdf.ValueTypeNames.String).Set("metal")
dining.GetPrim().CreateAttribute("chair:height",
    Sdf.ValueTypeNames.Float).Set(75.0)

print(f"  /World/OfficeArea/Chair  material: "
      f"'{stage2.GetPrimAtPath('/World/OfficeArea/Chair').GetAttribute('chair:material').Get()}'")
print(f"  /World/OfficeArea/Chair  height:   "
      f"{stage2.GetPrimAtPath('/World/OfficeArea/Chair').GetAttribute('chair:height').Get()}")
print()
print(f"  /World/DiningArea/Chair  material: "
      f"'{stage2.GetPrimAtPath('/World/DiningArea/Chair').GetAttribute('chair:material').Get()}'")
print(f"  /World/DiningArea/Chair  height:   "
      f"{stage2.GetPrimAtPath('/World/DiningArea/Chair').GetAttribute('chair:height').Get()}")

print("""
  Both chairs coexist. Neither overrides the other.
  Each PrimStack now shows exactly ONE layer — clean.
""")

# ── PART D: PATH MISMATCH (CASE SENSITIVITY) ────────────────────────
print(SEP)
print("  PART D — Case sensitivity: path mismatch")
print(SEP)
print("""
  USD prim paths are CASE-SENSITIVE.
  /World/Chair and /World/chair are completely different prims.
  An override at /World/chair will NEVER apply to /World/Chair.
""")

stage3 = Usd.Stage.CreateInMemory()

# Define with capital C
UsdGeom.Xform.Define(stage3, "/World/Chair")

# Try to get with lowercase c
wrong = stage3.GetPrimAtPath("/World/chair")
right = stage3.GetPrimAtPath("/World/Chair")

print(f"\n  GetPrimAtPath('/World/Chair').IsValid(): {right.IsValid()}")
print(f"  GetPrimAtPath('/World/chair').IsValid(): {wrong.IsValid()}")
print(f"""
  If your override isn't applying: check for case mismatch.
  This is one of the most common subtle path bugs.
""")

# ── USDVIEW EQUIVALENT + EXPORT ──────────────────────────────────────
print(SEP)
print("  USDVIEW — How namespace collisions appear visually")
print(SEP)
print("""
  usdview makes namespace collisions very visible — you see
  unexpected prims or wrong attribute values in the Scenegraph.

  COLLISION STAGE:
  1. .\\scripts\\usdview.bat debug_namespace_collision.usda

  2. In the Scenegraph panel:
     /World/Chair exists — but which chair is it?

  3. Click /World/Chair → Properties panel
     chair:material = 'wood'   (office won — it was index 0)
     chair:height   = 90.0
     The dining chair data is gone — silently overridden.

  4. Metadata/Composition → LayerStack tab
     RED FLAG: You see TWO unrelated asset layers:
       office_chair_asset.usda  ← contributing to /World/Chair
       dining_chair_asset.usda  ← also contributing to /World/Chair
     When you expected only ONE — that's the collision.

  FIXED STAGE:
  5. .\\scripts\\usdview.bat debug_namespace_collision_fixed.usda

  6. Scenegraph panel shows:
     /World/OfficeArea/Chair
     /World/DiningArea/Chair
     Two separate prims. Neither overrides the other.

  7. Click each → Properties panel
     Each shows its own correct material and height.
     LayerStack tab shows ONLY ONE layer for each.

  The LayerStack tab showing multiple unrelated layers = collision.
  LayerStack tab showing one layer = clean, no collision.
""")

import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Export collision stage
out_collision = os.path.join(SCRIPT_DIR, "debug_namespace_collision.usda")
path_office = os.path.join(SCRIPT_DIR, "debug_nc_office_asset.usda")
path_dining = os.path.join(SCRIPT_DIR, "debug_nc_dining_asset.usda")

for p in [path_office, path_dining, out_collision]:
    if os.path.exists(p): os.remove(p)

office_layer.Export(path_office)
dining_layer.Export(path_dining)

root_out = Sdf.Layer.CreateNew(out_collision)
root_out.subLayerPaths = [
    os.path.basename(path_office),
    os.path.basename(path_dining),
]
root_out.Save()
print(f"  Collision stage saved → {out_collision}")

# Export fixed stage
out_fixed = os.path.join(SCRIPT_DIR, "debug_namespace_collision_fixed.usda")
stage2.Export(out_fixed)
print(f"  Fixed stage saved → {out_fixed}")

print(f"""
  Open both in usdview and compare:
    .\\scripts\\usdview.bat {out_collision}
    .\\scripts\\usdview.bat {out_fixed}

  Collision stage:
    Click /World/Chair → LayerStack tab
    → See BOTH asset layers contributing to same path
    → chair:material = 'wood' (dining chair data is lost)

  Fixed stage:
    Click /World/OfficeArea/Chair → LayerStack tab → one layer only
    Click /World/DiningArea/Chair → LayerStack tab → one layer only
    Each chair has its correct independent data.
""")