# Day 5 — Schemas and Data Modeling

> **OpenUSD NCP Certification Study Notes**  
> _USD Schemas, Schema Types, usdGenSchema, Custom Schemas, SdfFileFormat_

---

## Table of Contents

1. [What is a Schema?](#1-what-is-a-schema)
2. [IsA Schemas vs API Schemas](#2-isa-schemas-vs-api-schemas)
3. [Schema Inheritance Hierarchy](#3-schema-inheritance-hierarchy)
4. [Creating Custom Schemas](#4-creating-custom-schemas)
5. [The usdGenSchema Workflow](#5-the-usdgenschema-workflow)
6. [TfType Registration](#6-tftype-registration)
7. [Custom File Format Plugins — SdfFileFormat](#7-custom-file-format-plugins--sdffileformat)
8. [Model Kinds — Classifying Prims by Pipeline Role](#8-model-kinds--classifying-prims-by-pipeline-role)
9. [Custom Model Kinds — UsdModelKindRegistry](#9-custom-model-kinds--usdmodelkindregistry)
10. [Exam Pattern Recognition — Elimination Guide](#1--exam-pattern-recognition--elimination-guide)
11. [Key Takeaways](#11-key-takeaways)

---

## 1. What is a Schema?

A **schema** is a formal definition of a prim type — what attributes it has, what their types and default values are, and how it participates in USD's type system. Schemas are what make `UsdGeom.Sphere` a sphere and `UsdLux.DistantLight` a directional light.

USD ships with built-in schemas for common 3D concepts (`Mesh`, `Camera`, `Material`, `DistantLight`). When your pipeline needs a type that doesn't exist in USD — a `TemperatureSensor`, a `ConveyorBelt`, a `ShotCamera` — you create a **custom schema**.

---

## 2. IsA Schemas vs API Schemas

USD has two fundamentally different schema types:

### IsA Schemas (Typed Schemas)

An IsA schema **defines the type of a prim**. It sets the `typeName` metadata. A prim has exactly **one** IsA schema — it IS a Mesh, or it IS a Sphere, not both.

```usda
def Mesh "Chair" {     # typeName = "Mesh" — this prim IS a Mesh
    ...
}
```

```python
prim.IsA(UsdGeom.Mesh)       # True — prim is of type Mesh
prim.GetTypeName()            # "Mesh"
```

### API Schemas

An API schema **augments a prim** with additional properties and behaviours without changing its type. A prim can have **multiple** API schemas applied simultaneously. They are listed in `apiSchemas` metadata.

```usda
def Mesh "Character" (
    prepend apiSchemas = ["PhysicsRigidBodyAPI", "MotionAPI"]
    # Still a Mesh — but with physics and motion APIs applied
) { }
```

```python
prim.HasAPI(UsdPhysics.RigidBodyAPI)   # True
prim.IsA(UsdGeom.Mesh)                 # Still True
```

| Property            | IsA Schema            | API Schema                   |
| ------------------- | --------------------- | ---------------------------- |
| Sets `typeName`     | ✅ Yes                | ❌ No                        |
| Number per prim     | Exactly 1             | Multiple                     |
| Checking            | `prim.IsA()`          | `prim.HasAPI()`              |
| Declaration in USDA | `def TypeName "name"` | `prepend apiSchemas = [...]` |

---

## 3. Schema Inheritance Hierarchy

All USD schemas ultimately inherit from `UsdSchemaBase`. The hierarchy determines what capabilities a schema inherits.

```
UsdSchemaBase                    ← root of ALL schemas
├── UsdTyped                     ← base for all IsA (typed) schemas
│   ├── UsdGeomImageable         ← all renderable prims (visibility, purpose)
│   │   ├── UsdGeomXformable     ← all transformable prims
│   │   │   ├── UsdGeomGprim     ← all geometric primitives
│   │   │   │   ├── UsdGeomMesh
│   │   │   │   ├── UsdGeomSphere
│   │   │   │   └── ...
│   │   │   ├── UsdGeomCamera
│   │   │   └── UsdLuxLight      ← all lights
│   │   └── ...
│   └── UsdShadeMaterial
└── UsdAPISchemaBase             ← base for all API schemas
    ├── UsdGeomMotionAPI
    ├── UsdPhysicsRigidBodyAPI
    └── ...
```

### Choosing the Right Base Class for Custom Schemas

| Base Class         | Use when                                                      |
| ------------------ | ------------------------------------------------------------- |
| `UsdSchemaBase`    | ❌ Almost never — requires implementing everything manually   |
| `UsdTyped`         | ✅ Standard IsA schema that is a new prim type                |
| `UsdGeomImageable` | ✅ Custom renderable object that needs visibility and purpose |
| `UsdGeomXformable` | ✅ Custom object that needs transforms                        |

> **Exam trap:** "Inherit directly from UsdSchemaBase" is typically the wrong answer. The correct base is `UsdTyped` for standard custom IsA schemas, or `UsdGeomImageable` if the schema is a renderable object.

---

## 4. Creating Custom Schemas

USD ships with schemas for common 3D concepts — `Mesh`, `Sphere`, `Material`, `DistantLight`. These cover general-purpose use cases. But a factory automation company needs prims for `TemperatureSensor` and `ConveyorBelt`. A film studio needs `ShotCamera` and `CharacterRig`. These don't exist in USD out of the box.

Custom schemas let you add new prim types as **first-class USD citizens** — with the same type safety, API generation, schema fallbacks, and tool integration as built-in schemas.

### Plain Attributes vs Custom Schema

| Capability                    | Plain custom attributes           | Custom schema                        |
| ----------------------------- | --------------------------------- | ------------------------------------ |
| `prim.IsA(TemperatureSensor)` | ❌ No type checking               | ✅ Works correctly                   |
| Schema fallback values        | ❌ Returns `None` if unset        | ✅ Returns defined default           |
| Generated Python/C++ API      | ❌ Manual `GetAttribute("name")`  | ✅ `sensor.GetTemperatureAttr()`     |
| usdview introspection         | ❌ Arbitrary data, no schema info | ✅ Full attribute listing with types |
| Validation at authoring time  | ❌ Silent errors                  | ✅ Type-checked at definition        |
| Inheritance chain known       | ❌ No                             | ✅ `IsA(UsdGeomXform)` also works    |

### When to Use

| ✅ Use custom schemas when                 | ❌ Don't use for                          |
| ------------------------------------------ | ----------------------------------------- |
| Standardised types shared across teams     | Quick one-off pipeline attributes         |
| `prim.IsA()` and `prim.HasAPI()` must work | Data not shared across tools              |
| Schema fallback values are needed          | Rapid prototyping (use plain attrs first) |
| Full C++ and Python API is needed          | One-time migration scripts                |

Custom schemas are defined in a `schema.usda` file that describes the schema's class, what it inherits from, and what attributes it provides with their types and default values.

### `schema.usda` File Structure

```usda
#usda 1.0
(
    subLayers = [
        @usd/schema.usda@       # inherit from base USD schemas
    ]
)
#usdGenSchema config describing how to name the generated code it has no runtime existence
over "GLOBAL" (
    customData = {
        string libraryName   = "acmeSensors"    # library name
        string libraryPrefix = "AcmeSensor"     # C++ class prefix
    }
) {}

# Custom IsA schema — inherits from Xform (which is a UsdTyped)
class Xform "TemperatureSensor" (
    customData = {
        string className = "TemperatureSensor"
    }
    doc = """A prim representing a physical temperature sensor."""
    inherits = </Xform>
) {
    float  sensor:temperature = 20.0      # default = 20°C
    float  sensor:minRange    = -40.0
    float  sensor:maxRange    = 125.0
    string sensor:serialNumber = ""
}
```

---

## 5. The usdGenSchema Workflow

`usdGenSchema` is the code generation tool that transforms a `schema.usda` definition into compilable C++ code and Python bindings. Understanding where TfType fits into each step is essential — it explains why each step exists and what breaks if you skip any of them.

```
STEP 1  Write schema.usda
        ─────────────────────────────────────────────────────
        Define the schema class, base class, and attributes.
        This is your source of truth — human-readable intent.

        class Xform "TemperatureSensor" (
                ↑           ↑
            base class   schema class (the new type you are creating)
            inherits = </Xform>
        ) {
            float sensor:temperature = 20.0
        }

        TfType relevance: NONE YET
        The type does not exist anywhere at runtime.
        It is only an intent written in a text file.

        ↓

STEP 2  Run usdGenSchema schema.usda
        ─────────────────────────────────────────────────────
        usdGenSchema reads schema.usda and generates:

          acmeSensors.h           ← C++ class declaration
          acmeSensors.cpp         ← C++ implementation
                                     CONTAINS TF_REGISTRY_FUNCTION  ← key output
          wrapAcmeSensors.cpp     ← Python bindings
          plugInfo.json           ← manifest file containing the plugin discovery metadata

        TfType relevance: TF_REGISTRY_FUNCTION IS GENERATED HERE
        usdGenSchema writes the registration macro automatically.
        You never write TF_REGISTRY_FUNCTION by hand.
        It is compiled into the library in the next step.

        What TF_REGISTRY_FUNCTION looks like in the generated source:

          TF_REGISTRY_FUNCTION(TfType) {
              TfType::Define<AcmeSensors_TemperatureSensor,
                             TfType::Bases<UsdGeomXform>>();
          }

        ↓

STEP 3  Compile C++ into a shared library
        ─────────────────────────────────────────────────────
        cmake + make → acmeSensors.so (Linux) / acmeSensors.dll (Windows)

        TfType relevance: TF_REGISTRY_FUNCTION IS NOW IN THE BINARY
        The macro is compiled into the .so file.
        It exists on disk but has NOT run yet.
        The TfType registry is still empty for this type.

        ↓

STEP 4  Deploy the plugin
        ─────────────────────────────────────────────────────
        Place acmeSensors.so + plugInfo.json in a directory.
        /path/to/acmeSensors/
          ├── acmeSensors.so       ← compiled library (contains TF_REGISTRY_FUNCTION)
          └── plugInfo.json        ← discovery metadata (tells USD the library exists)

        Set PXR_PLUGINPATH_NAME=/path/to/acmeSensors/

        TfType relevance: DISCOVERY ENABLED, REGISTRATION STILL PENDING
        USD now knows where to find the library (plugInfo.json).
        But TF_REGISTRY_FUNCTION has still NOT run.
        The registry is still empty for TemperatureSensor.
        This is why manifest-file-only is wrong — discovery ≠ registration.

        ↓

STEP 5  First use of the type in a running process
        ─────────────────────────────────────────────────────
        prim.IsA(TemperatureSensor) is called for the first time.
        USD checks registry → not found → loads acmeSensors.so.
        Loading the .so triggers TF_REGISTRY_FUNCTION to run.

        TfType relevance: REGISTRATION HAPPENS NOW
        TF_REGISTRY_FUNCTION executes:
          Registry entry created:
          TemperatureSensor → Xform → Xformable → Imageable → Typed → SchemaBase

        From this point until the process ends:
          prim.IsA(TemperatureSensor)         → True
          prim.IsA(UsdGeom.Xform)             → True
          sensor.GetTemperatureAttr().Get()   → 20.0
          usdview shows all schema attributes → True

        When process ends → registry gone.
        Next process starts from Step 4 again.
```

### The TfType Journey in One View

```
schema.usda          →   usdGenSchema   →   acmeSensors.so    →   Running process
(text file)              (code gen)         (binary)               (in-memory registry)

"TemperatureSensor       TF_REGISTRY_      TF_REGISTRY_           TemperatureSensor
 inherits Xform"    →    FUNCTION         FUNCTION               → Xform
                         written in   →   compiled into   →      → Xformable
                         .cpp             .so                    → Imageable
                                          (dormant)              → Typed
                                                                 → SchemaBase
                    [intent]         [generated]        [on disk] [active in RAM]
```

### Why Not Python-Only?

Python has no mechanism to run `TF_REGISTRY_FUNCTION`. There is no `.so` binary, no compiled macro, nothing that writes into the TfType registry at load time. The type name exists as a string but the registry never gets populated.

| Capability                       | Python-only                   | Full C++ via usdGenSchema         |
| -------------------------------- | ----------------------------- | --------------------------------- |
| `TF_REGISTRY_FUNCTION` in binary | None                          | Generated automatically in Step 2 |
| `prim.IsA()`                     | False or error                | Works — registry populated        |
| Inheritance chain known          | No                            | Full chain in registry            |
| Schema fallback values           | `Get()` returns None          | Returns schema default            |
| Generated accessor methods       | Manual `GetAttribute("name")` | `GetTemperatureAttr()`            |
| Correct for                      | Prototyping only              | Production pipelines              |

---

## 6. TfType Registration

### What Problem TfType Solves

When USD reads a file containing `def TemperatureSensor "Sensor_001"`, it sees a string. Without something telling USD what that string means, it cannot answer:

- What attributes does this prim have?
- What does it inherit from?
- What fallback values apply?
- Does `prim.IsA(UsdGeom.Xform)` return True?

That "something" is the **TfType registry** — USD's runtime type identification system. Registration is what transforms a string into a meaningful type with a full inheritance chain, fallback values, and a generated API.

> **Where TfType fits in the workflow:** See Section 5 above. `TF_REGISTRY_FUNCTION` is generated in Step 2 (by usdGenSchema), compiled in Step 3, deployed in Step 4, and finally **runs** in Step 5 when the type is first used. The registry is populated at Step 5 only.

> **Analogy — The Immigration Database**
>
> Think of USD as a border system. A passport says "citizen of AcmeSensors Corp."
> That string means nothing until the border system looks it up in a registry
> that knows: what rights does this citizen have, what languages do they speak?
>
> The TfType registry is that database. Without it, `TemperatureSensor` is a
> passport from a country the system has never heard of — the string exists
> but carries no meaning. With it, USD knows the full profile.
>
> The `schema.usda` is the passport application. `usdGenSchema` prints the passport.
> `TF_REGISTRY_FUNCTION` is the moment it gets stamped and entered into the database.
> `plugInfo.json` is the address where the passport office is located.

### Without Registration vs With Registration

```
WITHOUT TfType registration          WITH TfType registration
────────────────────────────────     ────────────────────────────────
prim.GetTypeName()                   prim.GetTypeName()
→ "TemperatureSensor"                → "TemperatureSensor"
  (just a string, no meaning)          (meaningful — registry knows it)

prim.IsA(TemperatureSensor)          prim.IsA(TemperatureSensor)
→ False or AttributeError            → True

prim.IsA(UsdGeom.Xform)             prim.IsA(UsdGeom.Xform)
→ False (ancestry unknown)           → True (ancestry chain known)

sensor.GetTemperatureAttr().Get()    sensor.GetTemperatureAttr().Get()
→ None (no schema fallback)          → 20.0 (schema fallback works)

usdview:                             usdview:
→ "unknown schema type"              → all attributes listed with types
→ no attribute listing               → schema documentation visible
```

Same USD file. Same prim. The difference is entirely whether the registry has been populated for this process.

### What usdGenSchema Uses Internally — SdfPropertySpec

When `usdGenSchema` generates the C++ code that registers your schema, it also generates code that uses `SdfPropertySpec` and `SdfPrimSpec` to describe what attributes the schema type has — their names, types, default values, and documentation.

This is why `sensor.GetTemperatureAttr().Get()` returns `20.0` even without ever calling `Set()` — the generated code used `SdfAttributeSpec` to register that default at schema definition time, not at authoring time.

You interact with `SdfPropertySpec` directly when:

- Reading `GetPropertyStack()` or `GetPrimStack()` results — both return Sdf spec objects
- Writing pipeline validators that inspect raw layer contents
- Authoring directly into a layer without a full stage

> **Full explanation and code examples:** [Day 4 Section 3b — Working Directly with Layers](day-04-advanced-composition.md#3b-working-directly-with-layers--sdfprimspec-and-sdfpropertyspec)

---

### The Two Components — Both Required

Registration requires exactly two things working together. Neither alone is sufficient.

**Component 1 — `plugInfo.json` (Discovery)**

This file tells USD: "there is a plugin here, go load it when someone needs `TemperatureSensor`." It is the _address_ of the library. It does not perform registration itself.

```json
{
  "Plugins": [
    {
      "Name": "acmeSensors",
      "LibraryPath": "acmeSensors.so",
      "Types": {
        "AcmeSensors_TemperatureSensor": {
          "bases": ["UsdGeomXform"],
          "alias": { "UsdSchemaBase": "TemperatureSensor" }
        }
      }
    }
  ]
}
```

**Component 2 — `TF_REGISTRY_FUNCTION` (Actual Registration)**

This C++ macro is generated by `usdGenSchema` inside the compiled source. It runs when the shared library loads into memory, writing the type into the TfType registry.

```cpp
// Generated by usdGenSchema — do not write manually
// Runs when acmeSensors.so is loaded into the process

TF_REGISTRY_FUNCTION(TfType)
{
    TfType::Define<AcmeSensors_TemperatureSensor,
                   TfType::Bases<UsdGeomXform>>();
    // After this line:
    // Registry knows: TemperatureSensor → Xform → Xformable → Imageable → Typed → SchemaBase
}
```

> **Analogy — Street Address vs Showing Up**
>
> `plugInfo.json` is like posting your address on a directory — it tells people
> where to find you. But until you open the door and introduce yourself,
> you are not registered with the neighbourhood.
>
> `TF_REGISTRY_FUNCTION` is the moment of showing up. The address (manifest)
> and the introduction (macro) are both required. One without the other does nothing.

> **Exam trap — manifest file only:** "Implement the schema by subclassing UsdGeomImageable
> and registering it via a plugin manifest file **only**" is **WRONG**.
> The manifest enables discovery. `TF_REGISTRY_FUNCTION` in the C++ source
> performs the actual registration. Both are required.

---

### When Registration Runs — Per Process, Not Forever

This is the most commonly misunderstood aspect. Registration does **not** persist between processes and is never written to disk. Every new process rebuilds the registry by loading the plugin.

```
Process lifecycle for a custom schema type:

  Process starts
       |
       v
  USD scans PXR_PLUGINPATH_NAME
  Reads all plugInfo.json files
  Notes which plugins exist — does NOT load them yet
       |
       v
  Someone calls prim.IsA(TemperatureSensor)
       |
       v
  Registry check: "do I know TemperatureSensor?"
  Answer: No → "plugInfo.json says there's a library for this"
       |
       v
  acmeSensors.so loads into memory
  TF_REGISTRY_FUNCTION runs
  Type written into registry
       |
       v
  IsA(), fallbacks, API all work
  (for the lifetime of THIS process only)
       |
       v
  Process ends → registry gone from memory
  Next process starts from zero
```

> **Analogy — A Guest List at a Venue**
>
> Each time a new event starts (a new process), the venue sets up a fresh guest list.
> The plugin library is a guest who must check in at the door each time the event runs.
> Once checked in, they can move around freely for the whole event.
> When the event ends, the list is discarded — next event, check in again.
>
> This is why `PXR_PLUGINPATH_NAME` must be set in every environment that uses
> your custom schema — every render farm node, every artist machine, every CI runner.
> Each new process needs to find the plugin and register it fresh.

### What Happens Without the Plugin Deployed

If a colleague opens your USD file without the plugin in their `PXR_PLUGINPATH_NAME`:

```python
# The raw data is still readable — the file is not corrupted
prim.GetTypeName()                             # "TemperatureSensor" — string is there
prim.GetAttribute("sensor:temperature").Get()  # 23.5 — raw value readable

# But schema knowledge is gone
prim.IsA(TemperatureSensor)                    # False — type unknown
prim.IsA(UsdGeom.Xform)                        # False — ancestry unknown
sensor.GetTemperatureAttr()                    # AttributeError — API not available
sensor.GetTemperatureAttr().Get()              # None — no fallback
```

The file is not broken. The raw data is readable. But without the plugin, USD cannot interpret the type — no inheritance, no fallbacks, no generated API. The type name is just a string until the registry is populated.

---

### Exam Trap Summary for TfType

| Option phrasing                                               | Verdict | Why                                                          |
| ------------------------------------------------------------- | ------- | ------------------------------------------------------------ |
| "Register via plugin manifest file only"                      | Wrong   | `TF_REGISTRY_FUNCTION` in C++ source also required           |
| "Python-only schema"                                          | Wrong   | No `TF_REGISTRY_FUNCTION` — `IsA()` and fallbacks don't work |
| "Token registration without schema linkage"                   | Wrong   | Token alone = no inheritance, no fallbacks, no API           |
| "Modify USD core source to add the type"                      | Wrong   | Plugin system exists to avoid core modification entirely     |
| "UsdSchemaRegistry for dynamic loading without recompilation" | Wrong   | Requires plugin mechanisms or compile-time registration      |
| "Register with TfType AND deploy via PXR_PLUGINPATH_NAME"     | Correct | Both components required                                     |
| "Subclass UsdSchemaBase or a derived class"                   | Correct | UsdTyped and UsdGeomImageable ARE derived from UsdSchemaBase |

---

## 7. Custom File Format Plugins — SdfFileFormat

A **file format plugin** teaches USD to read and write a new file type (`.abc`, `.fbx`, `.myformat`). This is completely separate from custom schemas — schemas define what prim types mean; file format plugins define how data is read and written from files.

```
UsdSchema   = defines what scene data IS (prim types, attributes, meaning)
SdfFileFormat = defines how data is READ and WRITTEN to/from a file format
```

### Implementation Steps

```
1. Create a C++ class inheriting from SdfFileFormat
   class MyFormatPlugin : public SdfFileFormat { ... }

2. Implement required methods:
   bool Read(SdfLayer*, const string& resolvedPath, bool metadataOnly)
   bool WriteToFile(const SdfLayer&, const string& filePath, ...)

3. Register with TfType:
   TF_REGISTRY_FUNCTION(TfType) {
       TfType::Define<MyFormatPlugin,
                      TfType::Bases<SdfFileFormat>>();
   }

4. Declare in plugInfo.json for automatic discovery

5. When USD opens a .myformat file:
   → Looks up registered SdfFileFormat plugins
   → Finds MyFormatPlugin (registered for .myformat)
   → Calls MyFormatPlugin.Read() to translate to SdfLayer
   → Stage composes normally from that point
```

### ArResolver — Handling External References During File I/O

When your file format contains **references to external assets** (textures, sub-files, referenced layers), the plugin must integrate with **`ArResolver`** — USD's asset resolution system — to correctly locate those files.

```
Without ArResolver integration:
  MyFormat file contains: texture = "textures/wood.png"
  Plugin reads raw string "textures/wood.png" — but WHERE is it?
  Relative to what? The answer depends on the resolver context.

With ArResolver integration:
  Plugin calls ArResolver to resolve "textures/wood.png"
  → Resolver applies search paths, asset remapping, version pinning
  → Returns the actual absolute path to the correct file
  → File loading works correctly in all deployment environments
```

```cpp
// Inside your SdfFileFormat::Read() implementation:
ArResolver& resolver = ArGetResolver();
ArResolverContext ctx = resolver.GetCurrentContext();

// Resolve asset paths from the file using the resolver
std::string resolved = resolver.Resolve("textures/wood.png");
// resolved = "/project/assets/textures/wood.png"
```

> **Note 1:** "Ensure thread safety by implementing custom locking mechanisms" is **WRONG**. USD core manages concurrent access — file format plugins do not implement their own locking. This is unnecessary and handled at a higher level.

> **Note 2:** "Embed a custom USD stage cache within the plugin" is **WRONG**. Stage caching is managed by USD core and clients, not inside file format plugins. Embedding one causes inconsistencies.

### Wrong Approaches

| Wrong approach                                 | Why it's wrong                                                                                               |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Override `UsdStage::Open()`                    | Static method, not designed for overriding. File loading happens at the `SdfLayer` level, not `Stage` level. |
| Modify USD core source code                    | USD is designed for extensibility via plugins. Modifying core breaks compatibility.                          |
| Create a `UsdSchema` for the file format       | Schemas define scene description types. They do NOT control file I/O.                                        |
| Implement custom thread locking in Read/Write  | USD core manages concurrent access — plugins don't need custom locking                                       |
| Embed a stage cache inside the plugin          | Stage caching belongs at the USD core/client level — not inside file format plugins                          |
| Use `UsdUtils` exclusively to parse the format | UsdUtils provides utilities but does NOT replace implementing `SdfFileFormat` methods                        |
| Implement a `UsdStage` subclass for the format | UsdStage is format-agnostic — file format I/O is `SdfFileFormat`'s responsibility                            |

---

## 8. Model Kinds — Classifying Prims by Pipeline Role

A **model kind** is a metadata tag on a prim that describes its
**role in the pipeline** — not what it looks like geometrically,
but what function it serves in the scene assembly hierarchy.

```python
from pxr import Usd

model_api = Usd.ModelAPI(prim)
model_api.SetKind("component")   # tag this prim with its role
print(model_api.GetKind())       # "component"
```

Schema type answers: "what IS this prim?" (Mesh, Sphere, Light)
Model kind answers: "what ROLE does this prim play?" (assembly, component)

---

### The Four Built-in Kinds

```
assembly
  └── group
        └── component
              └── subcomponent
```

#### assembly

The top-level container that represents a complete published scene
or set. An assembly is what gets handed off between departments or
delivered to a client. It contains everything needed for the scene.

```
/ShotsRoot                   kind = assembly
  /ShotsRoot/Shot_042        kind = assembly
    /ShotsRoot/Shot_042/Set  kind = group
```

**Real example:** A complete city block handed from the environments
department to the lighting department. The whole city block is one
assembly — it is a self-contained deliverable.

```python
scene = stage.DefinePrim("/CityBlock", "Xform")
Usd.ModelAPI(scene).SetKind("assembly")
```

#### group

An organisational container inside an assembly. Groups do not
represent reusable assets — they are structural containers that
organise components into logical units.

```
/CityBlock                   kind = assembly
  /CityBlock/Buildings       kind = group     ← organises buildings
  /CityBlock/Streets         kind = group     ← organises streets
  /CityBlock/Props           kind = group     ← organises props
```

**Real example:** Inside the city block assembly, all the building
assets are grouped under `/CityBlock/Buildings`. The group itself
is not a reusable asset — it is just organisation.

```python
buildings = stage.DefinePrim("/CityBlock/Buildings", "Xform")
Usd.ModelAPI(buildings).SetKind("group")
```

#### component

A leaf reusable asset — the fundamental unit of content that gets
referenced into scenes. A component is self-contained, has a
`defaultPrim`, and can be referenced independently.

```
/CityBlock/Buildings/BuildingA   kind = component  ← one reusable building
/CityBlock/Buildings/BuildingB   kind = component  ← another building
/CityBlock/Props/Bench_001       kind = component  ← a bench asset
/CityBlock/Props/Lamppost_003    kind = component  ← a lamppost asset
```

**Real example:** A single chair asset. It has its own USD file,
its own materials, its own LOD variants. It is the smallest unit
that gets independently published, versioned, and referenced.

```python
chair = stage.DefinePrim("/World/Chair", "Xform")
Usd.ModelAPI(chair).SetKind("component")
```

**Components must:**

- Have `defaultPrim` set on their USD file
- Be self-contained (all materials inside the root prim)
- Be independently referenceable

#### subcomponent

An important named internal node within a component. Subcomponents
are not independently reusable — they exist only inside a component
and are tagged to signal that they are structurally significant.

```
/Chair                    kind = component
  /Chair/SeatGeo          kind = subcomponent  ← significant internal part
  /Chair/BackGeo          kind = subcomponent  ← significant internal part
  /Chair/LegFL            kind = subcomponent  ← front-left leg
  /Chair/LegFR            kind = subcomponent
```

**Real example:** Inside a character component, the head, torso,
and limbs are subcomponents — they are significant named parts
that tools might need to reference specifically (e.g. for attaching
accessories or applying targeted effects), but they are not
independently published assets.

```python
seat = stage.DefinePrim("/Chair/SeatGeo", "Mesh")
Usd.ModelAPI(seat).SetKind("subcomponent")
```

### The Full Hierarchy in a Real Scene

```
/Shot_042                          kind = assembly
  /Shot_042/Environment            kind = group
    /Shot_042/Environment/CityBlock  kind = assembly  ← nested assembly
      /Shot_042/.../Buildings        kind = group
        /Shot_042/.../BuildingA      kind = component
          /Shot_042/.../BuildingA/Facade  kind = subcomponent
  /Shot_042/Characters             kind = group
    /Shot_042/Characters/Hero      kind = component
      /Shot_042/.../Hero/Head      kind = subcomponent
      /Shot_042/.../Hero/Torso     kind = subcomponent
  /Shot_042/Props                  kind = group
    /Shot_042/Props/Bench_001      kind = component
```

### Why Model Kinds Matter in Practice

**Asset management tools** use model kinds to traverse the scene
and find all components — without having to know the specific
paths or types:

```python
from pxr import Usd

# Find all component-level assets in the scene
for prim in stage.Traverse():
    kind = Usd.ModelAPI(prim).GetKind()
    if kind == "component":
        print(f"Component asset: {prim.GetPath()}")
        # → can now check version, load payload, apply overrides
```

**Renderers and pipeline tools** use model kinds to decide what
to load, what to show in asset browsers, and what to include in
render submissions — without needing custom logic per project.

### Kind vs Schema Type — The Key Distinction

```
Schema type  answers: WHAT IS IT?
  prim.GetTypeName() → "Mesh", "Sphere", "Xform"
  Describes the geometric or functional type

Model kind   answers: WHAT ROLE DOES IT PLAY?
  Usd.ModelAPI(prim).GetKind() → "component", "assembly"
  Describes the pipeline and organisational role

A prim can be both:
  typeName = "Xform"      ← it IS an Xform (schema type)
  kind     = "component"  ← it PLAYS THE ROLE of a component (model kind)
```

### Quick Reference

| Kind           | Role                                     | Reusable?                         | Example                               |
| -------------- | ---------------------------------------- | --------------------------------- | ------------------------------------- |
| `assembly`     | Top-level complete scene or deliverable  | Yes — published                   | Full city block, complete shot        |
| `group`        | Organisational container within a scene  | No — structural only              | `/Buildings`, `/Props`, `/Characters` |
| `component`    | Leaf reusable asset — fundamental unit   | Yes — independently referenced    | Chair, building, character            |
| `subcomponent` | Significant internal part of a component | No — exists inside component only | Head, seat, facade panel              |

---

## 9. Custom Model Kinds — UsdModelKindRegistry

USD has a built-in hierarchy of **model kinds** that classify prims by their role in the scene:

```
assembly       ← top-level published collection of assets
  group        ← organisational container
    component  ← leaf reusable asset (a chair, a tree, a building)
      subcomponent ← important internal node within a component
```

### Creating Custom Model Kinds

To add a new kind (`factory_unit`) to this hierarchy:

**Step 1 — Define and register with `UsdModelKindRegistry`**

The kind must be registered with the registry so USD recognises it as valid.

```python
from pxr import Usd

registry = Usd.ModelKindRegistry.GetInstance()

registry.Register(
    "factory_unit",   # new kind name
    "component",      # parent kind — places it under component in hierarchy
)

# USD hierarchy after registration:
# assembly → group → component → factory_unit
```

**Step 2 — Set the kind on prims using `Usd.ModelAPI`**

```python
from pxr import Usd

prim = stage.DefinePrim("/Factory/Unit_A", "Xform")

# Set the kind using UsdModelAPI
model_api = Usd.ModelAPI(prim)
model_api.SetKind("factory_unit")

# Read the kind
print(model_api.GetKind())   # "factory_unit"
```

**Step 3 — Implement a schema plugin that INHERITS (not overrides) UsdModelAPI**

```
EXTEND UsdModelAPI   ← adds behaviour for the new kind

What you write manually:
  FactoryUnitAPI.h          ← C++ header declaring your class
  FactoryUnitAPI.cpp        ← C++ implementation
                               contains TF_REGISTRY_FUNCTION (written manually)
  plugInfo.json             ← manifest file (written manually)
```

#### Code Snippet:

```python
# In C++ — your schema plugin adds behaviour without replacing existing
#
# class FactoryUnitAPI : public UsdModelAPI {   ← EXTENDS UsdModelAPI
# public:
#
#     // Add new behaviour specific to factory_unit
#     bool GetFacilityId(std::string* facilityId) const;
#     bool SetFacilityId(const std::string& facilityId);
#
#     // Original UsdModelAPI methods still work unchanged:
#     // GetKind(), SetKind(), IsModel(), IsGroup() etc.
#     // Nothing is replaced — only added
# };
#
# In Python after the plugin is deployed:
factory_api = FactoryUnitAPI(prim)
factory_api.GetFacilityId()   # new method you added
factory_api.GetKind()         # original UsdModelAPI method still works
```

plugInfo.json

```python
{
  "Plugins": [{
    "Name": "factoryUnit",
    "LibraryPath": "factoryUnit.so",
    "Types": {
      "FactoryUnitAPI": {
        "bases": ["UsdModelAPI"]
      }
    }
  }]
}
```

````

What you run:
cmake + make ← compiles your C++ into factoryUnit.so

What you deploy:
factoryUnit.so
plugInfo.json
→ both placed in a directory
→ PXR_PLUGINPATH_NAME points to that directory

```

**Step 4 — Extend the `Validate()` method for domain-specific rules**

```python
Custom validation ensures `factory_unit` prims always have the required structure.

# In C++ — override Validate() to add factory_unit specific checks
#
# bool FactoryUnitAPI::Validate(std::string* reason) const {
#
#     // First run the parent validation — do NOT skip this
#     if (!UsdModelAPI::Validate(reason)) {
#         return false;   // fails standard component rules → reject
#     }
#
#     // Now add factory_unit specific rules on top
#     UsdPrim prim = GetPrim();
#
#     // Rule 1: must have pipeline:facilityId metadata
#     std::string facilityId;
#     if (!GetFacilityId(&facilityId) || facilityId.empty()) {
#         *reason = "factory_unit must have pipeline:facilityId set";
#         return false;
#     }
#
#     // Rule 2: must have at least one TemperatureSensor child
#     bool hasSensor = false;
#     for (const auto& child : prim.GetChildren()) {
#         if (child.IsA<AcmeSensors_TemperatureSensor>()) {
#             hasSensor = true;
#             break;
#         }
#     }
#     if (!hasSensor) {
#         *reason = "factory_unit must contain at least one TemperatureSensor";
#         return false;
#     }
#
#     return true;   // passes all rules
# }
#
# In Python after the plugin is deployed:
factory_api = FactoryUnitAPI(prim)
is_valid, reason = factory_api.Validate()
if not is_valid:
    print(f"Invalid factory_unit: {reason}")
    # "factory_unit must have pipeline:facilityId set"
```

### Wrong Approaches

| Wrong approach                                  | Why                                                                            |
| ----------------------------------------------- | ------------------------------------------------------------------------------ |
| Override (not extend) UsdModelAPI               | Replaces existing behaviour — breaks standard kinds                            |
| Register token in TfType without schema linkage | Provides a name but no behaviour, API, or validation                           |
| Use variants within the model kind              | Variants = content variation. Model kinds = classification. Separate concerns. |
| Modify USD core source                          | USD's plugin and registry system exists to avoid this                          |

---

## 10. Exam Pattern Recognition — Elimination Guide

### Pattern 1 — "How do you create a custom schema?"

**Correct answer framework:**

1. Write `schema.usda`
2. Inherit from **`UsdTyped`** or **`UsdGeomImageable`** (NOT `UsdSchemaBase` directly)
3. Run **`usdGenSchema`** to generate C++ and Python
4. Register with **TfType system** via `plugInfo.json`
5. Deploy as plugin via `PXR_PLUGINPATH_NAME`

### Pattern 2 — "How do you add a new file format?"

**Correct answer framework:**
Implement the **`SdfFileFormat` interface** + register with **TfType system** + declare in `plugInfo.json`

### Pattern 3 — "How do you create custom model kinds?"

**Correct answer framework:**
Unique token + **`UsdModelKindRegistry`** + `kind` metadata on root prim via **`UsdModelAPI`** + schema plugin that **inherits** (EXTENDS, not overrides) `UsdModelAPI` + extended `Validate()` method

### Pattern 4 — "Extend vs Override"

> Any option saying "**override**" an existing schema, API, or core system = **WRONG**. USD is always extended, never overridden. Overriding breaks existing functionality for all users of that schema. Extending (inheriting from, adding to) maintains backward compatibility while adding new capabilities.

### Instant Elimination Phrases

Eliminate **any option** containing these phrases immediately:

| Phrase in option                                                | Reason to eliminate                                                                                 |
| --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `"Modify the core USD source code"`                             | USD uses plugins — never modifies core                                                              |
| `"Python-only schema"` or `"subclassing Usd.Schema in Python"`  | Full schemas need C++ + usdGenSchema                                                                |
| `"Overriding"` any existing schema, API, or method              | Always EXTEND — never override                                                                      |
| `"Override UsdStage::Open()"`                                   | File formats use `SdfFileFormat`, not Stage::Open                                                   |
| `"Register token in TfType WITHOUT schema or API linkage"`      | Token alone is insufficient — needs full schema backing                                             |
| `"Define schema in a .usd file at runtime"`                     | Schemas defined in `schema.usda` + compiled offline                                                 |
| `"Create new UsdSchema to control file format I/O"`             | Schemas ≠ file I/O — use `SdfFileFormat`                                                            |
| `"Embed fallback variant selections in prim metadata"`          | Fallbacks belong at stage/layer level, not prim metadata                                            |
| `"Plugin manifest file only"` for schema registration           | `TF_REGISTRY_FUNCTION` macro in C++ source is ALSO required — manifest alone is insufficient        |
| `"Custom locking in Read/Write"` for file format plugins        | USD core manages concurrency — plugins don't implement locking                                      |
| `"Embed stage cache in file format plugin"`                     | Stage caching belongs at USD core/client level, not in plugins                                      |
| `"Implement UsdStage subclass for new file format"`             | UsdStage is format-agnostic — use `SdfFileFormat`                                                   |
| `"USD auto-selects variants alphabetically"`                    | USD does NOT auto-select variants — fallbacks must be explicitly defined                            |
| `"UsdSchemaRegistry for dynamic loading without recompilation"` | Custom schemas require plugin mechanisms or compile-time registration — not dynamic runtime loading |
| `"Using UsdUtils exclusively to parse custom format"`           | UsdUtils provides utilities but does not replace implementing `SdfFileFormat` methods               |

---

## 11. Key Takeaways

| Concept                            | What to Remember                                                                                                        |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **IsA schema**                     | Defines a prim type. Sets `typeName`. One per prim. Check with `prim.IsA()`                                             |
| **API schema**                     | Augments a prim. No `typeName`. Multiple per prim. Check with `prim.HasAPI()`                                           |
| **Custom schema base**             | `UsdTyped` for standard schemas. `UsdGeomImageable` for renderable. NOT `UsdSchemaBase` directly                        |
| **usdGenSchema**                   | Generates C++ and Python from `schema.usda`. Required for full integration                                              |
| **TfType = runtime type registry** | Transforms a type name string into a meaningful type with full inheritance chain, fallbacks, and API                    |
| **Two components required**        | `plugInfo.json` (discovery address) + `TF_REGISTRY_FUNCTION` in C++ (actual registration). Neither alone is sufficient. |
| **`TF_REGISTRY_FUNCTION`**         | C++ macro generated by `usdGenSchema`. Runs when library loads into memory. Writes type into registry.                  |
| **Registration is per-process**    | Registry lives in memory only. Every new process reloads the plugin and re-registers. Never written to disk.            |
| **Without plugin deployed**        | Raw data readable. But `IsA()` = False, fallbacks = None, API = AttributeError. File not corrupted.                     |
| **`PXR_PLUGINPATH_NAME`**          | Must be set in every environment — render farm, artist machine, CI. Each new process needs to find the plugin.          |
| **Python-only schemas**            | No `TF_REGISTRY_FUNCTION` generated — `IsA()` and fallbacks don't work. Prototyping only, not production.               |
| **SdfFileFormat**                  | For teaching USD to read/write new file formats. Independent of schemas                                                 |
| **UsdModelKindRegistry**           | Register custom model kinds here. Use `Usd.ModelAPI.SetKind()` to apply                                                 |
| **Extend vs Override**             | Always EXTEND UsdModelAPI — never override. Override breaks existing kinds                                              |
| **Schema file format separation**  | Schema = what data IS. SdfFileFormat = how data is STORED. Independent.                                                 |

---

_Previous: [Day 4 — Advanced Composition Concepts](day-04-advanced-composition.md)_
_Next: [Day 6 — Visualization](day-06-visualization.md)_
````
