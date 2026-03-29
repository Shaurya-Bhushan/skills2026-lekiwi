# skills2026-lekiwi

Plug-and-play LeKiwi tooling for the 2026 Skills Ontario ECU and Steve workflow.

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

## Quick Answer: Do You Need Training?

Short answer: **no, not for the first useful version of this system**.

This repo is intentionally built so the first competition-ready baseline is:

- two RGB cameras
- OpenCV perception
- scripted finite-state-machine control
- no learning required

That means:

- you can bring up fuse work without training
- you can bring up circuit-board work without training
- you can bring up Steve pickup and lobby delivery without training
- you can attempt transformer work without training

Training is **optional**, not mandatory.

You should only add ACT later if:

- fuse insertion is still not reliable enough after calibration and pose tuning
- transformer bolt/contact behavior is still your main failure after the scripted baseline is already usable
- your teleop demos are clean and replayable

If the scripted system already scores enough points for your goals, you do **not** need training at all.

## What Plug-And-Play Means Here

This repo is designed to be as plug-and-play as realistically possible for LeKiwi, but it is **not** magic and it is **not** zero-setup.

In this repo, plug-and-play means:

- the system stays close to official LeRobot and LeKiwi workflows
- the setup is guided through a beginner UI
- your robot settings are saved in a reusable profile
- daily startup is repeatable
- the default backend is already chosen for you
- the commands for teleop, readiness checks, ECU tasks, and missions are already organized

It does **not** mean:

- no calibration
- no motor setup
- no pose capture
- no camera mounting
- no tuning

The goal is:

1. do the hard setup once
2. save it
3. reuse it every practice session
4. keep the daily workflow simple for students

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
- a task catalog centered on ECU repair, transformers, circuit boards, and Steve
- an ACT-ready data collection and replay workflow
- an optional ACT competition backend for trained checkpoints
- teleop / record / replay helpers that stay close to official LeRobot workflows

## What The User Must Still Do

The system is only as good as the physical setup you give it.

You still need to provide:

- a working LeKiwi robot
- a working leader arm
- a rigid front camera mount
- a rigid wrist camera mount
- correct motor IDs and robot wiring
- a safe kill switch
- a printed wiring diagram
- a known ECU service pose the robot can reach consistently
- enough lighting that the cameras can clearly see colors and markings

You also need to do these one-time setup tasks:

- install LeRobot and LeKiwi correctly
- calibrate the follower arm
- calibrate the leader arm
- detect and save camera IDs
- capture camera calibration
- capture service poses for each main task

If any of those are skipped, the system will still run, but it will not feel truly plug-and-play.

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

## What Works Without Training

The baseline system is meant to work **without training** for the Ontario tasks this repo focuses on.

That baseline is strongest for:

- fuse pickup and fuse insertion
- board removal and board insertion
- Steve pickup and Steve placement in the lobby
- first-pass transformer bolt / remove / replace routines

Why that is realistic:

- the front camera handles coarse scene understanding
- the wrist camera handles the final close-range alignment
- the controller uses saved service poses instead of trying to solve everything from scratch
- the ECU geometry and markings are forgiving enough for a classical baseline

The hardest baseline task is still transformers.

Transformers are included in the system, but they will usually need more pose tuning and more careful mechanical setup than fuses, boards, or Steve.

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
3. make Steve reliable once lobby reach is stable
4. leave transformers for after fuses and boards
5. keep OpenCV + scripted control as the baseline
6. add ACT only after the baseline is repeatable

## Recommended Build Order

If you are new, do the project in this order:

1. Build and wire the robot safely.
2. Get official LeRobot + LeKiwi working.
3. Calibrate the follower arm and leader arm.
4. Use this repo’s UI to make a saved profile.
5. Get teleop working.
6. Run the scripted fuse workflow.
7. Run the scripted board workflow.
8. Run the scripted Steve workflow.
9. Tackle transformers only after fuses and boards are dependable.
10. Record data only after teleop and replay are stable.
11. Add ACT only after the scripted version is already useful.

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
- rigid front camera mount
- rigid wrist camera mount
- robot computer:
  - Raspberry Pi 5 4 GB is acceptable for the scripted OpenCV stack
- development laptop
- stable lighting over the ECU work area
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

## How The System Works

At a high level, the system works like this:

1. the robot is manually parked at a known ECU work pose
2. the front camera looks at the full work area
3. the front pipeline finds the target object or target slot
4. the arm moves to a saved coarse approach pose
5. the wrist camera becomes important near the last few centimeters of the task
6. the wrist pipeline refines alignment and checks final placement
7. the finite-state machine decides whether to continue, verify, retry, or back out

The two cameras have different jobs:

- front camera:
  - find the ECU face
  - find the target part
  - find the target slot or hole
  - support coarse approach
- wrist camera:
  - refine near-gripper alignment
  - verify final insertion or placement
  - help with contact-heavy steps such as fuse insertion and transformer interaction

The controller itself is not a black box.
It follows a fixed state-machine style flow:

- detect global target
- approach coarse pose
- switch to wrist precision
- align fine
- grasp or insert
- verify result
- retract
- retry or abort if needed

This is important for students because failures stay visible.
You can usually tell whether the problem is:

- bad detection
- bad service poses
- bad calibration
- bad mechanical alignment
- or genuine contact difficulty

## What Makes It Run On A Pi 5 4 GB

This repo is built to stay lightweight enough for the scripted Ontario baseline.

It does that by:

- using classical vision instead of a heavy detector
- using one always-on front pipeline
- using the wrist camera mainly during close-range precision phases
- using a runtime budget that can reduce wrist usage if compute falls behind
- avoiding heavy live visualization in competition mode

That means the Pi is being used for:

- camera capture
- OpenCV processing
- finite-state-machine control
- LeKiwi client/runtime logic

It is **not** expected to do:

- heavy training
- fancy multimodal models
- big multi-camera learned pipelines

So for this repo’s intended use, the Pi 5 4 GB is acceptable.

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

Important: the UI lets you choose a profile name. In the commands below, add
`--profile <your-profile>` after `skills2026` if you did not keep the default
`default` profile name.

## Step 6: Capture Live Setup

When the robot is powered and the cameras are working:

```bash
skills2026 --profile <your-profile> setup
```

This command helps you save:

- current ports
- camera IDs
- camera calibration clicks
- service poses

For this repo, the important service poses are the ones that support:

- fuse removal
- fuse insertion
- board removal
- board insertion
- Steve pickup
- Steve placement in the lobby
- transformer bolt interaction
- transformer removal
- transformer insertion
- safe retract / stow positions

If these poses are missing or wrong, the system will not feel plug-and-play.
If you enable `start_local_host` in the profile, the helper commands will start
the LeKiwi host for you. If you leave it off, start the host manually before
running `setup`, `teleop`, `record`, `replay`, `pickup_validation`, or
`competition`.

If the robot is not powered yet, you can still save the basic profile:

```bash
skills2026 --profile <your-profile> setup --skip-live
```

## Step 7: Check Readiness

Run:

```bash
skills2026 --profile <your-profile> doctor
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

If `doctor` is failing, do **not** try to fix the problem by jumping straight to training.
Training does not solve:

- wrong ports
- wrong motor IDs
- moved cameras
- bad calibration
- missing service poses

## Step 8: Teleoperate First

Before trying autonomous behavior, make sure teleop works:

```bash
skills2026 --profile <your-profile> teleop
```

What success looks like:

- leader arm moves the follower arm correctly
- the robot does not jerk or drift unexpectedly
- front and wrist cameras make sense
- base stop behavior is safe

If teleop is not solid, do not start data collection yet.

## Step 8.5: Run Pickup Validation

Before trusting the robot on real pickup tasks, run the built-in pickup stress test:

```bash
skills2026 --profile <your-profile> pickup_validation --suite core --trials 3
```

What this does:

- repeats the pickup routine several times
- checks the exact failure modes that usually break RGB pickup:
  - one easy object
  - two similar nearby objects
  - wrist-camera motion during final approach
  - partial occlusion near grasp
  - slightly changed lighting
- writes a JSON report into `data/logs/`

Use the ECU-focused suite once the generic pickup path is stable:

```bash
skills2026 --profile <your-profile> pickup_validation --suite ecu --trials 3
```

That suite checks:

- `pick_fuse`
- `pick_board`
- `pick_transformer`
- `pick_steve`

If it refuses to start, that usually means one of the saved pickup poses is internally inconsistent, especially a gripper position saved in the profile that does not match what the primitive actually commands. Re-capture the pose and try again.

It can also refuse to start if the live camera framing check fails. That means the camera is alive, but the current view is probably too dark, too blurry, too blank, or pointed at the wrong part of the field. Fix the mount, lighting, or camera ID before trying again.

How to interpret the result:

- if every trial passes, your pickup path is in a good place
- if any trial fails, do **not** jump straight to training
- first fix:
  - service poses
  - camera mount stability
  - exposure / white balance
  - scene reset consistency

This is the fastest way to catch “it worked once but not reliably” problems before they waste a practice session.

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
skills2026 --profile <your-profile> competition ecu --primitive insert_fuse --target-color green
```

Repeat with the other colors once one color works.

Important: the first useful fuse version does **not** need training.
If the system can:

- detect the fuse color
- reach the right hover pose
- line up the bare-wood insertion end
- insert consistently enough for practice

then you already have a valid baseline.

## Step 10: Do Boards Next

Boards are the next best Ontario Skills target because the visual cues are large:

- malfunctioning board: big `X`
- functioning board: green strip

Use:

```bash
skills2026 --profile <your-profile> competition ecu --primitive insert_board --target-slot center
```

You will probably need to adjust your service poses and calibration a few times before board insertion feels clean.

Again, this step does **not** require training first.
Most board issues will come from:

- slot alignment
- coarse pose placement
- gripper approach angle
- camera framing

## Step 11: Add Steve Once Lobby Reach Is Stable

Steve is a good follow-up arm task after boards because:

- he is a visible, structured object
- there is no tight insertion step
- it builds confidence before transformer work

Run:

```bash
skills2026 --profile <your-profile> competition ecu --primitive deliver_steve_to_lobby --target-slot lobby
```

Steve is also meant to work without training in the baseline system.
If Steve is failing, first check:

- pickup pose
- lobby place pose
- gripper opening
- whether the robot is parked consistently enough for the arm reach

## Step 12: Only Then Tackle Transformers

Transformers are harder because:

- they are larger
- contact matters more
- barrel-bolt motion is more jam-prone

This repo includes transformer primitives, but the intended beginner path is:

1. fuses
2. boards
3. Steve
4. only then transformers

Start with the focused ECU + Steve mission:

```bash
skills2026 --profile <your-profile> competition mission --mission-name ecu_steve_priority
```

That preset runs:

- fuse repair
- board repair
- transformer repair
- Steve to lobby
- breaker flip

The goal is that this mission is still useful **before** any learning is added.
Transformer steps are the most likely part to need extra tuning, but the repo is still designed so you try them scripted first. The transformer flow now includes an explicit bolt re-lock step after the replacement.

Other presets:

```bash
skills2026 --profile <your-profile> competition mission --mission-name ecu_only
skills2026 --profile <your-profile> competition mission --mission-name full_match
```

The `full_match` and `rescue_support` presets also include a final-position confirmation step before the breaker flip, because the breaker ends the run.

## Step 13: Record Data Only After Baseline Works

You can stop here if the scripted system already does well enough for your goals.

That is the intended design:

- baseline first
- training second
- only if needed

Once teleop and scripted control are stable, collect demonstrations:

```bash
skills2026 --profile <your-profile> record insert_fuse
```

You can also record the other important Ontario primitives:

```bash
skills2026 --profile <your-profile> record remove_board
skills2026 --profile <your-profile> record insert_board
skills2026 --profile <your-profile> record deliver_steve_to_lobby
skills2026 --profile <your-profile> record unlock_transformer_bolts
skills2026 --profile <your-profile> record lock_transformer_bolts
skills2026 --profile <your-profile> record replace_transformer
```

Then replay them:

```bash
skills2026 --profile <your-profile> replay <your-profile>_insert_fuse 0
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
- transformer contact refinement if your scripted path is close but still inconsistent

Do **not** use ACT as the first thing you build.
Do **not** assume ACT is required for this repo to be useful.

The right question is:

- is the baseline already scoring enough?

If the answer is yes, stay with the baseline.
If the answer is no, and the remaining failures are mostly final contact/alignment failures, then ACT becomes worth trying.

In other words:

- training is optional
- calibration is mandatory
- service poses are mandatory
- replay stability is mandatory before training

### What ACT Means In This Repo

ACT in this repo is an **optional backend**, not the main system.

The default remains:

- `opencv_fsm`

ACT is only for the case where you already have:

- a trained ACT checkpoint
- a recorded local dataset for the same primitive
- matching camera names and action layout

Run it like this:

```bash
skills2026 --profile <your-profile> competition ecu \
  --backend act \
  --primitive insert_fuse \
  --policy-path your_user/your_act_checkpoint \
  --dataset-name <your-profile>_insert_fuse
```

Or with a local checkpoint path:

```bash
skills2026 --profile <your-profile> competition ecu \
  --backend act \
  --primitive replace_transformer \
  --policy-path /absolute/path/to/pretrained_model \
  --dataset-name <your-profile>_replace_transformer
```

The ACT backend uses:

- your trained checkpoint for action prediction
- your recorded LeRobot dataset metadata for feature names and normalization stats
- the same LeKiwi runtime and safety wrapper used by the scripted system

So ACT is not a separate robot stack.
It is just an optional learned policy path inside the same LeKiwi system.

### What ACT Still Does Not Replace

Even with ACT, you still need:

- correct LeKiwi setup
- correct ports
- correct calibration
- rigid cameras
- good service poses
- a stable ECU work position

ACT does **not** fix:

- bad wiring
- wrong motor IDs
- moved cameras
- bad calibration
- bad datasets

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

## Daily Use Checklist

Once the one-time setup is finished, the normal student workflow should look like this:

1. power the robot computer
2. connect the front camera
3. connect the wrist camera
4. connect the leader arm
5. make sure the robot is in the same physical setup you calibrated for
6. run `skills2026 --profile <your-profile> doctor`
7. run `skills2026 --profile <your-profile> teleop` for a quick motion sanity check
8. park the robot at the ECU service pose
9. run the focused ECU mission or a single ECU primitive

That is the real plug-and-play goal of this repo:

- not zero setup forever
- but repeatable daily bring-up with the saved profile

## Common Commands

```bash
skills2026 --profile <your-profile> ui
skills2026 --profile <your-profile> setup --skip-live
skills2026 --profile <your-profile> setup
skills2026 --profile <your-profile> doctor
skills2026 --profile <your-profile> teleop
skills2026 --profile <your-profile> pickup_validation --suite core --trials 3
skills2026 --profile <your-profile> pickup_validation --suite ecu --trials 3
skills2026 --profile <your-profile> record insert_fuse
skills2026 --profile <your-profile> record unlock_transformer_bolts
skills2026 --profile <your-profile> record lock_transformer_bolts
skills2026 --profile <your-profile> replay <your-profile>_insert_fuse 0
skills2026 --profile <your-profile> competition ecu --primitive insert_fuse --target-color green
skills2026 --profile <your-profile> competition ecu --primitive insert_board --target-slot center
skills2026 --profile <your-profile> competition ecu --primitive deliver_steve_to_lobby --target-slot lobby
skills2026 --profile <your-profile> competition ecu --primitive replace_transformer --target-slot left
skills2026 --profile <your-profile> competition mission --mission-name ecu_steve_priority
skills2026 --profile <your-profile> competition ecu --backend act --primitive insert_fuse --policy-path your_user/your_act_checkpoint --dataset-name <your-profile>_insert_fuse
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
