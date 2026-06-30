"""
UsdGeomImageable — VISIBILITY DEMO
====================================
This script ONLY covers visibility.
Run it, open the .usda in usdview, and see which spheres appear.

KEY RULE:
  "invisible"  →  hidden
  "inherited"  →  visible (there is no "visible" token!)

After running open in usdview:
  .\\scripts\\usdview.bat visibility_demo.usda
Then press F to frame all geometry.
"""

import os
from pxr import Usd, UsdGeom, Gf

# Always overwrite — no "file already exists" problem
stage = Usd.Stage.CreateInMemory()
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(stage, 0.01)

# ─────────────────────────────────────────────────────────
# BUILD THE SCENE
# Three spheres under one parent
# Spread out so they don't overlap
# ─────────────────────────────────────────────────────────
parent  = UsdGeom.Xform.Define(stage,  "/World/Parent")

red     = UsdGeom.Sphere.Define(stage, "/World/Parent/RedSphere")
green   = UsdGeom.Sphere.Define(stage, "/World/Parent/GreenSphere")
blue    = UsdGeom.Sphere.Define(stage, "/World/Parent/BlueSphere")

UsdGeom.XformCommonAPI(red).SetTranslate(Gf.Vec3d(-5, 0, 0))
UsdGeom.XformCommonAPI(green).SetTranslate(Gf.Vec3d(0, 0, 0))
UsdGeom.XformCommonAPI(blue).SetTranslate(Gf.Vec3d(5, 0, 0))

red.GetDisplayColorAttr().Set([(1.0, 0.0, 0.0)])
green.GetDisplayColorAttr().Set([(0.0, 1.0, 0.0)])
blue.GetDisplayColorAttr().Set([(0.0, 0.0, 1.0)])

# ─────────────────────────────────────────────────────────
# EXPERIMENT 1 — hide only the red sphere directly
# Expected in usdview: green ✅  blue ✅  red ❌
# ─────────────────────────────────────────────────────────
UsdGeom.Imageable(red.GetPrim()).MakeInvisible()
# Sets:  token visibility = "invisible"  on RedSphere only
# Green and Blue have visibility = "inherited" → they are VISIBLE

print("=== EXPERIMENT 1 — Red sphere hidden directly ===")
print("RedSphere   authored:", red.GetPrim().GetAttribute("visibility").Get())
print("GreenSphere authored:", green.GetPrim().GetAttribute("visibility").Get())
print()
print("RedSphere   computed:", UsdGeom.Imageable(red.GetPrim()).ComputeVisibility())
print("GreenSphere computed:", UsdGeom.Imageable(green.GetPrim()).ComputeVisibility())
print("BlueSphere  computed:", UsdGeom.Imageable(blue.GetPrim()).ComputeVisibility())
print()
print("Expected in usdview:  Green ✅  Blue ✅  Red ❌")

# Save experiment 1
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
path1 = os.path.join(SCRIPT_DIR, "visibility_exp1.usda")
stage.Export(path1)
print(f"Saved → {path1}")
print()

# ─────────────────────────────────────────────────────────
# EXPERIMENT 2 — hide the PARENT
# This hides ALL children even though they say "inherited"
# Because "inherited" means "ask my parent" — and parent says invisible
# Expected in usdview: green ❌  blue ❌  red ❌  (all hidden)
# ─────────────────────────────────────────────────────────

# First restore red sphere so it would be visible if parent allows it
UsdGeom.Imageable(red.GetPrim()).MakeVisible()
# Now all three spheres say "inherited"

# Hide the parent
UsdGeom.Imageable(parent.GetPrim()).MakeInvisible()

print("=== EXPERIMENT 2 — Parent hidden (hides ALL children) ===")
print("Parent      authored:", parent.GetPrim().GetAttribute("visibility").Get())
print("RedSphere   authored:", red.GetPrim().GetAttribute("visibility").Get())
print("GreenSphere authored:", green.GetPrim().GetAttribute("visibility").Get())
print()
# Even though children say "inherited", computed resolves to "invisible"
# because the parent is invisible
print("RedSphere   computed:", UsdGeom.Imageable(red.GetPrim()).ComputeVisibility())
print("GreenSphere computed:", UsdGeom.Imageable(green.GetPrim()).ComputeVisibility())
print("BlueSphere  computed:", UsdGeom.Imageable(blue.GetPrim()).ComputeVisibility())
print()
print("Expected in usdview:  All hidden ❌ ❌ ❌")
print("KEY POINT: children say 'inherited' but COMPUTE to 'invisible'")
print("           because their parent is invisible")

path2 = os.path.join(SCRIPT_DIR, "visibility_exp2.usda")
stage.Export(path2)
print(f"Saved → {path2}")
print()

# ─────────────────────────────────────────────────────────
# EXPERIMENT 3 — parent hidden but one child explicitly visible?
# There is NO "visible" token — you cannot escape a hidden parent
# The closest you can do is set "inherited" which still loses to parent
# Expected in usdview: ALL still hidden
# ─────────────────────────────────────────────────────────

# Parent is still invisible from experiment 2
# Try to "show" green by calling MakeVisible
UsdGeom.Imageable(green.GetPrim()).MakeVisible()
# MakeVisible() sets visibility = "inherited"
# But "inherited" means "ask parent" — parent still says invisible

print("=== EXPERIMENT 3 — Can a child escape a hidden parent? ===")
print("Parent      authored:", parent.GetPrim().GetAttribute("visibility").Get())
print("GreenSphere authored:", green.GetPrim().GetAttribute("visibility").Get())
print()
print("GreenSphere computed:", UsdGeom.Imageable(green.GetPrim()).ComputeVisibility())
print()
print("Expected in usdview:  Green still hidden ❌")
print("KEY POINT: 'inherited' on child cannot override 'invisible' on parent")
print("           This is why there is no 'visible' token —")
print("           it would let children escape parent hiding")

path3 = os.path.join(SCRIPT_DIR, "visibility_exp3.usda")
stage.Export(path3)
print(f"Saved → {path3}")
print()

print("=" * 55)
print("OPEN EACH FILE IN USDVIEW TO SEE THE DIFFERENCE:")
print(f"  Exp 1 (red hidden):   .\\scripts\\usdview.bat {path1}")
print(f"  Exp 2 (all hidden):   .\\scripts\\usdview.bat {path2}")
print(f"  Exp 3 (still hidden): .\\scripts\\usdview.bat {path3}")
print("Press F in usdview to frame all visible geometry")
print("=" * 55)