"""
Debug Exercise — MuteLayer
============================
Isolate which layer causes a problem by silencing layers one at a time.

TOPIC: stage.MuteLayer() / stage.UnmuteLayer()
WHEN TO USE: A value is wrong and you have multiple layers.
             Mute each candidate layer and see if the wrong value disappears.
             When it does — that layer is the culprit.

THE RULE: Muted layers do not participate in composition or value resolution.
          They are completely silent but NOT removed — UnmuteLayer() restores instantly.
          NEVER mute the root layer of a reference — it causes a composition error.

Run: python debug_mute_layer.py
"""

from pxr import Usd, UsdGeom, Sdf, Gf
import os

SEP = "=" * 65

# ── BUILD THE STAGE ─────────────────────────────────────────────────
# Three layers all have translate opinions.
# Session layer has the wrong value — it's the culprit.
root    = Sdf.Layer.CreateAnonymous("root.usda")
session = Sdf.Layer.CreateAnonymous("session.usda")
director= Sdf.Layer.CreateAnonymous("director.usda")
layout  = Sdf.Layer.CreateAnonymous("layout.usda")

root.subLayerPaths = [
    session.identifier,
    director.identifier,
    layout.identifier,
]
stage = Usd.Stage.Open(root)

# Layout has the base position
stage.SetEditTarget(layout)
UsdGeom.Xform.Define(stage, "/World/Chair")
prim = stage.GetPrimAtPath("/World/Chair")
UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(0, 0, 0))

# Director has the intended creative position
stage.SetEditTarget(director)
stage.OverridePrim("/World/Chair")
UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(5, 0, 0))

# Session has a stale interactive edit — THE BUG
stage.SetEditTarget(session)
stage.OverridePrim("/World/Chair")
UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(99, 0, 0))

stage.SetEditTarget(root)
prim = stage.GetPrimAtPath("/World/Chair")
attr = prim.GetAttribute("xformOp:translate")

# ── STEP 1: OBSERVE THE PROBLEM ─────────────────────────────────────
print(SEP)
print("  STEP 1 — Starting situation")
print(SEP)
print(f"\n  Composed translate: {attr.Get()}   ← wrong, expected (5,0,0)")
print(f"\n  Layers (strongest → weakest):")
for i, layer in enumerate([session, director, layout]):
    name = os.path.basename(layer.identifier)
    print(f"  [{i}] {name}")
print()

# ── STEP 2: SYSTEMATIC MUTING ───────────────────────────────────────
print(SEP)
print("  STEP 2 — Mute each layer in turn to find the culprit")
print(SEP)

candidates = [
    (layout,   "layout.usda"),
    (director, "director.usda"),
    (session,  "session.usda"),
]

for layer, name in candidates:
    stage.MuteLayer(layer.identifier)
    val = attr.Get()
    culprit = "  <── CULPRIT FOUND" if val and round(val[0]) == 5 else ""
    print(f"\n  Muting {name}...")
    print(f"  Value after muting: {val}{culprit}")
    stage.UnmuteLayer(layer.identifier)
    print(f"  Unmuted. Value restored to: {attr.Get()}")

# ── STEP 3: FIX ─────────────────────────────────────────────────────
print()
print(SEP)
print("  STEP 3 — Fix: clear the session layer")
print(SEP)
print(f"\n  Session layer is the culprit.")
print(f"  Fix 1: Clear the session layer entirely")

stage.GetSessionLayer().Clear()
print(f"  After Clear(): {attr.Get()}   ← now correct (director wins)")

print("""
  Fix 2: Remove just the specific opinion
    session_layer.RemovePrimIfInert("/World/Chair")
    or use the Edit Target to explicitly block the value

  Fix 3: Don't use usdview interactive edits if you need persistence
    usdview writes ALL interactive changes to the session layer
    The session layer is NEVER saved to disk
""")

# ── STEP 4: CHECK MUTED LAYERS ──────────────────────────────────────
print(SEP)
print("  STEP 4 — Check what is currently muted")
print(SEP)

# Mute one layer for demonstration
stage.MuteLayer(layout.identifier)
muted = stage.GetMutedLayers()
print(f"\n  stage.GetMutedLayers():")
for m in muted:
    print(f"  → {os.path.basename(m)}")

print(f"\n  Is layout muted? {stage.IsLayerMuted(layout.identifier)}")
stage.UnmuteLayer(layout.identifier)
print(f"  After UnmuteLayer: {stage.IsLayerMuted(layout.identifier)}")

print("""
  IMPORTANT RULES:
  ✅ Safe to mute: sublayers, session layer
  ❌ Never mute: the root layer of a referenced asset
     Muting a reference's root layer = composition error
     (as if that asset doesn't exist at all)
""")
