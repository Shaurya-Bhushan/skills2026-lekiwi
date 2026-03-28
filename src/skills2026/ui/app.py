from __future__ import annotations

from dataclasses import asdict

from skills2026.ui.service import (
    SetupFormData,
    apply_detected_defaults,
    build_next_steps,
    build_profile_summary,
    discover_hardware_snapshot,
    ensure_profile_name,
    form_values_from_profile,
    load_or_default_profile,
    profile_name_choices,
    run_doctor_for_form,
    save_form_data,
)


CSS = """
:root {
  --sand: #f5efe6;
  --paper: #fffaf3;
  --ink: #1f2933;
  --muted: #637381;
  --olive: #5f7a61;
  --rust: #c96b3b;
  --line: #e7dccb;
}
.gradio-container {
  background:
    radial-gradient(circle at top left, rgba(201, 107, 59, 0.10), transparent 28%),
    radial-gradient(circle at top right, rgba(95, 122, 97, 0.12), transparent 24%),
    linear-gradient(180deg, var(--sand), #efe6d9);
}
#hero {
  background: linear-gradient(135deg, rgba(255,250,243,0.95), rgba(247,239,228,0.92));
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 22px 24px 10px 24px;
  box-shadow: 0 18px 50px rgba(70, 57, 44, 0.08);
}
.setup-card {
  border: 1px solid var(--line);
  border-radius: 20px;
  background: rgba(255, 250, 243, 0.9);
}
"""


def _current_form(*values) -> SetupFormData:
    return SetupFormData(*values)


def build_setup_app(default_profile: str = "default"):
    try:
        import gradio as gr
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime only
        raise RuntimeError(
            "The setup UI needs Gradio. Install it in your active environment with `python3 -m pip install gradio` "
            "or reinstall this package after updating dependencies."
        ) from exc

    initial_profile = load_or_default_profile(default_profile)
    initial_form = SetupFormData.from_profile(initial_profile)
    camera_rows, port_rows, suggestion_md = discover_hardware_snapshot()

    with gr.Blocks(title="Skills2026 LeKiwi Setup", css=CSS, theme=gr.themes.Soft()) as demo:
        with gr.Column(elem_id="hero"):
            gr.Markdown(
                """
                # Skills2026 LeKiwi Setup
                A beginner-friendly control panel for the two-camera LeKiwi ECU system.

                Use this page to discover your hardware, save a profile, and check whether the robot is ready before you try teleop or competition mode.
                The recommended beginner path is OpenCV + FSM first, then ACT later if insertion still needs help.
                """
            )

        with gr.Row():
            profile_picker = gr.Dropdown(
                choices=profile_name_choices(),
                value=initial_form.profile_name,
                label="Saved profile",
                info="Pick an existing profile or type a new profile name below.",
                allow_custom_value=True,
            )
            refresh_profiles_btn = gr.Button("Refresh Profiles", variant="secondary")
            load_profile_btn = gr.Button("Load Profile", variant="secondary")

        with gr.Row():
            profile_name = gr.Textbox(label="Profile name", value=initial_form.profile_name)
            runtime_mode = gr.Radio(
                choices=["dev_remote", "competition_local"],
                value=initial_form.mode,
                label="Runtime mode",
                info="Use dev_remote while developing on a laptop. Use competition_local on the robot.",
            )
            default_backend = gr.Radio(
                choices=["opencv_fsm"],
                value=initial_form.default_backend,
                label="Default competition backend",
                info="Use the scripted OpenCV + FSM stack first. Add ACT later through training, not as a setup toggle.",
            )

        with gr.Tabs():
            with gr.Tab("1. Hardware"):
                gr.Markdown("### What the system sees right now")
                with gr.Row():
                    cameras_table = gr.Dataframe(
                        headers=["Camera ID", "Camera name"],
                        value=camera_rows,
                        interactive=False,
                        label="Detected cameras",
                        wrap=True,
                    )
                    serial_table = gr.Dataframe(
                        headers=["Port", "Description"],
                        value=port_rows,
                        interactive=False,
                        label="Detected serial ports",
                        wrap=True,
                    )
                hardware_hint = gr.Markdown(f"### Suggested defaults\n{suggestion_md}")
                with gr.Row():
                    refresh_hardware_btn = gr.Button("Refresh Hardware", variant="secondary")
                    use_detected_btn = gr.Button("Use Detected Defaults", variant="primary")

            with gr.Tab("2. Robot and Cameras"):
                with gr.Row():
                    remote_ip = gr.Textbox(label="LeKiwi host IP", value=initial_form.remote_ip)
                    robot_id = gr.Textbox(label="Robot ID", value=initial_form.robot_id)
                    start_local_host = gr.Checkbox(
                        label="Start local host automatically",
                        value=initial_form.start_local_host,
                    )
                with gr.Row():
                    leader_port = gr.Textbox(label="Leader arm port", value=initial_form.leader_port)
                    robot_serial_port = gr.Textbox(label="Robot serial port", value=initial_form.robot_serial_port)

                gr.Markdown("### Front camera")
                with gr.Row():
                    front_camera_id = gr.Textbox(label="Front camera ID", value=initial_form.front_camera_id)
                    front_width = gr.Number(label="Width", value=initial_form.front_width, precision=0)
                    front_height = gr.Number(label="Height", value=initial_form.front_height, precision=0)
                    front_fps = gr.Number(label="FPS", value=initial_form.front_fps, precision=0)
                    front_enabled = gr.Checkbox(label="Enabled", value=initial_form.front_enabled)

                gr.Markdown("### Wrist camera")
                with gr.Row():
                    wrist_camera_id = gr.Textbox(label="Wrist camera ID", value=initial_form.wrist_camera_id)
                    wrist_width = gr.Number(label="Width", value=initial_form.wrist_width, precision=0)
                    wrist_height = gr.Number(label="Height", value=initial_form.wrist_height, precision=0)
                    wrist_fps = gr.Number(label="FPS", value=initial_form.wrist_fps, precision=0)
                    wrist_enabled = gr.Checkbox(label="Enabled", value=initial_form.wrist_enabled)

            with gr.Tab("3. Safety"):
                gr.Markdown("### Competition checklist")
                with gr.Row():
                    kill_switch_ready = gr.Checkbox(label="Kill switch ready", value=initial_form.kill_switch_ready)
                    wiring_diagram_ready = gr.Checkbox(label="Wiring diagram ready", value=initial_form.wiring_diagram_ready)
                    tabletop_stand_ready = gr.Checkbox(label="Tabletop stand ready", value=initial_form.tabletop_stand_ready)
                    local_only_mode_confirmed = gr.Checkbox(
                        label="Local-only video mode confirmed",
                        value=initial_form.local_only_mode_confirmed,
                    )

                gr.Markdown(
                    """
                    ### Learning later
                    Keep the competition stack on OpenCV + FSM first.

                    Only add ACT after:

                    - teleop is reliable
                    - replay is stable
                    - scripted fuse and board tasks are repeatable
                    """
                )
                with gr.Group(visible=False):
                    with gr.Row():
                        smolvla_enabled = gr.Checkbox(label="Enable SmolVLA option", value=initial_form.smolvla_enabled)
                        smolvla_device = gr.Dropdown(
                            choices=["auto", "cpu", "mps", "cuda"],
                            value=initial_form.smolvla_device,
                            label="SmolVLA device",
                        )
                        smolvla_require_finetuned = gr.Checkbox(
                            label="Require fine-tuned checkpoint",
                            value=initial_form.smolvla_require_finetuned,
                        )
                    smolvla_model_id = gr.Textbox(
                        label="SmolVLA model ID or path",
                        value=initial_form.smolvla_model_id,
                    )
                    smolvla_rename_map_json = gr.Code(
                        label="SmolVLA rename map (JSON)",
                        value=initial_form.smolvla_rename_map_json,
                        language="json",
                        lines=6,
                    )

            with gr.Tab("4. Save and Check"):
                status_md = gr.Markdown("### Status\n- No changes saved yet.")
                profile_summary = gr.Markdown(build_profile_summary(initial_profile))
                next_steps = gr.Markdown(build_next_steps(initial_profile))
                with gr.Row():
                    save_btn = gr.Button("Save Profile", variant="primary")
                    doctor_btn = gr.Button("Run Readiness Check", variant="secondary")
                doctor_table = gr.Dataframe(
                    headers=["Status", "Check", "Detail"],
                    value=[],
                    interactive=False,
                    label="Readiness checks",
                    wrap=True,
                )
                doctor_summary = gr.Markdown("### Readiness Result\n- Run the check after saving your profile.")

        form_inputs = [
            profile_name,
            runtime_mode,
            default_backend,
            remote_ip,
            robot_id,
            leader_port,
            robot_serial_port,
            start_local_host,
            front_camera_id,
            front_width,
            front_height,
            front_fps,
            front_enabled,
            wrist_camera_id,
            wrist_width,
            wrist_height,
            wrist_fps,
            wrist_enabled,
            kill_switch_ready,
            wiring_diagram_ready,
            tabletop_stand_ready,
            local_only_mode_confirmed,
            smolvla_enabled,
            smolvla_model_id,
            smolvla_device,
            smolvla_require_finetuned,
            smolvla_rename_map_json,
        ]

        profile_outputs = [
            profile_name,
            runtime_mode,
            default_backend,
            remote_ip,
            robot_id,
            leader_port,
            robot_serial_port,
            start_local_host,
            front_camera_id,
            front_width,
            front_height,
            front_fps,
            front_enabled,
            wrist_camera_id,
            wrist_width,
            wrist_height,
            wrist_fps,
            wrist_enabled,
            kill_switch_ready,
            wiring_diagram_ready,
            tabletop_stand_ready,
            local_only_mode_confirmed,
            smolvla_enabled,
            smolvla_model_id,
            smolvla_device,
            smolvla_require_finetuned,
            smolvla_rename_map_json,
            profile_summary,
            next_steps,
        ]

        def _load_profile(name: str):
            safe_name = ensure_profile_name(name)
            return form_values_from_profile(safe_name)

        def _refresh_profiles():
            names = profile_name_choices()
            return gr.Dropdown(choices=names)

        def _refresh_hardware():
            camera_data, port_data, hint = discover_hardware_snapshot()
            return camera_data, port_data, f"### Suggested defaults\n{hint}"

        def _apply_detected(name: str):
            safe_name = ensure_profile_name(name)
            return apply_detected_defaults(safe_name)

        def _save(*values):
            form = _current_form(*values)
            form.profile_name = ensure_profile_name(form.profile_name)
            try:
                message, summary, steps = save_form_data(form)
            except Exception as exc:
                fallback_profile = load_or_default_profile(form.profile_name)
                return (
                    f"### Status\n- Could not save the profile.\n- Error: `{exc}`",
                    build_profile_summary(fallback_profile),
                    build_next_steps(fallback_profile),
                    gr.Dropdown(choices=profile_name_choices(), value=form.profile_name),
                )
            return (
                f"### Status\n- {message}\n- You can now run the readiness check below.",
                summary,
                steps,
                gr.Dropdown(choices=profile_name_choices(), value=form.profile_name),
            )

        def _doctor(*values):
            form = _current_form(*values)
            form.profile_name = ensure_profile_name(form.profile_name)
            rows, summary = run_doctor_for_form(form)
            return rows, summary

        refresh_profiles_btn.click(_refresh_profiles, outputs=[profile_picker])
        load_profile_btn.click(_load_profile, inputs=profile_picker, outputs=profile_outputs)
        refresh_hardware_btn.click(_refresh_hardware, outputs=[cameras_table, serial_table, hardware_hint])
        use_detected_btn.click(_apply_detected, inputs=profile_name, outputs=profile_outputs)
        save_btn.click(
            _save,
            inputs=form_inputs,
            outputs=[status_md, profile_summary, next_steps, profile_picker],
        )
        doctor_btn.click(_doctor, inputs=form_inputs, outputs=[doctor_table, doctor_summary])

    return demo
