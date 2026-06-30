"""
Debug Exercise — GetCompositionErrors
========================================
Detect and read broken references and other composition failures.

TOPIC: stage.GetCompositionErrors() / prim.GetPrimIndex().DumpToString()
WHEN TO USE: A prim is empty or invalid despite being defined in the scene.
             References or payloads are not resolving correctly.

Run: python debug_composition_errors.py
"""

from pxr import Usd, UsdGeom, Sdf, Gf
import os

SEP = "=" * 65

# ── BUILD A STAGE WITH BROKEN REFERENCES ───────────────────────────
stage = Usd.Stage.CreateInMemory()

# Define /World as Xform so hierarchy is visible in usdview
UsdGeom.Xform.Define(stage, "/World")

# Valid prim — no reference
valid_prim = UsdGeom.Xform.Define(stage, "/World/ValidObject")

# Broken prim — references a file that does not exist
broken_prim = UsdGeom.Sphere.Define(stage, "/World/BrokenChair").GetPrim()
broken_prim.GetReferences().AddReference("./this_file_does_not_exist.usda")

# Prim with valid reference but wrong internal path
# Anonymous layers cannot be saved — use a real temp file on disk
import tempfile, os as _os
good_asset_path = _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), "debug_ce_good_asset.usda"
)
if _os.path.exists(good_asset_path):
    _os.remove(good_asset_path)

# Create and save as a real file so the reference can resolve
good_stage = Usd.Stage.CreateNew(good_asset_path)
UsdGeom.Xform.Define(good_stage, "/MyAsset")
good_stage.GetRootLayer().Save()

# Reference the real file path but point to a prim that doesn't exist
prim_wrong_path = UsdGeom.Cube.Define(stage, "/World/WrongPath").GetPrim()
prim_wrong_path.GetReferences().AddReference(
    good_asset_path, "/PathThatDoesNotExist"
)

# ── STEP 1: CHECK COMPOSITION ERRORS ───────────────────────────────
print(SEP)
print("  STEP 1 — stage.GetCompositionErrors()")
print(SEP)

errors = stage.GetCompositionErrors()
print(f"\n  Total composition errors: {len(errors)}\n")
for i, err in enumerate(errors):
    err_str = str(err)
    print(f"  Error [{i+1}]:")
    print(f"    {err_str[:100]}")
    print()

# ── STEP 2: CHECK PRIM VALIDITY ─────────────────────────────────────
print(SEP)
print("  STEP 2 — Check prim validity")
print(SEP)
print(f"\n  {'Prim':<30} {'IsValid':<10} {'IsDefined':<12} Observation")
print("  " + "-" * 72)

for path in ["/World/ValidObject",
             "/World/BrokenChair",
             "/World/WrongPath"]:
    p = stage.GetPrimAtPath(path)
    obs = (
        "Normal prim"             if p.IsValid() and p.IsDefined() else
        "Exists but not defined"  if p.IsValid() and not p.IsDefined() else
        "Invalid"
    )
    print(f"  {path:<30} {str(p.IsValid()):<10} {str(p.IsDefined()):<12} {obs}")

print("""
  OBSERVATIONS:
  /World/ValidObject  → IsValid=True, IsDefined=True  — all good
  /World/BrokenChair  → still shows as valid (prim exists in stage)
                        but its reference arc has an error
  /World/WrongPath    → prim exists but referenced prim path not found
""")

# ── STEP 3: PRIM INDEX DUMP ─────────────────────────────────────────
print(SEP)
print("  STEP 3 — prim.GetPrimIndex().DumpToString()")
print(SEP)
print("""
  DumpToString() shows the full composition graph for one prim.
  It reveals every arc, where it came from, and any errors.
  This is the most detailed programmatic composition debug tool.
""")

broken = stage.GetPrimAtPath("/World/BrokenChair")
dump = broken.GetPrimIndex().DumpToString()
# Show first portion — it can be very verbose
lines = dump.split('\n')[:20]
print("  First 20 lines of prim index for /World/BrokenChair:")
print()
for line in lines:
    print(f"  {line}")
print(f"  ... ({len(dump.split(chr(10)))} total lines)")

# ── STEP 4: COMMON ERROR TYPES ──────────────────────────────────────
print()
print(SEP)
print("  STEP 4 — Common composition error types")
print(SEP)
print("""
  PcpErrorType_InvalidAssetPath
    → The referenced file cannot be found at the given path
    → Fix: ensure the file exists at the relative/absolute path

  PcpErrorType_InvalidPrimPath
    → The file was found but the prim path inside it doesn't exist
    → Fix: check the referenced prim path matches what's in the file
    → Most commonly: defaultPrim not set on the referenced file

  PcpErrorType_ArcCycle
    → A circular reference — A references B which references A
    → Fix: break the cycle

  PcpErrorType_UnresolvedPrimPath
    → An inherit or specialize arc targets a prim that can't be found
    → Fix: ensure the class prim exists in the composed namespace

  QUICK DIAGNOSTIC:
  stage.GetCompositionErrors()          → all errors on the stage
  prim.GetPrimIndex().DumpToString()    → full arc graph for one prim
  usdchecker scene.usda                 → pre-delivery validation
""")

print("Composition Errors:",stage.GetCompositionErrors())
# ── USDVIEW EQUIVALENT + EXPORT ──────────────────────────────────────
print(SEP)
print("  USDVIEW — How composition errors appear visually")
print(SEP)
print("""
  usdview shows composition errors visually in two ways:

  1. Open usdview:
     .\\scripts\\usdview.bat debug_composition_errors.usda

  2. In the Scenegraph panel:
     /World/BrokenChair appears with a WARNING icon or
     highlighted in a different colour — signalling a problem.
     Its children will be missing or empty.

  3. Click /World/BrokenChair

  4. Metadata/Composition → Composition tab
     Shows the broken reference arc with an ERROR annotation:
     "Could not open asset @./this_file_does_not_exist.usda@"
     This is the visual equivalent of stage.GetCompositionErrors()

  5. Metadata/Composition → LayerStack tab
     Only the local layer shows up — the reference failed to load.
     If a reference had loaded, you'd see its layers here too.

  6. The terminal / console at the bottom of usdview
     Also shows composition error messages as text —
     same text as GetCompositionErrors() returns in Python.

  WORKFLOW:
  Quick check → usdview Composition tab (visual, immediate)
  Scripted check → stage.GetCompositionErrors() (automation, CI)
  Deep investigation → prim.GetPrimIndex().DumpToString() (most detail)
""")

import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(SCRIPT_DIR, "debug_composition_errors.usda")
stage.Export(output_path)
print(f"  Saved → {output_path}")
print(f"  Open in usdview:")
print(f"    .\\scripts\\usdview.bat {output_path}")
print(f"\n  In usdview:")
print(f"    1. Look for warning icons on /World/BrokenChair")
print(f"    2. Click it → Composition tab → see the broken arc")
print(f"    3. Compare /World/ValidObject (clean) vs BrokenChair (error)")