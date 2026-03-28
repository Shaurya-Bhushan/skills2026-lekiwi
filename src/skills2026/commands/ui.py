from __future__ import annotations


def run(args) -> int:
    try:
        from skills2026.ui.app import build_setup_app
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"Could not start the setup UI because `{exc.name}` is missing. "
            "Install the UI dependency with `python3 -m pip install gradio` or reinstall the package."
        ) from exc

    app = build_setup_app(default_profile=args.profile)
    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        inbrowser=not args.no_browser,
        prevent_thread_lock=False,
    )
    return 0
