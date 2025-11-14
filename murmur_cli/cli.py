"""Murmur CLI tool for controlling the daemon."""

import argparse
import json
import sys
from pathlib import Path

from murmur_daemon.ipc_server import IPCClient


def format_response(response: dict) -> str:
    """Format response for display.

    Args:
        response: Response from daemon

    Returns:
        Formatted string
    """
    if response["status"] == "success":
        if "message" in response:
            output = f"✓ {response['message']}"
        else:
            output = "✓ Success"

        if "result" in response and response["result"]:
            result = response["result"]
            if isinstance(result, dict):
                output += "\n\n" + json.dumps(result, indent=2)
            elif isinstance(result, str):
                output += f"\n\n{result}"

        return output

    else:  # error
        message = response.get("message", "Unknown error")
        return f"✗ Error: {message}"


def cmd_start(args, client: IPCClient) -> int:
    """Handle 'start' command."""
    response = client.send_command("start")

    print(format_response(response))

    return 0 if response["status"] == "success" else 1


def cmd_stop(args, client: IPCClient) -> int:
    """Handle 'stop' command."""
    response = client.send_command("stop")

    print(format_response(response))

    # If successful, show transcription result
    if response["status"] == "success" and "result" in response:
        result = response["result"]

        if "transcription" in result and result["transcription"]:
            print(f"\nTranscription ({len(result['transcription'])} characters):")
            print("-" * 60)
            print(result["transcription"])
            print("-" * 60)

        if "insertion_method" in result:
            method = result["insertion_method"]
            print(f"\n📋 Text insertion method: {method}")

            if method == "clipboard":
                print("   Please press Ctrl+V to paste")

    return 0 if response["status"] == "success" else 1


def cmd_status(args, client: IPCClient) -> int:
    """Handle 'status' command."""
    response = client.send_command("status")

    if response["status"] == "success" and "result" in response:
        result = response["result"]

        # Format status output
        print("Murmur Status")
        print("=" * 60)

        daemon_running = result.get("daemon_running", True)  # If we got response, daemon is running
        print(f"Daemon:           {'🟢 Running' if daemon_running else '🔴 Stopped'}")

        if "recording" in result:
            recording = result["recording"]
            print(f"Recording:        {'🔴 Active' if recording else '⚪ Idle'}")

        if "model_loaded" in result:
            model_loaded = result["model_loaded"]
            model_name = result.get("model_name", "unknown")
            print(f"Model:            {'✓' if model_loaded else '✗'} {model_name}")

        if "uptime" in result:
            uptime = result["uptime"]
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            print(f"Uptime:           {hours}h {minutes}m")

        if "sessions_count" in result:
            print(f"Sessions:         {result['sessions_count']}")

        if "text_injection_available" in result:
            injection = result["text_injection_available"]
            print(f"\nText Insertion Methods:")
            print(f"  Direct:         {'✓' if injection.get('direct') else '✗'}")
            print(f"  Auto-paste:     {'✓' if injection.get('auto_paste') else '✗'}")
            print(f"  Clipboard:      {'✓' if injection.get('clipboard') else '✗'}")

        # Show all other fields in JSON format
        excluded_fields = {
            "daemon_running",
            "recording",
            "model_loaded",
            "model_name",
            "uptime",
            "sessions_count",
            "text_injection_available",
        }
        other_fields = {k: v for k, v in result.items() if k not in excluded_fields}

        if other_fields and args.verbose:
            print(f"\nDetailed Info:")
            print(json.dumps(other_fields, indent=2))

    else:
        print(format_response(response))

    return 0 if response["status"] == "success" else 1


def cmd_shutdown(args, client: IPCClient) -> int:
    """Handle 'shutdown' command."""
    if not args.force:
        response = input("Are you sure you want to shut down the daemon? (y/N): ")
        if response.lower() != "y":
            print("Cancelled")
            return 0

    response = client.send_command("shutdown")
    print(format_response(response))

    return 0 if response["status"] == "success" else 1


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        prog="whi",
        description="Murmur - Real-time voice-to-text for Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  whi start              Start recording
  whi stop               Stop recording and insert text
  whi status             Check daemon status
  whi status -v          Check detailed status

Hyprland Keybindings:
  Add to ~/.config/hypr/hyprland.conf:
    bind = SUPER SHIFT, Space, exec, whi start
    bind = SUPER SHIFT, R, exec, whi stop

For more information, see: https://github.com/yourusername/Whisper
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
        default=None,
    )

    parser.add_argument(
        "--socket",
        type=str,
        help="Path to daemon socket",
        default="/tmp/murmur-daemon.sock",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Start command
    parser_start = subparsers.add_parser("start", help="Start recording")

    # Stop command
    parser_stop = subparsers.add_parser("stop", help="Stop recording and insert text")

    # Status command
    parser_status = subparsers.add_parser("status", help="Check daemon status")
    parser_status.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed status"
    )

    # Shutdown command (hidden, for advanced users)
    parser_shutdown = subparsers.add_parser("shutdown", help="Shut down daemon")
    parser_shutdown.add_argument("-f", "--force", action="store_true", help="Force shutdown")

    args = parser.parse_args()

    # Show help if no command
    if not args.command:
        parser.print_help()
        return 0

    # Create IPC client
    client = IPCClient(socket_path=args.socket)

    # Execute command
    commands = {
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "shutdown": cmd_shutdown,
    }

    if args.command in commands:
        try:
            return commands[args.command](args, client)
        except KeyboardInterrupt:
            print("\nCancelled")
            return 130
        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            return 1
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
