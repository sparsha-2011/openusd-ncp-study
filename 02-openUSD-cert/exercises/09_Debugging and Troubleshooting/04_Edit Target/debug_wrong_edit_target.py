"""
Debug Exercise — Wrong Edit Target
=====================================
Reproduce and fix the most common silent authoring bug in USD.

TOPIC: stage.GetEditTarget() / stage.SetEditTarget()
WHEN TO USE: You authored a value but the file looks unchanged.
             No error was raised. The value went to the wrong layer.

THE BUG: USD always writes to the current edit target layer.
         If you don't set it explicitly, it defaults to the root layer.
         Writing to the wrong layer silently loses your work.

Run: python debug_wrong_edit_target.py
"""

from pxr import Usd, UsdGeom, Sdf, Gf
import os

SEP = "=" * 65

# ── BUILD THE STAGE ─────────────────────────────────────────────────
root           = Sdf.Layer.CreateAnonymous("shot.usda")
override_layer = Sdf.Layer.CreateAnonymous("artist_override.usda")
model_layer    = Sdf.Layer.CreateAnonymous("model_base.usda")

root.subLayerPaths = [override_layer.identifier, model_layer.identifier]
stage = Usd.Stage.Open(root)

# Define /World as Xform so hierarchy is visible in usdview
stage.SetEditTarget(model_layer)
UsdGeom.Xform.Define(stage, "/World")

# Base model defines the prim
stage.SetEditTarget(model_layer)
UsdGeom.Xform.Define(stage, "/World/Chair")

# Reset to root (the default)
stage.SetEditTarget(root)

prim = stage.GetPrimAtPath("/World/Chair")

# ── STEP 1: REPRODUCE THE BUG ──────────────────────────────────────
print(SEP)
print("  STEP 1 — Reproduce the bug (writing to wrong layer)")
print(SEP)

print(f"\n  Current edit target: "
      f"{os.path.basename(stage.GetEditTarget().GetLayer().identifier)}")
print(f"  (We want to write to artist_override.usda)")
print(f"  (But we forgot to call SetEditTarget)\n")

# BUG: write without setting edit target first
# This goes to root (shot.usda) not override
UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(5, 0, 0))

# Where did the value actually go?
print(f"  After authoring translate (5,0,0):")
print(f"  Composed value: {prim.GetAttribute('xformOp:translate').Get()}")
print()

# Check each layer
print(f"  {'Layer':<30} Has translate opinion?")
print("  " + "-" * 50)
for layer in [root, override_layer, model_layer]:
    lname = os.path.basename(layer.identifier)
    # GetAttributeAtPath returns None if the attr spec doesn't exist
    # calling .IsValid() on None crashes — just check if it's not None
    spec = layer.GetAttributeAtPath(
        Sdf.Path("/World/Chair.xformOp:translate"))
    has_opinion = spec is not None
    marker = " <-- WRONG LAYER" if has_opinion and layer == root else ""
    print(f"  {lname:<30} {has_opinion}{marker}")

print(f"""
  The translate went to shot.usda (root) — NOT artist_override.usda.
  No error. No warning. Silent failure.
  If we save shot.usda and override_layer is empty, our work is lost.
""")

# ── STEP 2: THE FIX ─────────────────────────────────────────────────
print(SEP)
print("  STEP 2 — Fix: always check and set the edit target")
print(SEP)

# ALWAYS check first
current = stage.GetEditTarget().GetLayer()
print(f"\n  Current target:  {os.path.basename(current.identifier)}")
print(f"  Intended target: artist_override.usda")
print(f"  Do they match?   {current.identifier == override_layer.identifier}")

# Set the correct target
stage.SetEditTarget(override_layer)
print(f"\n  After SetEditTarget(override_layer):")
print(f"  Current target:  "
      f"{os.path.basename(stage.GetEditTarget().GetLayer().identifier)}")

# Now author correctly
UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(10, 0, 0))

# Verify it went to the right layer
spec = override_layer.GetAttributeAtPath(
    Sdf.Path("/World/Chair.xformOp:translate"))
print(f"\n  override_layer now has translate: {spec is not None}")
print(f"  Composed value: {prim.GetAttribute('xformOp:translate').Get()}")

# ── STEP 3: CONTEXT MANAGER PATTERN ────────────────────────────────
print()
print(SEP)
print("  STEP 3 — Safer pattern: context manager")
print(SEP)
print("""
  The safest pattern saves the previous target, sets the new one,
  authors the value, then restores the original.
  GetEditTargetContext() exists in some USD builds but not all
  pip-installed versions — use the explicit save/restore instead.

  previous = stage.GetEditTarget()
  stage.SetEditTarget(override_layer)
  prim.GetAttribute("xformOp:translate").Set((15, 0, 0))
  stage.SetEditTarget(previous)   # always restore

  This prevents forgetting to reset the target after authoring.
""")

# Save current target
previous_target = stage.GetEditTarget()
print(f"  Before: edit target = "
      f"{os.path.basename(stage.GetEditTarget().GetLayer().identifier)}")

# Set the target we want
stage.SetEditTarget(override_layer)
prim.GetAttribute("xformOp:translate").Set(Gf.Vec3d(15, 0, 0))
print(f"  During: edit target = "
      f"{os.path.basename(stage.GetEditTarget().GetLayer().identifier)}")

# Always restore
stage.SetEditTarget(previous_target)
print(f"  After restore: edit target = "
      f"{os.path.basename(stage.GetEditTarget().GetLayer().identifier)}")
print(f"  Composed translate: {prim.GetAttribute('xformOp:translate').Get()}")

# ── STEP 4: CHECKLIST ───────────────────────────────────────────────
print()
print(SEP)
print("  STEP 4 — The edit target checklist")
print(SEP)
print("""
  Before EVERY authoring operation ask yourself:

  1. stage.GetEditTarget().GetLayer().identifier
     → Is this the layer I actually want to write to?

  2. stage.SetEditTarget(target_layer)
     → If not, set it before calling any Set() or Define()

  3. Save / restore pattern for scoped authoring:
       previous = stage.GetEditTarget()
       stage.SetEditTarget(target_layer)
       attr.Set(value)
       stage.SetEditTarget(previous)   ← always restore

  4. If value isn't sticking after Save() → check edit target
     → The session layer is never saved to disk
     → stage.SetEditTarget(stage.GetRootLayer()) to write to root
""")

# ── USDVIEW EQUIVALENT + EXPORT ──────────────────────────────────────
print(SEP)
print("  USDVIEW — How to spot the wrong edit target visually")
print(SEP)
print("""
  usdview's LayerStack tab is the fastest way to see which layer
  a value was accidentally written to.

  1. Open usdview:
     .\\scripts\\usdview.bat debug_wrong_edit_target.usda

  2. Click /World/Chair in the Scenegraph

  3. Metadata/Composition → LayerStack tab
     Look at where translate opinions are authored:

     If the bug is present:
     shot.usda (ROOT)          translate = (5,0,0)  ← wrong layer
     artist_override.usda      (no opinion here)

     After the fix:
     artist_override.usda      translate = (10,0,0) ← correct layer
     shot.usda (ROOT)          (no opinion)

  4. The LayerStack tab immediately shows you:
     - Which layer has the opinion
     - Whether it's the layer you intended
     - No code needed — purely visual inspection

  WORKFLOW IN PRODUCTION:
  When a value isn't persisting or went to the wrong place:
  → Open usdview → LayerStack tab → find the opinion
  → If it's in the wrong layer, go to Python and fix the edit target
  → Re-export and verify in usdview again
""")

import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(SCRIPT_DIR, "debug_wrong_edit_target.usda")

path_override = os.path.join(SCRIPT_DIR, "debug_artist_override.usda")
path_model    = os.path.join(SCRIPT_DIR, "debug_model_base.usda")

for p in [path_override, path_model, output_path]:
    if os.path.exists(p): os.remove(p)

override_layer.Export(path_override)
model_layer.Export(path_model)

root_out = Sdf.Layer.CreateNew(output_path)
root_out.subLayerPaths = [
    os.path.basename(path_override),
    os.path.basename(path_model),
]
root_out.Save()
print(f"  Saved → {output_path}")
print(f"  Open in usdview:")
print(f"    .\\scripts\\usdview.bat {output_path}")
print(f"\n  In usdview:")
print(f"    1. Click /World/Chair in Scenegraph")
print(f"    2. Metadata/Composition → LayerStack tab")
print(f"    3. See which layer has the translate opinion")
print(f"    4. Compare against which layer you INTENDED to write to")
