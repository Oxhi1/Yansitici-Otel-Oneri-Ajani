import argparse
import os
import sys


def run_cli():
    from app.agents.request_handler import run_full_recommendation_flow
    run_full_recommendation_flow()


def run_ui(host: str, port: int):
    # streamlit'i subprocess ile çağırıyoruz
    import subprocess
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        "app/ui/streamlit_app.py",
        "--server.address", host,
        "--server.port", str(port),
    ]
    subprocess.run(cmd, check=False)


def main():
    parser = argparse.ArgumentParser(description="Otel & Restoran Öneri Sistemi")
    parser.add_argument("--mode", choices=["cli", "ui"], default="ui")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()

    if args.mode == "cli":
        run_cli()
    else:
        run_ui(args.host, args.port)


if __name__ == "__main__":
    main()

