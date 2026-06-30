# 🤖 Physical AI Learning Journey — Sparsha Srinath

> Full stack developer with 2 years of experience transitioning into Physical AI and robotics simulation.
> Documenting my path from zero to NVIDIA Omniverse developer — honest notes, real friction points, and everything I build along the way.

<a href="#"><img src="https://img.shields.io/badge/OpenUSD-In%20Progress-76b900?style=flat-square&logo=nvidia&logoColor=white" alt="OpenUSD In Progress"/></a>
<a href="#"><img src="https://img.shields.io/badge/Isaac%20Sim-In%20Progress-0078D4?style=flat-square&logo=nvidia&logoColor=white" alt="Isaac Sim In Progress"/></a>
<a href="#"><img src="https://img.shields.io/badge/Omniverse-In%20Progress-7B2FBE?style=flat-square&logo=nvidia&logoColor=white" alt="Omniverse In Progress"/></a>
<a href="#"><img src="https://img.shields.io/badge/Physical%20AI-Learning-FF6B35?style=flat-square" alt="Physical AI Learning"/></a>

---

## 🗺️ Timeline

```
Jun 24 ──────── Jun 24-29 ──────── Jun 30 ──────── Jul 1 ──────── Jul 2
   │                │                  │               │              │
 Setup           OpenUSD            Omniverse        Synthetic     Physics
 Brev +          Cert 🔄            Intro Course     Data Gen      Sim
 Isaac Sim 🔄                        ⏳               ⏳            ⏳
```

---

## 🔄 Jun 24 — Brev cloud setup

**Goal:** Get Isaac Sim running without a local NVIDIA GPU.

**Status:** In progress · Jun 24, 2026

Isaac Sim requires an NVIDIA RTX GPU — running on Intel Iris Xe on Mac locally, so set up NVIDIA Brev cloud to spin up a GPU instance on demand. This is the recommended path for developers without local RTX hardware.

- Created NVIDIA Brev account
- Located Isaac Sim 6.0.0 with ROS2 Jazzy launchable (L40S GPU · $2.27/hr)
- Deployment ready

[📝 Setup notes →](./01-brev-setup/notes.md) | [📸 Screenshots →](./01-brev-setup/screenshots/)

---

## 🔄 Jun 24–29 — OpenUSD Certification

**Goal:** Understand the foundational language of the entire Physical AI stack.

**Status:** In progress · Jun 24–29, 2026

OpenUSD (Universal Scene Description) is the file format and framework that underpins Omniverse, Isaac Sim, and every robot and simulation asset in the Physical AI ecosystem. Originally built by Pixar for film pipelines, adopted by NVIDIA as the foundation of Omniverse.

**Key concepts:**

- Stage composition and prim hierarchy
- USD schemas and typed prims
- Referencing, layering, and composition arcs
- Python scripting with the USD API
- Why USD enables interoperability across the entire Physical AI stack

[📝 Cert notes →](./02-openUSD-cert/notes/) | [💡 Key concepts →](./02-openUSD-cert/notes/README.md)

---

## 🔄 Jun 30 — An Introduction to Developing With NVIDIA Omniverse

**Goal:** Understand how Omniverse applications are built and extended.

Omniverse is NVIDIA's platform built on top of OpenUSD — the runtime, renderer, and app ecosystem that powers Isaac Sim and the broader Physical AI stack. This course covers building a Kit-based application from a template and customizing it via extensions.

**Key concepts:**

- How `.kit` files define and assemble Omniverse applications
- Adding and configuring extensions
- How Omniverse supports OpenUSD workflows under the hood
- The relationship: OpenUSD → Omniverse → Isaac Sim

[📝 Notes →](./03-omniverse-intro-course/notes.md) | [💡 Kit file explainer →](./03-omniverse-intro-course/kit-file-explained.md) | [📸 Screenshots →](./03-omniverse-intro-course/screenshots/)

---

## ⏳ Jul 1 — Synthetic Data Generation

**Goal:** Build a data pipeline that generates training data for AI models at scale.

Synthetic data generation (SDG) is one of the most critical use cases for Physical AI — it lets you train robot models on thousands of varied scenarios without real-world data collection. Using Omniverse Replicator to randomise lighting, object placement, and camera angles.

[📝 Workflow →](./04-synthetic-data/workflow.md) | [🐍 Script →](./04-synthetic-data/replicator-script.py) | [📸 Screenshots →](./04-synthetic-data/screenshots/)

---

## ⏳ Jul 2 — Physics Simulation

**Goal:** Load a robot with real physics, sensors, and simulate its behaviour.

Physically accurate simulation is what makes Isaac Sim valuable for robotics — robots trained in simulation behave predictably in the real world because the physics match. Covers articulation, joint drives, rigid body dynamics, and sensor attachment.

[📝 Notes →](./05-physics-sim/notes.md) | [📸 Screenshots →](./05-physics-sim/screenshots/)

---

## 💡 What I learned

> Updated as I go — honest reflections on the developer experience, friction points, and what other developers coming from a software background should know before starting.

| Insight       | When |
| ------------- | ---- |
| _Coming soon_ | —    |

---

## 🔗 Resources

| Resource                 | Link                                                                                                                      |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| NVIDIA OpenUSD Cert      | [developer.nvidia.com/usd](https://developer.nvidia.com/usd)                                                              |
| Isaac Sim Docs           | [docs.isaacsim.omniverse.nvidia.com](https://docs.isaacsim.omniverse.nvidia.com)                                          |
| Omniverse DLI Courses    | [learn.nvidia.com](https://learn.nvidia.com)                                                                              |
| Isaac Sim on Brev        | [Brev cloud setup](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_advanced_cloud_setup_brev.html) |
| NVIDIA Developer Discord | [discord.gg/nvidiaomniverse](http://discord.gg/nvidiaomniverse)                                                           |

---

<p align="center">
  <i>Updated daily · Jun 26 – Jul 3, 2026</i>
</p>
