"""Command line interface for Riden RK6006/RK6006H supplies."""

from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, TextIO

DEFAULT_CH340_VID_PID = "VID:PID=1A86:7523"

if TYPE_CHECKING:
    from RK6006_module import RK6006


@dataclass(frozen=True)
class Sample:
    index: int
    elapsed_s: float
    voltage_v: float
    current_a: float
    power_w: float


def find_default_port() -> str:
    """Return the first CH340 serial port, matching the board's USB adapter."""
    try:
        import serial.tools.list_ports
    except ImportError as exc:
        raise RuntimeError(
            "pyserial is required for automatic port detection. "
            "Install it or pass --port explicitly."
        ) from exc

    for port in serial.tools.list_ports.comports():
        if DEFAULT_CH340_VID_PID in port.hwid:
            return port.device

    raise RuntimeError(
        "No CH340 serial adapter was found. Connect the supply or pass --port."
    )


def connect(args: argparse.Namespace) -> RK6006:
    try:
        from RK6006_module import RK6006
    except ImportError as exc:
        raise RuntimeError(
            "minimalmodbus and pyserial are required to connect to the supply."
        ) from exc

    port = args.port or find_default_port()
    return RK6006(
        port=port,
        baudrate=args.baudrate,
        address=args.address,
        modbus_timeout=args.timeout,
    )


def output_state_text(value: int) -> str:
    return "ON" if value else "OFF"


def protection_text(value: int) -> str:
    return {0: "OK", 1: "OVP", 2: "OCP"}.get(value, f"UNKNOWN({value})")


def mode_text(value: int) -> str:
    return {0: "CV", 1: "CC"}.get(value, f"UNKNOWN({value})")


def print_info(device: RK6006, out: TextIO = sys.stdout) -> None:
    print(f"Model            : {device.model}", file=out)
    print(f"Serial number    : {device.sn:08}", file=out)
    print(f"Firmware         : V{device.fw}", file=out)
    print(f"Port             : {device.port}", file=out)
    print(f"Modbus address   : {device.address}", file=out)
    print(f"Max set voltage  : {device.max_set_voltage:.2f} V", file=out)
    print(f"Max set current  : {device.max_set_current:.3f} A", file=out)


def print_status(device: RK6006, out: TextIO = sys.stdout) -> None:
    input_voltage = device.get_input_voltage()
    set_voltage = device.get_set_voltage()
    set_current = device.get_set_current()
    output_voltage = device.get_output_voltage()
    output_current = device.get_output_current()
    output_power = device.get_output_power()
    capacity = device.get_capacity_ah()
    energy = device.get_energy_wh()
    enable_state = device.get_enable_state()
    protection = device.get_protection_status()
    output_mode = device.get_current_output_mode()
    internal_temp = device.get_temp_internal()
    external_temp = device.get_temp_external()

    print(f"Output           : {output_state_text(enable_state)}", file=out)
    print(f"Mode             : {mode_text(output_mode)}", file=out)
    print(f"Output voltage   : {output_voltage:.2f} V", file=out)
    print(f"Output current   : {output_current:.3f} A", file=out)
    print(f"Output power     : {output_power:.2f} W", file=out)
    print(f"Set voltage      : {set_voltage:.2f} V", file=out)
    print(f"Set current      : {set_current:.3f} A", file=out)
    print(f"Capacity         : {capacity:.3f} Ah", file=out)
    print(f"Energy           : {energy:.3f} Wh", file=out)
    print(f"Protection       : {protection_text(protection)}", file=out)
    print(f"Input voltage    : {input_voltage:.2f} V", file=out)
    print(f"Internal temp    : {internal_temp} \N{DEGREE SIGN}C", file=out)
    if external_temp < -40:
        print("External temp    : unavailable", file=out)
    else:
        print(f"External temp    : {external_temp} \N{DEGREE SIGN}C", file=out)


def apply_setpoints(device: RK6006, args: argparse.Namespace) -> bool:
    changed = False
    if args.set_voltage is not None:
        device.set_voltage(args.set_voltage)
        changed = True
    if args.set_current is not None:
        device.set_current(args.set_current)
        changed = True
    return changed


def print_setpoints(device: RK6006, out: TextIO = sys.stdout) -> None:
    print(f"Set voltage      : {device.get_set_voltage():.2f} V", file=out)
    print(f"Set current      : {device.get_set_current():.3f} A", file=out)


def iter_samples(
    device: RK6006,
    count: int | None,
    duration: float | None,
    interval: float,
) -> Iterable[Sample]:
    start = time.monotonic()
    next_sample = start
    index = 0

    while True:
        now = time.monotonic()
        if now < next_sample:
            time.sleep(next_sample - now)

        elapsed = time.monotonic() - start
        yield Sample(
            index=index,
            elapsed_s=elapsed,
            voltage_v=device.get_output_voltage(),
            current_a=device.get_output_current(),
            power_w=device.get_output_power(),
        )

        index += 1
        if count is not None and index >= count:
            break
        if duration is not None and elapsed >= duration:
            break

        next_sample = start + index * interval


def sample_interval(args: argparse.Namespace) -> float:
    if args.count is not None and args.count < 1:
        raise ValueError("--count must be at least 1")
    if args.duration is not None and args.duration < 0:
        raise ValueError("--duration must be non-negative")
    if args.interval <= 0:
        raise ValueError("--interval must be greater than 0")
    if args.duration is None or args.count is None or args.count <= 1:
        return args.interval
    return args.duration / (args.count - 1)


def write_samples(
    samples: Iterable[Sample],
    csv_output: bool,
    out: TextIO = sys.stdout,
) -> None:
    if csv_output:
        writer = csv.writer(out)
        writer.writerow(["index", "elapsed_s", "voltage_v", "current_a", "power_w"])
        for sample in samples:
            writer.writerow(
                [
                    sample.index,
                    f"{sample.elapsed_s:.3f}",
                    f"{sample.voltage_v:.3f}",
                    f"{sample.current_a:.4f}",
                    f"{sample.power_w:.3f}",
                ]
            )
        return

    print("index elapsed_s voltage_v current_a power_w", file=out)
    for sample in samples:
        print(
            f"{sample.index:5d} "
            f"{sample.elapsed_s:9.3f} "
            f"{sample.voltage_v:9.3f} "
            f"{sample.current_a:9.4f} "
            f"{sample.power_w:7.3f}",
            file=out,
        )


def add_connection_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-p",
        "--port",
        help="Serial port, for example COM3. Defaults to the first CH340 adapter.",
    )
    parser.add_argument(
        "-b",
        "--baudrate",
        type=int,
        default=115200,
        help="Serial baud rate. Default: 115200.",
    )
    parser.add_argument(
        "-a",
        "--address",
        type=int,
        default=1,
        help="Modbus slave address. Default: 1.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=0.5,
        help="Modbus response timeout in seconds. Default: 0.5.",
    )


def add_setpoint_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--set_voltage",
        "--set-voltage",
        dest="set_voltage",
        type=float,
        help="Set output voltage in volts before running the command.",
    )
    parser.add_argument(
        "--set_current",
        "--set-current",
        dest="set_current",
        type=float,
        help="Set output current limit in amperes before running the command.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rk6006",
        description="Control a Riden RK6006/RK6006H laboratory power supply.",
    )
    add_connection_options(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("info", help="Show device identity and limits.")
    subparsers.add_parser("status", help="Show output, setpoints, and measurements.")

    on_parser = subparsers.add_parser("on", help="Enable the output.")
    add_setpoint_options(on_parser)

    off_parser = subparsers.add_parser("off", help="Disable the output.")
    add_setpoint_options(off_parser)

    set_parser = subparsers.add_parser(
        "set",
        help="Set output voltage and/or current without changing output state.",
    )
    add_setpoint_options(set_parser)

    sample_parser = subparsers.add_parser(
        "sample",
        help="Sample output voltage/current over time.",
    )
    sample_parser.add_argument(
        "-c",
        "--count",
        type=int,
        help="Number of samples to capture.",
    )
    sample_parser.add_argument(
        "-d",
        "--duration",
        type=float,
        help="Sampling window in seconds.",
    )
    sample_parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between samples. Ignored when both --count and --duration are set. Default: 1.",
    )
    sample_parser.add_argument(
        "--csv",
        action="store_true",
        help="Print samples as CSV.",
    )

    return parser


def run(args: argparse.Namespace) -> int:
    device = connect(args)

    if args.command == "info":
        print_info(device)
    elif args.command == "status":
        print_status(device)
    elif args.command == "on":
        changed = apply_setpoints(device, args)
        device.set_enable_state(True)
        if changed:
            print_setpoints(device)
        print(f"Output: {output_state_text(device.get_enable_state())}")
    elif args.command == "off":
        changed = apply_setpoints(device, args)
        device.set_enable_state(False)
        if changed:
            print_setpoints(device)
        print(f"Output: {output_state_text(device.get_enable_state())}")
    elif args.command == "set":
        if not apply_setpoints(device, args):
            raise ValueError("set requires --set_voltage and/or --set_current")
        print_setpoints(device)
    elif args.command == "sample":
        interval = sample_interval(args)
        count = args.count if args.count is not None else None
        duration = args.duration if args.duration is not None else None
        if count is None and duration is None:
            count = 1
        write_samples(iter_samples(device, count, duration, interval), args.csv)
    else:
        raise ValueError(f"Unhandled command: {args.command}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return run(args)
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
