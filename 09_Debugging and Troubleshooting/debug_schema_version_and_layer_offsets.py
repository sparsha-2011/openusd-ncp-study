"""
Debug Exercise — Schema Version Validation + Layer Offsets
============================================================
Two advanced debugging topics from the real exam.

TOPIC 1: Schema version mismatches across layers
TOPIC 2: Layer offsets affecting time-based composition

WHEN TO USE:
  Schema versions: Unexpected attribute behaviour when layers come from
                   different pipeline versions or USD releases.
  Layer offsets:   Animation appears at the wrong time code after referencing.

Run: python debug_schema_version_and_layer_offsets.py
"""

from pxr import Usd, UsdGeom, Sdf, Gf
import os

SEP = "=" * 65

# ══════════════════════════════════════════════════════════════════
# TOPIC 1 — SCHEMA VERSION VALIDATION
# ══════════════════════════════════════════════════════════════════
print(SEP)
print("  TOPIC 1 — Schema Version Validation")
print(SEP)
print("""
  SCENARIO:
  Two layers were authored with different pipeline schema versions.
  Old version used attribute name "shader:roughness".
  New version renamed it to "inputs:roughness".
  When composed, the layers don't agree on attribute names.
  The result is unexpected or missing values.
""")

# Simulate old-schema layer
old_layer = Sdf.Layer.CreateAnonymous("old_pipeline_v1.usda")
old_stage = Usd.Stage.Open(old_layer)
shader_old = old_stage.DefinePrim("/Looks/Mat/Shader")
# Old schema attribute name
shader_old.CreateAttribute(
    "shader:roughness", Sdf.ValueTypeNames.Float).Set(0.3)

# Simulate new-schema layer
new_layer = Sdf.Layer.CreateAnonymous("new_pipeline_v2.usda")
new_stage = Usd.Stage.Open(new_layer)
shader_new = new_stage.DefinePrim("/Looks/Mat/Shader")
# New schema attribute name (UsdShade convention)
shader_new.CreateAttribute(
    "inputs:roughness", Sdf.ValueTypeNames.Float).Set(0.5)

# Compose them
root = Sdf.Layer.CreateAnonymous("shot.usda")
root.subLayerPaths = [new_layer.identifier, old_layer.identifier]
stage = Usd.Stage.Open(root)

shader = stage.GetPrimAtPath("/Looks/Mat/Shader")

print(f"  Attributes on composed shader prim:")
for prop in shader.GetProperties():
    val = prop.Get() if hasattr(prop, 'Get') else '(relationship)'
    print(f"    {prop.GetName():<30} = {val}")

print(f"""
  RESULT: BOTH attributes exist on the prim simultaneously.
  'shader:roughness'  = 0.3   (old schema name)
  'inputs:roughness'  = 0.5   (new schema name)
  The renderer uses ONE of these — likely 'inputs:roughness'.
  The old value (0.3) silently has no effect.

  HOW TO CHECK SCHEMA VERSIONS:
""")

# Check custom layer data for version metadata
for layer in [old_layer, new_layer]:
    lname = os.path.basename(layer.identifier)
    custom = layer.customLayerData
    version = custom.get("pipeline:schemaVersion", "not set")
    print(f"  {lname:<40} schema version: {version}")

print(f"""
  PREVENTION:
  1. Set pipeline version in customLayerData at authoring time:
     layer.customLayerData = {{"pipeline:schemaVersion": "2.0"}}

  2. Run usdchecker across all layers before delivery:
     usdchecker scene.usda
     [WARNING] Layer uses deprecated attribute names

  3. Write migration scripts when renaming schema attributes:
     scan all layers, find old names, rename to new names
""")


# ══════════════════════════════════════════════════════════════════
# TOPIC 2 — LAYER OFFSETS AND TIME COMPOSITION
# ══════════════════════════════════════════════════════════════════
print(SEP)
print("  TOPIC 2 — Layer Offsets Affecting Time-Based Composition")
print(SEP)
print("""
  SCENARIO:
  You reference an animation. Its keyframe is at time=10.
  But in the composed stage it appears at time=120.
  The layer offset on the reference is transforming the time.

  FORMULA: composed_time = (source_time × scale) + offset
""")

# Build the referenced animation
anim_layer = Sdf.Layer.CreateAnonymous("walk_cycle.usda")
anim_stage = Usd.Stage.Open(anim_layer)
UsdGeom.Xform.Define(anim_stage, "/Character")
char = anim_stage.GetPrimAtPath("/Character")

# Keyframe at source time 10
translate_attr = char.CreateAttribute(
    "xformOp:translate", Sdf.ValueTypeNames.Double3)
char.CreateAttribute(
    "xformOpOrder", Sdf.ValueTypeNames.TokenArray).Set(["xformOp:translate"])
translate_attr.Set(Gf.Vec3d(0, 0, 0),  time=1)
translate_attr.Set(Gf.Vec3d(5, 0, 0),  time=10)
translate_attr.Set(Gf.Vec3d(10, 0, 0), time=20)
anim_stage.GetRootLayer().Save()

# Build the shot that references the animation WITH an offset
shot_stage = Usd.Stage.CreateInMemory()
shot_stage.SetMetadata("timeCodesPerSecond", 24)

char_in_shot = shot_stage.DefinePrim("/World/Character")

# Reference with offset=100, scale=2.0
# composed_time = (source_time * 2.0) + 100
ref_with_offset = Sdf.Reference(
    assetPath=anim_layer.identifier,
    primPath=Sdf.Path("/Character"),
    layerOffset=Sdf.LayerOffset(offset=100.0, scale=2.0)
)
char_in_shot.GetReferences().AddReference(ref_with_offset)

# Check where the keyframe appears in the composed stage
composed_char = shot_stage.GetPrimAtPath("/World/Character")
attr_composed = composed_char.GetAttribute("xformOp:translate")

# The source keyframe was at time=10
# With offset=100, scale=2.0: composed = (10 × 2.0) + 100 = 120
source_time = 10.0
offset = 100.0
scale = 2.0
expected_composed_time = (source_time * scale) + offset

print(f"  Source animation keyframe at:     time = {source_time}")
print(f"  Layer offset: offset={offset}, scale={scale}")
print(f"  Formula: ({source_time} × {scale}) + {offset} = {expected_composed_time}")
print(f"  Expected composed time:           time = {expected_composed_time}")

time_samples = attr_composed.GetTimeSamples()
print(f"\n  Actual time samples in composed stage: {time_samples}")

# Show values at various composed times
print(f"\n  Values at key times in composed stage:")
for t in [100, 120, 140]:
    val = attr_composed.Get(time=t)
    print(f"    time={t:<6} → {val}")

print(f"""
  RESULT:
  The keyframe from time=10 in the source appears at time=120
  in the composed stage — exactly as the formula predicts.

  BUG PATTERN:
  "Animation appears at the wrong time" →
  First thing to check: layer offset on the reference arc.

  HOW TO CHECK LAYER OFFSETS:
  Look at the prim's PrimStack:
    for spec in prim.GetPrimStack():
        print(spec.layer.identifier)
  The layer offset is stored on the reference arc itself.
  Inspect the USDA — look for:
    prepend references = @./walk_cycle.usda@  (offset = 100, scale = 2)

  EXAM KEY POINT:
  "Ignoring layer offsets as they do not affect composition" → WRONG
  Layer offsets DO affect time-varying data composition.
  Always check layer offsets when debugging animation timing issues.
""")
