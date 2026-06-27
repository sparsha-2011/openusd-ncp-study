"""
UsdGeomImageable — PURPOSE DEMO
=================================
This script demonstrates purpose tokens properly.
Each representation gets its CORRECT purpose token set,
then we create separate files to visualise each perspective.

PURPOSE TOKENS:
  "default"  →  shown everywhere — the fallback
  "render"   →  final quality mesh — renderer only
  "proxy"    →  lightweight stand-in — viewport
  "guide"    →  rig controls — rigging tools only

WHY USDVIEW ONLY SHOWS GREY (proxy):
  usdview acts like a viewport tool.
  By default it shows: "default" and "proxy"
  By default it hides: "render" and "guide"
  This is CORRECT behaviour — not a bug.

FILES CREATED:
  purpose_compare.usda   → all prims purpose="default" so you see everything
  purpose.usda   → correct purpose tokens — usdview shows proxy only

HOW TO VERIFY THE ORANGE SPHERE EXISTS:
  Open purpose_correct.usda in a TEXT EDITOR
  You will see HeroMesh with radius=3 and orange colour
  AND the line:  uniform token purpose = "render"
  It IS there — usdview just filters it by purpose

Run: python purpose_demo.py
Then open each file in usdview and press F.
"""

import os
from pxr import Usd, UsdGeom, Gf

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ═══════════════════════════════════════════════════════════════════════
# FILE 1: purpose.usda
# All prims have purpose="default" so usdview shows EVERYTHING
# Use this to see all three representations side by side
# Orange (big) LEFT · Grey (small) MIDDLE · Cyan (tiny) RIGHT
# ═══════════════════════════════════════════════════════════════════════
s1 = Usd.Stage.CreateInMemory()
UsdGeom.SetStageUpAxis(s1, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(s1, 0.01)

# RENDER representation — big orange sphere, LEFT
# purpose intentionally left as "default" so usdview shows it
# In real production this would be purpose="render"
hero1 = UsdGeom.Sphere.Define(s1, "/World/HeroMesh")
hero1.GetRadiusAttr().Set(3.0)
hero1.GetDisplayColorAttr().Set([(1.0, 0.4, 0.0)])        # bright orange
UsdGeom.XformCommonAPI(hero1).SetTranslate(Gf.Vec3d(-10, 0, 0))

# PROXY representation — small grey sphere, MIDDLE
# purpose="default" — always visible
# In real production this would be purpose="proxy"
proxy1 = UsdGeom.Sphere.Define(s1, "/World/ProxyMesh")
proxy1.GetRadiusAttr().Set(1.0)
proxy1.GetDisplayColorAttr().Set([(0.6, 0.6, 0.6)])       # grey

# GUIDE representation — tiny cyan sphere, RIGHT
# purpose="default" — always visible
# In real production this would be purpose="guide"
guide1 = UsdGeom.Sphere.Define(s1, "/World/RigControl")
guide1.GetRadiusAttr().Set(0.5)
guide1.GetDisplayColorAttr().Set([(0.0, 1.0, 1.0)])       # cyan
UsdGeom.XformCommonAPI(guide1).SetTranslate(Gf.Vec3d(10, 3, 0))

path1 = os.path.join(SCRIPT_DIR, "purpose.usda")
s1.Export(path1)
print(f"File 1 saved → {path1}")
print("  All purpose='default' — usdview shows EVERYTHING")
print("  LEFT  = big orange  (what a RENDERER uses)")
print("  MID   = small grey  (what a VIEWPORT shows)")
print("  RIGHT = tiny cyan   (what a RIGGER sees)")
print()


# ═══════════════════════════════════════════════════════════════════════
# FILE 2: purpose_correct.usda
# Prims have their CORRECT purpose tokens
# usdview only shows proxy (grey) — orange and cyan are filtered
# The orange render sphere IS there — usdview filters it by purpose
# ═══════════════════════════════════════════════════════════════════════
s2 = Usd.Stage.CreateInMemory()
UsdGeom.SetStageUpAxis(s2, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(s2, 0.01)

char2 = UsdGeom.Xform.Define(s2, "/World/Character")

# ── HERO — purpose="render" ──────────────────────────────────────────
hero2 = UsdGeom.Sphere.Define(s2, "/World/Character/HeroMesh")
hero2.GetRadiusAttr().Set(3.0)
hero2.GetDisplayColorAttr().Set([(1.0, 0.4, 0.0)])
UsdGeom.XformCommonAPI(hero2).SetTranslate(Gf.Vec3d(-5, 0, 0))
# Set the actual purpose token — THIS is what was missing before
UsdGeom.Imageable(hero2.GetPrim()).GetPurposeAttr().Set(UsdGeom.Tokens.render)
# Produces in USDA:  uniform token purpose = "render"
# usdview HIDES this prim

print(f"HeroMesh authored purpose:   {UsdGeom.Imageable(hero2.GetPrim()).GetPurposeAttr().Get()}")
print(f"HeroMesh computed purpose:   {UsdGeom.Imageable(hero2.GetPrim()).ComputePurpose()}")

# ── PROXY — purpose="proxy" ──────────────────────────────────────────
proxy2 = UsdGeom.Sphere.Define(s2, "/World/Character/ProxyMesh")
proxy2.GetRadiusAttr().Set(1.0)
proxy2.GetDisplayColorAttr().Set([(0.6, 0.6, 0.6)])
# Set the actual purpose token
UsdGeom.Imageable(proxy2.GetPrim()).GetPurposeAttr().Set(UsdGeom.Tokens.proxy)
# Produces in USDA:  uniform token purpose = "proxy"
# usdview SHOWS this prim

print(f"ProxyMesh authored purpose:  {UsdGeom.Imageable(proxy2.GetPrim()).GetPurposeAttr().Get()}")
print(f"ProxyMesh computed purpose:  {UsdGeom.Imageable(proxy2.GetPrim()).ComputePurpose()}")

# ── GUIDE — purpose="guide" ──────────────────────────────────────────
guide2 = UsdGeom.Sphere.Define(s2, "/World/Character/RigControl")
guide2.GetRadiusAttr().Set(0.4)
guide2.GetDisplayColorAttr().Set([(0.0, 1.0, 1.0)])
UsdGeom.XformCommonAPI(guide2).SetTranslate(Gf.Vec3d(0, 5, 0))
# Set the actual purpose token
UsdGeom.Imageable(guide2.GetPrim()).GetPurposeAttr().Set(UsdGeom.Tokens.guide)
# Produces in USDA:  uniform token purpose = "guide"
# usdview HIDES this prim

print(f"RigControl authored purpose: {UsdGeom.Imageable(guide2.GetPrim()).GetPurposeAttr().Get()}")
print(f"RigControl computed purpose: {UsdGeom.Imageable(guide2.GetPrim()).ComputePurpose()}")
print()

path2 = os.path.join(SCRIPT_DIR, "purpose_correct.usda")
s2.Export(path2)
print(f"File 2 saved → {path2}")
print("  Correct purpose tokens — usdview shows ONLY grey proxy sphere")
print("  Orange hero IS in the file — usdview filters purpose='render'")
print("  Cyan guide IS in the file  — usdview filters purpose='guide'")
print()


# ═══════════════════════════════════════════════════════════════════════
# PRINT USDA OF FILE 2
# Look for these lines in the output:
#   uniform token purpose = "render"
#   uniform token purpose = "proxy"
#   uniform token purpose = "guide"
# These are the actual purpose tokens that were missing before
# ═══════════════════════════════════════════════════════════════════════
print("=== purpose_correct.usda — look for 'purpose' lines ===")
print(s2.ExportToString(addSourceFileComment=False))


# ═══════════════════════════════════════════════════════════════════════
# TRAVERSE AND CONFIRM PURPOSES
# ═══════════════════════════════════════════════════════════════════════
print("=== COMPUTED PURPOSE FOR EACH PRIM ===")
for prim in s2.Traverse():
    if prim.IsA(UsdGeom.Imageable):
        authored = UsdGeom.Imageable(prim).GetPurposeAttr().Get()
        computed = UsdGeom.Imageable(prim).ComputePurpose()
        visible  = "shown in usdview" if computed in ("default", "proxy") else "HIDDEN by usdview"
        print(f"  {str(prim.GetPath()):<45} purpose={computed:<10}  {visible}")
print()

print("=" * 65)
print("OPEN IN USDVIEW:")
print()
print(f"  .\\scripts\\usdview.bat {path1}")
print("  → Press F — see ALL THREE side by side")
print("  → All have purpose='default' so nothing is filtered")
print()
print(f"  .\\scripts\\usdview.bat {path2}")
print("  → Press F — see ONLY the grey sphere")
print("  → Orange hidden:  purpose='render' (renderer only)")
print("  → Cyan hidden:    purpose='guide'  (rigging tools only)")
print("  → Open this file in VS Code to confirm orange IS in the file")
print()
print("KEY INSIGHT:")
print("  Seeing only grey in usdview is CORRECT.")
print("  usdview = viewport tool → shows proxy.")
print("  Renderer              → shows render.")
print("  Rigging tool          → shows guide.")
print("  Same USD file. Different tools. Different views.")
print("=" * 65)