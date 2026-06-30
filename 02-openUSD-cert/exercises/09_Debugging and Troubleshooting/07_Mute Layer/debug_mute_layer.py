"""
Debug Exercise — MuteLayer
============================
Isolate which layer causes a problem by silencing layers one at a time.

TOPIC: stage.MuteLayer() / stage.UnmuteLayer()
WHEN TO USE: A value is wrong and you have multiple layers.
             Mute each candidate layer and see if the wrong value disappears.
             When it does — that layer is the problem.

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
# The director sublayer has the wrong value — it's the culprit.
# We use three plain sublayers so the culprit can be isolated by muting.
root     = Sdf.Layer.CreateAnonymous("root.usda")
fx       = Sdf.Layer.CreateAnonymous("fx.usda")
director = Sdf.Layer.CreateAnonymous("director.usda")
layout   = Sdf.Layer.CreateAnonymous("layout.usda")

root.subLayerPaths = [
    fx.identifier,
    director.identifier,
    layout.identifier,
]
stage = Usd.Stage.Open(root)

# Define /World as Xform so hierarchy is visible in usdview
stage.SetEditTarget(layout)
UsdGeom.Xform.Define(stage, "/World")

# Layout — base position (0,0,0)
stage.SetEditTarget(layout)
UsdGeom.Xform.Define(stage, "/World/Chair")
prim = stage.GetPrimAtPath("/World/Chair")
UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(0, 0, 0))

# Director — THE BUG: authored 99 instead of the intended 5
stage.SetEditTarget(director)
stage.OverridePrim("/World/Chair")
UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(99, 0, 0))

# FX layer — has a correct unrelated override (strongest layer)
# but no translate opinion — so director's 99 is winning
stage.SetEditTarget(fx)
stage.OverridePrim("/World/Chair")
prim.CreateAttribute("fx:enabled", Sdf.ValueTypeNames.Bool).Set(True)

stage.SetEditTarget(root)
prim = stage.GetPrimAtPath("/World/Chair")
attr = prim.GetAttribute("xformOp:translate")

# ── STEP 1: OBSERVE THE PROBLEM ─────────────────────────────────────
print(SEP)
print("  STEP 1 — Starting situation")
print(SEP)
print(f"\n  Composed translate: {attr.Get()}")
print(f"  Expected:           (5.0, 0.0, 0.0)")
print(f"  Something is wrong.\n")
print(f"  Layers (strongest → weakest):")
for i, layer in enumerate([fx, director, layout]):
    name = os.path.basename(layer.identifier)
    print(f"  [{i}] {name}")
print()

# ── STEP 2: SYSTEMATIC MUTING ───────────────────────────────────────
print(SEP)
print("  STEP 2 — Mute each layer in turn to find the culprit")
print(SEP)
print("""
  Strategy: mute one layer at a time.
  When the wrong value disappears → that layer is responsible.
  Always unmute before trying the next one.
""")

candidates = [
    (fx,       "fx.usda"),
    (layout,   "layout.usda"),
    (director, "director.usda"),
]

for layer, name in candidates:
    stage.MuteLayer(layer.identifier)
    val = attr.Get()
    if val is None:
        result = "None (no opinion left)"
        tag = ""
    elif round(val[0]) == 5:
        result = str(val)
        tag = "  <── CULPRIT FOUND — removing this reveals (5,0,0)"
    elif round(val[0]) == 99:
        result = str(val)
        tag = "  still 99 — NOT the culprit"
    else:
        result = str(val)
        tag = ""
    print(f"\n  Muting {name}...")
    print(f"  Value after muting: {result}{tag}")
    stage.UnmuteLayer(layer.identifier)
    print(f"  Unmuted. Value restored to: {attr.Get()}")

# ── STEP 3: FIX ─────────────────────────────────────────────────────
print()
print(SEP)
print("  STEP 3 — Fix: correct the value in director layer")
print(SEP)
print(f"\n  director.usda is the culprit — it has translate = (99,0,0)")
print(f"  The correct value should be (5,0,0)")
print(f"\n  Fix: set the correct value in director layer")

stage.SetEditTarget(director)
UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(5, 0, 0))
stage.SetEditTarget(root)

print(f"  After fix: {attr.Get()}   ← now correct")

print("""
  OTHER FIX APPROACHES:
  Fix 2: Mute the layer permanently during debugging
    stage.MuteLayer(director.identifier)
    → Removes its contribution without deleting anything

  Fix 3: Clear all opinions in one layer
    director.Clear()
    → Removes everything director.usda authored

  Fix 4: If the bug is in the real session layer (usdview edits)
    stage.GetSessionLayer().Clear()
    → The real session layer = usdview interactive edits
    → This is different from a sublayer named session.usda
    → stage.GetSessionLayer() is USD's built-in in-memory layer
    → It is always the STRONGEST layer in the stage
""")

# ── STEP 4: THE REAL SESSION LAYER ──────────────────────────────────
print(SEP)
print("  STEP 4 — The real session layer vs a sublayer named 'session'")
print(SEP)
print(f"""
  IMPORTANT DISTINCTION:
  stage.GetSessionLayer() is USD's BUILT-IN session layer.
  It is NOT the same as a sublayer you create and name "session.usda".

  Built-in session layer:
  → Always exists, always strongest
  → Contains usdview interactive edits
  → Never saved to disk
  → Cleared with stage.GetSessionLayer().Clear()

  A sublayer named "session.usda":
  → Just a regular sublayer you added to subLayerPaths
  → Has whatever strength position you gave it
  → Can be saved to disk
  → Cleared with your_layer_variable.Clear()

  This exercise uses regular sublayers so muting works clearly.
  In production, if a usdview edit is causing a wrong value:
  → stage.GetSessionLayer().Clear() removes ALL usdview edits
  → Or use stage.MuteLayer(stage.GetSessionLayer().identifier)
""")

print(f"  stage.GetSessionLayer().identifier:")
print(f"  {stage.GetSessionLayer().identifier}")
print(f"\n  Our 'session' sublayer identifier:")
print(f"  {os.path.basename(fx.identifier)}")
print(f"\n  They are different objects — confirmed.")

# ── STEP 5: CHECK MUTED LAYERS API ───────────────────────────────────
print()
print(SEP)
print("  STEP 5 — Mute/unmute API reference")
print(SEP)

stage.MuteLayer(layout.identifier)
print(f"\n  stage.GetMutedLayers(): {[os.path.basename(m) for m in stage.GetMutedLayers()]}")
print(f"  stage.IsLayerMuted(layout): {stage.IsLayerMuted(layout.identifier)}")
stage.UnmuteLayer(layout.identifier)
print(f"  After UnmuteLayer — IsLayerMuted: {stage.IsLayerMuted(layout.identifier)}")

print("""
  IMPORTANT RULES:
  ✅ Safe to mute: any sublayer, the real session layer
  ❌ Never mute: the root layer of a referenced asset
     Muting a reference's root layer = composition error
     (USD treats it as if the referenced file doesn't exist)
""")

# ── USDVIEW EQUIVALENT + EXPORT ──────────────────────────────────────
print(SEP)
print("  USDVIEW — How to mute layers interactively")
print(SEP)
print("""
  usdview's Layers panel lets you toggle layers on/off
  interactively with one click — the visual equivalent of MuteLayer.

  1. Open usdview:
     .\\scripts\\usdview.bat debug_mute_layer.usda

  2. Click /World/Chair in the Scenegraph
     Properties panel → translate = (99,0,0)  ← the bug

  3. Open the Layers panel (Windows → Layers or View → Layers)
     You see:
       fx.usda       ← strongest
       director.usda
       layout.usda   ← weakest

  4. Untick fx.usda
     translate is still (99,0,0) — fx had no translate opinion
     → fx is NOT the culprit

  5. Re-tick fx, then untick layout.usda
     translate is still (99,0,0) — layout has (0,0,0) which is weaker
     → layout is NOT the culprit

  6. Re-tick layout, then untick director.usda
     translate changes to (0,0,0) from layout
     → director IS the culprit — its 99 was the winning value

  This is exactly the Python MuteLayer workflow but visual and live.
""")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(SCRIPT_DIR, "debug_mute_layer.usda")

path_fx       = os.path.join(SCRIPT_DIR, "debug_ml_fx.usda")
path_director = os.path.join(SCRIPT_DIR, "debug_ml_director.usda")
path_layout   = os.path.join(SCRIPT_DIR, "debug_ml_layout.usda")

for fpath in [path_fx, path_director, path_layout, output_path]:
    if os.path.exists(fpath): os.remove(fpath)

fx.Export(path_fx)
director.Export(path_director)
layout.Export(path_layout)

root_out = Sdf.Layer.CreateNew(output_path)
root_out.subLayerPaths = [
    os.path.basename(path_fx),
    os.path.basename(path_director),
    os.path.basename(path_layout),
]
root_out.Save()

print(f"  Saved → {output_path} (open this in usdview)")
print(f"  Open in usdview:")
print(f"    .\\scripts\\usdview.bat {output_path}")
print(f"\n  In usdview:")
print(f"    1. Click /World/Chair → translate = (99,0,0)")
print(f"    2. Layers panel → toggle director.usda off")
print(f"       → translate changes to (0,0,0) from layout")
print(f"       → director confirmed as culprit")