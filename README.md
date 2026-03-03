# simulated-city-template

This is a template repository.

Get started by reading [docs/setup.md](docs/setup.md).
See [docs/overview.md](docs/overview.md) for an overview of the base module content.

## Template for a project

### Step 1: Define Your Simulation (Before Any Code)

Use this template to describe your project. Think about these four components and the messages they send between each other:

### My Smart City Project: Halftime Queue Dynamics in Stadium Section A4

#### 1. The Trigger (Who/What is moving?)
**Agents:** Spectators in Section A4 (about 1,000 people) moving between seats, cafés, toilets, and urinals.

**Surroundings:**
- Halftime duration is fixed at 15 minutes, creating strong time pressure.
- Walking time varies by seat position: about 30 seconds to 5 minutes one way.
- Demand peaks in the first 3–5 minutes after halftime starts.
- Spectators can choose different activity orders (toilet first, café first, one service only, or coordinated group behavior).

#### 2. The Observer (What does the city see?)
The simulation observes virtual sensor/events for:
- Queue arrivals at cafés, women’s toilets, men’s toilets, and urinals
- Current queue length per line and per zone
- Service start and completion times
- Concourse congestion when queue lengths begin blocking walking paths
- Remaining halftime time for each spectator

#### 3. The Control Center (The Logic)
The control logic updates movement and queue behavior over time:
- Spectators select facilities and sequence of actions based on needs and available time.
- Service times are randomized (café: 30–60 seconds, toilets: 1–3 minutes, urinals faster on average).
- If queues grow to around 15 people per line (up to 8 lines), movement paths are blocked and walking speed is reduced.
- Spectators may abandon queues, skip services, or stay seated if they risk missing kickoff.
- Two identical café zones are modeled so spectators can choose either area.

#### 4. The Response (What happens next?)
The controller updates facility states and publishes measurable outcomes for each simulation run:
- **Maximum queue length** at cafés and toilets
- **Average waiting time** in queues
- **Missed kickoff count** (spectators not back in seat before second half)

These outputs show how congestion forms in Section A4 and help compare halftime scenarios under different crowd and timing conditions.

---

## Workflow: Document-Driven Development with AI

**This is how you work with any AI model (including GitHub Copilot, ChatGPT, Claude, etc.). The approach works regardless of which model your school uses.**

### Phase 1: Clarify Your Idea with AI (No Code Yet)

#### Copy this prompt into your AI chat:

```
I want to build a simulated city based on this outline. 
Please help me clarify it before I code.

[Paste your Project Template filled in above]

Please:
1. Rewrite the 4 components using clear, technical language
2. Identify the MQTT topics each agent will publish/subscribe to
3. List any configuration parameters (MQTT broker, locations, thresholds)
4. Point out any ambiguities or missing details

Do NOT write any code. Just clarify the design.
```

#### Review the AI's response
- Does it capture your idea correctly?
- Are the agents clearly separated?
- Are the MQTT topics clear?
- If not, refine and ask again

---

### Phase 2: Get an Implementation Plan (Still No Code)

#### Once you agree on the design, use this prompt:

```
Based on the design we just clarified:

[Paste the clarified design from Phase 1]

Please propose a phased implementation plan:
- Phase 1: Single basic agent (smallest working notebook)
- Phase 2: Add configuration file
- Phase 3: Add MQTT publishing
- Phase 4: Add second agent with MQTT subscription
- Phase 5: Add dashboard visualization

For each phase:
1. List what new notebook files will be created
2. List what tests/verifications I should run
3. Say exactly what I should investigate/understand before moving to the next phase

Do NOT write code yet. Just show the phases.
```

#### Review and approve the plan
- Does each phase test one new thing?
- Can you run and understand each phase?
- Are there gaps?
- Ask AI to adjust if needed

---

### Phase 3: Implement ONE Phase at a Time

#### For the FIRST phase only, use this prompt:

```
Implement ONLY Phase 1 from the plan above:
[Paste Phase 1 description]

Remember these rules (from .github/copilot-instructions.md):
- Use anymap-ts for mapping (NOT folium)
- Each notebook is ONE agent (NOT monolithic)
- Load config via simulated_city.config.load_config()
- Use mqtt.publish_json_checked() for publishing
- Add all dependencies to pyproject.toml (NOT !pip install in notebooks)

Only implement Phase 1. Do NOT jump ahead to Phase 2.
Include comments explaining each section.
```

#### After you get the code:
```bash
python scripts/verify_setup.py      # Check dependencies
python -m pytest                     # Run tests
python -m jupyterlab                # Open the notebook and RUN IT
```

#### Investigate before moving forward
- Does the notebook actually run without errors?
- Can you explain what each cell does?
- Does it match the design from Phase 1?
- If something is wrong, ask AI to fix it before moving to Phase 2

---

### Phase 4: Move to the Next Phase

Once Phase 1 works, use this prompt:

```
Good! Phase 1 works. Now implement ONLY Phase 2:
[Paste Phase 2 description]

The Phase 1 notebooks/code are:
[List what was created in Phase 1]

Implement only Phase 2. Do NOT modify Phase 1 code unless necessary.
```

**Repeat this cycle for each phase.**

---

## Key Rules to Remember

✅ **DO** enforce these in every AI prompt:
1. Two separate MQTT topics are better than one shared variable
2. Each agent notebook is independent and can restart anytime
3. Configuration comes from `config.yaml`, not hardcoded values
4. All dependencies go in `pyproject.toml` first, then `pip install -e ".[notebooks]"`
5. Dependencies must be approved: `anymap-ts` ✅, `folium` ❌

❌ **DO NOT** let AI:
- Skip the documentation/planning phases
- Create one giant notebook with all logic
- Jump to implementation without a clear, approved design
- Install packages inside notebooks with `!pip install`
- Use `folium`, `matplotlib`, or `plotly` for real-time maps

---

## If the AI Skips Steps

If you ask for implementation and the AI writes code without clarifying the design first, respond with:

> "No code yet. I need to clarify the design first. Please rewrite my outline using the Phase 1 prompt above, then we'll get a plan before any implementation."

If the AI proposes all 5 phases at once instead of letting you implement one at a time:

> "I need only Phase 1 implementation. We'll do the other phases after I test Phase 1. Just give me Phase 1 code."

If the AI installs `folium` or uses `!pip install`:

> "No, use anymap-ts and add dependencies to pyproject.toml. Also, re-read .github/copilot-instructions.md for the full list of rules."

---

## Testing Your Work

After each phase, run:

```bash
# Check environment
python scripts/verify_setup.py

# Run existing tests
python -m pytest

# Try your new notebook
python -m jupyterlab
# Open the notebook and run all cells
```

Before submitting a pull request, include this in your description:

```
Docs updated: yes/no
Phases completed: [e.g., "Phase 1 and Phase 2"]
Tests passing: yes/no
```