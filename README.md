# skills2026-lekiwi

Plug-and-play LeKiwi tooling for the 2026 Skills Ontario ECU workflow.

This project is meant for a student team that wants the easiest realistic path:

- LeKiwi + leader arm
- two RGB cameras: front and wrist
- LeRobot as the official robot/data backbone
- OpenCV + scripted FSM control as the default competition path
- ACT later for the few precision/contact steps that still need help

If you know nothing yet, start at **Start Here** below and go in order.

## Start Here

This repo does **not** replace the official rules or official LeRobot setup docs.
Read these first and keep them open while you work:

- [Skills Ontario Robotics competition page](https://www.skillsontario.com/skills-ontario-competition)
- [2026 Robotics scope PDF](https://www.skillsontario.com/files/www/2026_Scopes/2026_-_Robotics_-_EN_-_2025-09-12.pdf)
- [2026 Appendix A](https://skillsontario.com/wp-content/uploads/2026_-_Robotics_-_Appendix_A_-_2025-09-19.pdf)
- [2026 Appendix C sample wiring diagrams](https://skillsontario.com/wp-content/uploads/2026_-_Robotics_-_Appendix_C.pdf)
- [2026 Appendix D inspection sheet](https://skillsontario.com/wp-content/uploads/2026_-_Robotics_-_Appendix_D.pdf)
- [LeRobot LeKiwi docs](https://huggingface.co/docs/lerobot/en/lekiwi)
- [LeRobot camera docs](https://huggingface.co/docs/lerobot/en/cameras)
- [LeRobot imitation learning on real robots](https://huggingface.co/docs/lerobot/en/il_robots)
- [LeRobot ACT docs](https://huggingface.co/docs/lerobot/en/act)

## What This Repo Does

This repo adds:

- a beginner-friendly setup UI
- saved robot profiles
- hardware discovery and readiness checks
- two-camera runtime budgeting for a Pi 5 4 GB
- OpenCV perception:
  - front camera for coarse scene understanding
  - wrist camera for close alignment and verification
- scripted ECU primitives with graceful fallback to front-only mode
- a full match task catalog for the main Ontario scoring buckets
- an ACT-ready data collection and replay workflow
- teleop / record / replay helpers that stay close to official LeRobot workflows

## What This Repo Does Not Do

This repo does **not**:

- assemble the robot for you
- set motor IDs automatically unless your LeRobot base setup is already correct
- replace the official LeRobot install/calibration steps
- guarantee legal competition compliance by itself
- train an ACT policy for you automatically

You still need to:

- build the robot safely
- wire it legally
- bring a kill switch
- bring a wiring diagram
- calibrate the follower and leader arms
- test the complete system before competition day

## Why This Approach Fits Skills Ontario

The ECU tasks are more forgiving than they first appear:

- Appendix A says the fuse holes are drilled through and are **1 1/8 inch** diameter for **1 inch** fuse dowels, which makes fuse insertion easier.
- Appendix A says fuses are painted for **2 inches** and left unpainted for **1 inch**, which gives a built-in insertion cue.
- Appendix A says circuit board storage spacing is **5/8 inch** for a loose fit around **1/2 inch** boards.
- Appendix A says transformer storage spacing is **7/8 inch** for a loose fit around **3/4 inch** parts.
- The scope says tele-operated robots may **not** transmit audio/visual information off the robot during competition.
- The scope and inspection sheet require a **single-motion kill switch** and a **wiring diagram**.

Because of that, the best short-timeline path is:

1. make fuses work first
2. make boards work second
3. leave transformers for later
4. keep OpenCV + scripted control as the baseline
5. add ACT only after the baseline is repeatable

## Recommended Build Order

If you are new, do the project in this order:

1. Build and wire the robot safely.
2. Get official LeRobot + LeKiwi working.
3. Calibrate the follower arm and leader arm.
4. Use this repo’s UI to make a saved profile.
5. Get teleop working.
6. Run the scripted fuse workflow.
7. Run the scripted board workflow.
8. Record data only after teleop and replay are stable.
9. Add ACT only after the scripted version is already useful.

Do **not** start with:

- transformers
- end-to-end learned policies
- depth cameras
- policy experiments before the scripted baseline works

## Hardware Checklist

Minimum practical setup:

- LeKiwi robot
- follower arm on the robot
- SO100 leader arm
- front RGB camera
- wrist RGB camera
- robot computer:
  - Raspberry Pi 5 4 GB is acceptable for the scripted OpenCV stack
- development laptop
- accessible kill switch
- printed wiring diagram
- tabletop stand

## Software Layout

Recommended split:

- robot computer:
  - LeRobot
  - LeKiwi host
  - cameras
  - competition-local runtime
- laptop:
  - LeRobot
  - this repo
  - setup UI
  - teleop
  - recording and debugging

This repo supports two modes:

- `dev_remote`
  - robot host on the robot computer
  - operator tools on the laptop
- `competition_local`
  - perception and control run locally on the robot
  - use this for competition because off-robot video is not allowed

## Step 1: Install LeRobot and LeKiwi

Do this on the robot computer first, then on the laptop.

Follow the official LeRobot installation guide from the LeRobot docs. After that, inside your `lerobot` checkout, install the LeKiwi extras:

```bash
python3 -m pip install -e ".[lekiwi]"
```

The LeKiwi docs say you should do this on both:

- the robot computer
- the local laptop or PC

This repo works out of the box with LeKiwi in either of these two setups:

- `lerobot` is already installed in your Python environment
- this repo is cloned beside a sibling `lerobot/` checkout

Example folder layout:

```text
robotics/
  lerobot/
  skills2026-lekiwi/
```

If your `lerobot` checkout lives somewhere else, set:

```bash
export LEROBOT_SRC=/absolute/path/to/lerobot/src
```

That makes the LeKiwi host and helper commands find LeRobot correctly.

## Step 2: Find Ports and Configure Motors

Use the official LeRobot tools before using this repo.

Find the controller board port:

```bash
lerobot-find-port
```

Set up LeKiwi motors:

```bash
lerobot-setup-motors \
  --robot.type=lekiwi \
  --robot.port=/dev/tty.usbmodemXXXX
```

If this part is wrong, nothing else in this repo will feel reliable.

## Step 3: Calibrate the Robot and Leader Arm

Calibrate the follower arm on the robot:

```bash
lerobot-calibrate \
  --robot.type=lekiwi \
  --robot.id=my_awesome_kiwi
```

Calibrate the leader arm on the laptop:

```bash
lerobot-calibrate \
  --teleop.type=so100_leader \
  --teleop.port=/dev/tty.usbmodemXXXX \
  --teleop.id=my_awesome_leader_arm
```

Do not skip calibration. The official LeKiwi docs treat it as important for reliable transfer and policy behavior.

## Step 4: Clone and Install This Repo

```bash
git clone https://github.com/Shaurya-Bhushan/skills2026-lekiwi.git
cd skills2026-lekiwi
python3 -m pip install -e .
```

## Step 5: Run the Beginner Setup UI

Start the UI:

```bash
skills2026 ui
```

In the UI:

1. detect the front and wrist cameras
2. assign the leader arm port
3. assign the robot serial port
4. choose a profile name
5. choose `dev_remote` while developing
6. keep `opencv_fsm` as the default backend
7. save the profile
8. run the readiness check

The recommended beginner path in this repo is:

- OpenCV + FSM first
- ACT later

## Step 6: Capture Live Setup

When the robot is powered and the cameras are working:

```bash
skills2026 setup
```

This command helps you save:

- current ports
- camera IDs
- camera calibration clicks
- service poses

If the robot is not powered yet, you can still save the basic profile:

```bash
skills2026 setup --skip-live
```

## Step 7: Check Readiness

Run:

```bash
skills2026 doctor
```

This checks:

- front camera present
- wrist camera present
- camera frame capture
- leader port
- robot serial port
- service poses
- competition checklist

Do not move on until `doctor` is mostly clean.

## Step 8: Teleoperate First

Before trying autonomous behavior, make sure teleop works:

```bash
skills2026 teleop
```

What success looks like:

- leader arm moves the follower arm correctly
- the robot does not jerk or drift unexpectedly
- front and wrist cameras make sense
- base stop behavior is safe

If teleop is not solid, do not start data collection yet.

## Step 9: Start With Fuses

This is the first Ontario Skills ECU task you should automate.

Why:

- fuse color is easy to detect
- the insertion end is visually obvious
- the hole is oversized relative to the fuse

Use the stack like this:

- front camera:
  - find fuse
  - find the target hole color
  - plan the coarse approach
- wrist camera:
  - refine alignment
  - verify the insertion end
  - verify full insertion

Run the scripted competition stack:

```bash
skills2026 competition ecu --primitive insert_fuse --target-color green
```

Repeat with the other colors once one color works.

## Step 10: Do Boards Next

Boards are the next best Ontario Skills target because the visual cues are large:

- malfunctioning board: big `X`
- functioning board: green strip

Use:

```bash
skills2026 competition ecu --primitive insert_board --target-slot center
```

You will probably need to adjust your service poses and calibration a few times before board insertion feels clean.

## Step 11: Leave Transformers For Later

Transformers are harder because:

- they are larger
- contact matters more
- barrel-bolt motion is more jam-prone

This repo includes transformer primitives, but the intended beginner path is:

1. fuses
2. boards
3. only then transformers

## Step 12: Expand To The Full Ontario Match

Once the ECU work is stable, this repo can also sequence the other major Ontario task families:

- fallen beam clearing
- debris clearing
- supply delivery
- supply orientation
- full ECU repair sequences:
  - remove bad part
  - discard bad part
  - pick replacement
  - install replacement
- ECU fan placement
- worker safety checks
- Steve to lobby
- breaker flip
- final-position finish flow

Run the full mission system with:

```bash
skills2026 competition mission --mission-name full_match
```

Other presets:

```bash
skills2026 competition mission --mission-name ecu_only
skills2026 competition mission --mission-name rescue_support
```

## Step 13: Record Data Only After Baseline Works

Once teleop and scripted control are stable, collect demonstrations:

```bash
skills2026 record insert_fuse
```

Then replay them:

```bash
skills2026 replay default_insert_fuse 0
```

The LeRobot docs recommend starting with at least **50 episodes** for a simple task and keeping the cameras fixed and the demonstrations consistent.

If replay looks bad, fix:

- calibration
- camera mount stability
- approach poses
- gripper behavior

Do not train around bad data.

## Step 14: Add ACT Later

### ACT

ACT is the first official LeRobot policy worth trying for this project because the LeRobot docs describe it as:

- recommended first for beginners
- trainable in a few hours on one GPU
- about 80M parameters
- often useful with around 50 demonstrations

Use ACT for:

- fuse insertion refinement
- bolt sliding refinement

Do **not** use ACT as the first thing you build.

## Match-Day Mode

Before competition, switch your profile to:

- `competition_local`

Make sure:

- processing runs on the robot computer
- no off-robot video is being sent to the driver station
- kill switch is mounted and reachable
- wiring diagram is printed
- tabletop stand is ready
- default backend is still `opencv_fsm` unless your ACT workflow is already proven

## Common Commands

```bash
skills2026 ui
skills2026 setup --skip-live
skills2026 setup
skills2026 doctor
skills2026 teleop
skills2026 record insert_fuse
skills2026 replay default_insert_fuse 0
skills2026 competition ecu --primitive insert_fuse --target-color green
skills2026 competition ecu --primitive insert_board --target-slot center
skills2026 competition mission --mission-name full_match
```

## If Something Is Going Wrong

Check these first:

1. Is LeRobot installed and working?
2. Are the motor IDs correct?
3. Are the leader and follower calibrated?
4. Did the camera IDs change after reboot?
5. Did the camera mount move?
6. Are the service poses still valid?
7. Are you accidentally trying to solve transformers before fuses work?

## Project Philosophy

This repo is intentionally biased toward:

- simple tools
- visible failures
- easy debugging
- beginner-friendly workflows
- reliable match behavior over flashy demos

That is why the default path is:

- official LeRobot / LeKiwi
- OpenCV
- scripted FSM primitives
- ACT only after the scripted baseline is dependable

## Sources

- [Skills Ontario Robotics competition page](https://www.skillsontario.com/skills-ontario-competition)
- [2026 Robotics scope PDF](https://www.skillsontario.com/files/www/2026_Scopes/2026_-_Robotics_-_EN_-_2025-09-12.pdf)
- [2026 Appendix A](https://skillsontario.com/wp-content/uploads/2026_-_Robotics_-_Appendix_A_-_2025-09-19.pdf)
- [2026 Appendix C sample wiring diagrams](https://skillsontario.com/wp-content/uploads/2026_-_Robotics_-_Appendix_C.pdf)
- [2026 Appendix D inspection sheet](https://skillsontario.com/wp-content/uploads/2026_-_Robotics_-_Appendix_D.pdf)
- [LeRobot LeKiwi docs](https://huggingface.co/docs/lerobot/en/lekiwi)
- [LeRobot camera docs](https://huggingface.co/docs/lerobot/en/cameras)
- [LeRobot imitation learning on real robots](https://huggingface.co/docs/lerobot/en/il_robots)
- [LeRobot ACT docs](https://huggingface.co/docs/lerobot/en/act)
