"""Turn "barrel button held + pen drag" into mouse-wheel scrolling.

Why this exists
---------------
The Wacom One (CTL-472) pen has no wheel and no touch ring, and the Wayland
input stack has no equivalent of the Windows Ink "pen drag pans the page"
behaviour. libinput only reports the tablet wheel axis for tools that libwacom
describes as having a wheel, and niri's ``input { tablet { } }`` block offers
only map-to-output / calibration options. Nothing in the configuration can
turn pen motion into scrolling, so the translation has to live in software --
which is exactly what Windows Ink does internally.

This daemon sits below the compositor and mirrors the pen onto a virtual one:

    pen evdev --(grab)--> virtual pen  (identical, plus a scroll wheel axis)

Holding the barrel button and dragging past a small deadzone starts a scroll
gesture: pen motion becomes wheel ticks and tip contact is withheld, so the
drag cannot also select text or paint. A quick barrel tap (never leaving the
deadzone) is replayed as a real barrel click. Pressing the barrel button while
already drawing is passed straight through, so normal drawing is untouched.

Emitting the wheel on the *tablet tool* rather than on a synthetic mouse
matters: niri forwards ``zwp_tablet_tool_v2.wheel`` to the surface the pen is
over, so the scroll lands on the window under the pen tip. Clients that ignore
the tablet wheel (Chromium/Electron) will not scroll; Firefox/GTK do.

The gesture state machine (PenScrollEngine) imports no evdev API, so it can be
unit tested without a tablet or /dev/uinput.
"""

from __future__ import annotations

import glob
import os
import signal
import stat
import sys
import time

# Input event codes (mirrors include/uapi/linux/input-event-codes.h).
EV_SYN = 0x00
EV_KEY = 0x01
EV_REL = 0x02
EV_ABS = 0x03
EV_FF = 0x15

ABS_X = 0x00
ABS_Y = 0x01
ABS_PRESSURE = 0x18
REL_HWHEEL = 0x06
REL_WHEEL = 0x08
# High-resolution wheel axes. Values are "v120" units: 120 == one logical
# notch. Sending these lets a client scroll by fractions of a notch, which the
# integer-only low-resolution axes cannot express.
REL_WHEEL_HI_RES = 0x0B
REL_HWHEEL_HI_RES = 0x0C
BTN_TOOL_PEN = 0x140
BTN_LEFT = 0x110
BTN_TOUCH = 0x14A
BTN_STYLUS = 0x14B
BTN_STYLUS2 = 0x14C

KEY_PRESS = 1
KEY_RELEASE = 0

MODE_IDLE = "idle"
MODE_ARMED = "armed"
MODE_SCROLLING = "scrolling"

# One logical wheel notch in v120 units; the kernel/libinput convention.
V120_PER_NOTCH = 120

# Physical pen travel per wheel notch when the axis resolution is known.
# 4 mm keeps a full-height stroke on the CTL-472 (about 95 mm of active area)
# near a screenful of text, which felt closer to a touchpad than 6 mm did.
DEFAULT_MM_PER_TICK = 4.0
# Physical travel that must be crossed before a gesture scrolls anything.
# Small enough to feel immediate, large enough that a deliberate barrel tap
# with the tip down is not mistaken for a drag.
DEFAULT_MM_DEADZONE = 1.5
# Notches a full-height stroke should cover when resolution is unavailable.
FALLBACK_NOTCHES_PER_AXIS = 40.0
DEFAULT_DEADZONE_PIXELS = 20.0


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        print(
            f"pen-scroll: ignoring non-numeric {name}={raw!r}",
            file=sys.stderr,
        )
        return default
    return value if value > 0 else default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class PenScrollEngine:
    """State machine turning pen events into forwarded + wheel events.

    ``handle`` consumes one ``(type, code, value)`` triple and returns
    ``(forward, scroll)``:

      forward -- events to re-emit on the virtual pen, in order
      scroll  -- ``(REL_*.code, ticks)`` pairs for the virtual pen

    Neither list carries SYN; the caller emits one SYN per source report.
    """

    def __init__(
        self,
        units_per_tick: float = 1.0,
        deadzone_pixels: float = DEFAULT_DEADZONE_PIXELS,
        barrel_code: int = BTN_STYLUS,
        natural: bool = True,
        horizontal: bool = False,
    ) -> None:
        self.units_per_tick = units_per_tick
        self.deadzone_pixels = deadzone_pixels
        self.barrel_code = barrel_code
        self.natural = natural
        self.horizontal = horizontal

        self.position = {ABS_X: 0, ABS_Y: 0}
        self.tip_down = False
        self.mode = MODE_IDLE
        # Barrel pressed while the tip was already down: forward everything so
        # a mid-stroke barrel press never disturbs drawing.
        self.passthrough = False
        # After a gesture ends with the tip still down, keep swallowing tip
        # contact until the pen is lifted so no stray dot is painted.
        self.suppress_until_lift = False
        # A tip-down that we swallowed must not later be followed by an
        # unmatched tip-up on the virtual device.
        self.withheld_tip = False
        # True once this barrel press has actually scrolled. A press that
        # scrolled must never also be replayed as a click on release.
        self.gestured = False
        self.anchor = (0, 0)
        self.last = (0, 0)
        self.accumulated = 0.0

    # -- helpers ---------------------------------------------------------
    @property
    def _axis_code(self) -> int:
        """Hi-res wheel axis matching the configured direction."""
        return REL_HWHEEL_HI_RES if self.horizontal else REL_WHEEL_HI_RES

    def _distance_from_anchor(self) -> float:
        dx = self.position[ABS_X] - self.anchor[0]
        dy = self.position[ABS_Y] - self.anchor[1]
        return (dx * dx + dy * dy) ** 0.5

    def _begin_scroll(self):
        """Engage the gesture and prime libinput's wheel accumulator.

        libinput ignores wheel deltas until ``ACC_V120_THRESHOLD`` (60) has
        accumulated, then switches to forwarding each delta as it arrives;
        below that a small delta would simply be discarded. So the gesture
        opens with one full notch, which both satisfies the threshold and
        gives the immediate response the user asked for. Every later step then
        arrives smoothly.

        Returns the initial ``(axis_code, v120)`` pair, or an empty list.
        """
        self.mode = MODE_SCROLLING
        self.gestured = True
        self.accumulated = 0.0
        self.last = (self.position[ABS_X], self.position[ABS_Y])
        self.primed = True

        travelled = self.position[ABS_X if self.horizontal else ABS_Y]
        origin = self.anchor[0 if self.horizontal else 1]
        offset = travelled - origin
        # Match _v120_for's sign convention (natural = dragging down scrolls
        # towards earlier content).
        sign = 1.0 if self.natural else -1.0
        v120 = V120_PER_NOTCH if sign * offset > 0 else -V120_PER_NOTCH
        return [(self._axis_code, v120)]

    def _should_begin_scroll(self) -> bool:
        """Whether an armed barrel press has now become a scroll gesture.

        The tip must be *on* the tablet: hovering the pen across the surface
        must keep moving the cursor and never scroll anything. The deadzone is
        measured from the point where the tip landed, so hovering far away
        before touching down cannot trigger an instant scroll.
        """
        if self.mode != MODE_ARMED:
            return False
        if not self.tip_down:
            return False
        return self._distance_from_anchor() > self.deadzone_pixels

    def _reset(self) -> None:
        # Leaving interception with the tip still down would forward a tip-up
        # that never had a matching tip-down; swallow the rest of the contact.
        if self.tip_down or self.withheld_tip:
            self.suppress_until_lift = True
        self.mode = MODE_IDLE
        self.passthrough = False
        self.gestured = False
        self.accumulated = 0.0

    def _end_stroke_scroll(self) -> None:
        """The tip lifted mid-gesture. Stop scrolling, stay ready for another.

        The barrel button is usually still held here, so going back to ARMED
        lets the user drag again without releasing it. Re-anchoring on the next
        touch-down keeps the deadzone honest; ``gestured`` stays set so
        releasing the barrel afterwards does not fire a stray click.
        """
        self.mode = MODE_ARMED
        self.withheld_tip = False
        self.accumulated = 0.0
        self.anchor = (self.position[ABS_X], self.position[ABS_Y])
        self.last = (self.position[ABS_X], self.position[ABS_Y])

    def _v120_for(self, delta: float) -> int:
        """Convert pen travel into v120 wheel units.

        Unlike a wheel notch, v120 is fine-grained (120 per notch), so the
        caller can drive smooth per-pixel scrolling instead of jumping a whole
        notch at a time. Fractional units are accumulated so no travel is lost.
        """
        if self.units_per_tick <= 0:
            return 0
        # Natural scrolling: dragging the pen down pulls the content down,
        # which is a scroll towards earlier content (positive wheel value).
        sign = 1.0 if self.natural else -1.0
        self.accumulated += sign * delta * (V120_PER_NOTCH / self.units_per_tick)
        whole = int(self.accumulated)
        if whole != 0:
            self.accumulated -= whole
        return whole

    def _intercepting_tip(self) -> bool:
        return self.mode != MODE_IDLE or self.suppress_until_lift

    # -- public API ------------------------------------------------------
    def handle(self, etype: int, code: int, value: int):
        forward = []
        scroll = []

        if etype == EV_ABS and code in (ABS_X, ABS_Y):
            self.position[code] = value
            forward.append((etype, code, value))

            if self.mode == MODE_SCROLLING:
                dx = self.position[ABS_X] - self.last[0]
                dy = self.position[ABS_Y] - self.last[1]
                self.last = (self.position[ABS_X], self.position[ABS_Y])
                v120 = self._v120_for(dx if self.horizontal else dy)
                if v120 != 0:
                    scroll.append((self._axis_code, v120))
            elif self._should_begin_scroll():
                scroll.extend(self._begin_scroll())
            return forward, scroll

        # Pressure and BTN_TOUCH are what libinput turns into tip contact;
        # withholding them is what stops a gesture from selecting or painting.
        if code == ABS_PRESSURE or (etype == EV_KEY and code == BTN_TOUCH):
            was_down = self.tip_down
            if code == ABS_PRESSURE:
                self.tip_down = value > 0
            elif value == KEY_PRESS:
                self.tip_down = True
            else:
                self.tip_down = False

            if self.mode == MODE_ARMED:
                if self.tip_down and not was_down:
                    # Tip has just touched down. Re-anchor here: hovering the
                    # pen far from the press point must not count towards the
                    # deadzone, otherwise the first touch would scroll
                    # instantly.
                    self.anchor = (self.position[ABS_X], self.position[ABS_Y])
                    self.withheld_tip = True
                elif not self.tip_down and self.withheld_tip:
                    # Lifted without ever scrolling: forget this contact and
                    # replay it as a plain barrel click on release.
                    self.withheld_tip = False
                return forward, scroll

            if self._intercepting_tip():
                if self.tip_down:
                    self.withheld_tip = True
                elif self.mode == MODE_SCROLLING:
                    # Lifting the tip ends the gesture even while the barrel
                    # button is still held. Otherwise the hand's natural drift
                    # back after the stroke keeps scrolling, which is felt as
                    # the view jerking in the opposite direction.
                    self._end_stroke_scroll()
                elif self.mode == MODE_IDLE:
                    # The pen finally lifted: forget the contact silently.
                    self.suppress_until_lift = False
                    self.withheld_tip = False
                return forward, scroll
            forward.append((etype, code, value))
            return forward, scroll

        if etype == EV_KEY and code == self.barrel_code:
            if value == KEY_PRESS:
                self.anchor = (self.position[ABS_X], self.position[ABS_Y])
                if self.tip_down:
                    # Barrel pressed mid-stroke: never intercept drawing.
                    self.passthrough = True
                    forward.append((etype, code, value))
                else:
                    # Withhold the press: it is either a click (replayed on
                    # release) or the start of a scroll gesture (dropped).
                    self.mode = MODE_ARMED
            elif value == KEY_RELEASE:
                if self.mode == MODE_SCROLLING:
                    self._reset()
                elif self.passthrough:
                    self.passthrough = False
                    forward.append((etype, code, value))
                elif self.mode == MODE_ARMED:
                    if self.gestured:
                        # This press already scrolled (possibly several
                        # strokes); releasing it must not also click.
                        self._reset()
                    else:
                        # A tap that never left the deadzone: replay a real
                        # click. If the tip was pressed during the gesture its
                        # contact was withheld too, so re-emit it in order.
                        if self.withheld_tip:
                            forward.append((EV_KEY, BTN_TOUCH, KEY_PRESS))
                            forward.append((EV_KEY, BTN_TOUCH, KEY_RELEASE))
                            self.withheld_tip = False
                        forward.append((EV_KEY, self.barrel_code, KEY_PRESS))
                        forward.append((EV_KEY, self.barrel_code, KEY_RELEASE))
                        self.mode = MODE_IDLE
                else:
                    forward.append((etype, code, value))
            return forward, scroll

        forward.append((etype, code, value))
        return forward, scroll

    def pen_left_proximity(self) -> None:
        """Forget transient state when the pen leaves the tablet."""
        self.tip_down = False
        self.mode = MODE_IDLE
        self.passthrough = False
        self.suppress_until_lift = False
        self.withheld_tip = False
        self.accumulated = 0.0


# ---------------------------------------------------------------------------
# evdev plumbing -- imported lazily so the engine stays testable off-target.
# ---------------------------------------------------------------------------

PEN_NAME_HINTS = ("wacom", "pen", "tablet", "stylus", "huion", "xp-pen")

# Identifies our own virtual device so a second instance can never grab it.
VIRTUAL_PHYS = "pen-scroll-virtual"


def mirror_capabilities(capabilities, wheel_codes=(REL_WHEEL, REL_HWHEEL)):
    """Return the uinput capability map for the virtual pen.

    Clones what the real pen reports and adds the scroll wheel, which is what
    niri needs in order to forward ``zwp_tablet_tool_v2.wheel`` to the surface
    under the pen tip. SYN is always filtered (uinput synthesises it).
    """
    events = {
        etype: list(codes)
        for etype, codes in capabilities.items()
        if etype not in (EV_SYN, EV_FF)
    }
    existing = {
        code for code in events.get(EV_REL, []) if isinstance(code, int)
    }
    existing.update(wheel_codes)
    events[EV_REL] = sorted(existing)
    return events


def find_pen_device():
    """Return the first stylus-like absolute device that is not our mirror."""
    import evdev
    from evdev import ecodes

    candidates = []
    for path in sorted(evdev.list_devices()):
        try:
            device = evdev.InputDevice(path)
        except OSError:
            continue

        if device.phys == VIRTUAL_PHYS:
            device.close()
            continue

        capabilities = device.capabilities()
        keys = capabilities.get(ecodes.EV_KEY, [])
        abs_codes = {
            entry[0] if isinstance(entry, tuple) else entry
            for entry in capabilities.get(ecodes.EV_ABS, [])
        }
        has_pen = ecodes.BTN_TOOL_PEN in keys or ecodes.BTN_STYLUS in keys
        has_xy = ecodes.ABS_X in abs_codes and ecodes.ABS_Y in abs_codes

        if has_pen and has_xy:
            named = any(hint in device.name.lower() for hint in PEN_NAME_HINTS)
            candidates.append((0 if named else 1, path, device))
        else:
            device.close()

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2]


def wait_for_pen_device(timeout_seconds: float = 30.0):
    """Block until a pen appears; return None once the timeout elapses."""
    if timeout_seconds > 0:
        deadline = time.monotonic() + timeout_seconds
    else:
        deadline = None
    while True:
        device = find_pen_device()
        if device is not None:
            return device
        if deadline is not None and time.monotonic() >= deadline:
            return None
        time.sleep(1.0)


# /dev/uinput is 0660 root:uinput on NixOS (hardware.uinput udev rule).
UINPUT_DEVICE = "/dev/uinput"


def uinput_status():
    """Describe why the virtual-device node is unusable, or None if it is fine.

    Distinguishes the three cases that need different fixes, so the log does
    not send the reader down the wrong path:

      missing    -- node absent; udev did not create it (module/static_node)
      permission -- node exists but the process lacks write access (groups)
      notchar    -- node exists but is not a character device
    """
    try:
        mode = os.stat(UINPUT_DEVICE).st_mode
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unreadable"
    if not stat.S_ISCHR(mode):
        return "notchar"
    if not os.access(UINPUT_DEVICE, os.W_OK):
        return "permission"
    return None


def current_groups() -> str:
    """Human-readable supplementary groups of this process.

    Printed on permission failures because the usual cause is that the
    process is running with a stale group set: a systemd **user** manager
    (user@UID.service) is started at first login and may keep running with
    the groups it had then, so even logging out and back in does not always
    refresh the groups a user service sees.
    """
    names = []
    for gid in os.getgroups():
        try:
            import grp

            names.append(grp.getgrgid(gid).gr_name)
        except (KeyError, ImportError):  # pragma: no cover - NSS lookup miss
            names.append(str(gid))
    return ", ".join(names) if names else "(none)"


def uinput_hint(status: str) -> str:
    """Actionable next step for a given uinput_status()."""
    if status == "missing":
        return (
            f"  {UINPUT_DEVICE} does not exist. Check that the uinput module "
            "is loaded (lsmod | grep uinput) and that hardware.uinput.enable "
            "is active, then reboot or re-trigger udev."
        )
    if status == "permission":
        return (
            f"  {UINPUT_DEVICE} is 0660 root:uinput but not writable. "
            f"This process's groups: {current_groups()}. "
            "If 'uinput' is absent, the session/user-manager group set is "
            "stale: log out and back in, and if it persists restart the user "
            "manager (systemctl --user daemon-reexec does not refresh groups; "
            "loginctl terminate-user $USER then log in again)."
        )
    return f"  {UINPUT_DEVICE} is not a usable character device."


def retryable_errors():
    """Exception types worth waiting out rather than crashing on.

    ``evdev.uinput.UInputError`` derives from ``Exception``, **not**
    ``OSError``, so catching only OSError misses exactly the permission and
    missing-node failures this daemon has to survive.
    """
    try:
        from evdev.uinput import UInputError
    except ImportError:  # pragma: no cover - evdev is a hard runtime dep
        return (OSError,)
    return (OSError, UInputError)


def build_mirror(device, name: str):
    """Virtual pen cloning the real capabilities, plus a scroll wheel axis.

    niri only accepts REL_WHEEL on a tablet tool, and forwards it to the
    surface the pen is over, so this is how a scroll reaches the right window
    without moving the mouse pointer.
    """
    from evdev import UInput

    info = device.info
    return UInput(
        mirror_capabilities(device.capabilities(absinfo=True)),
        name=name,
        phys=VIRTUAL_PHYS,
        vendor=info.vendor,
        product=info.product,
        version=info.version,
        bustype=info.bustype,
        input_props=device.input_props(),
    )


def units_per_tick_for(device, requested: float) -> float:
    """Wheel ticks per axis unit, from the pen's physical resolution."""
    from evdev import ecodes

    if requested > 0:
        return requested
    try:
        resolution = device.absinfo(ecodes.ABS_X).resolution
    except OSError:
        resolution = 0
    if resolution and resolution > 0:
        return DEFAULT_MM_PER_TICK * resolution
    try:
        info = device.absinfo(ecodes.ABS_X)
        span = abs(info.max - info.min)
    except OSError:
        span = 0
    if span:
        return span / FALLBACK_NOTCHES_PER_AXIS
    return 1.0


def deadzone_units_for(device, requested: float) -> float:
    """Gesture deadzone in axis units.

    Defaults to DEFAULT_MM_DEADZONE millimetres so the threshold has the same
    physical feel on any tablet. It only has to absorb hand tremor during a
    barrel tap; the deadzone is not what makes scrolling feel slow, since it
    is an order of magnitude smaller than one wheel notch.
    """
    from evdev import ecodes

    if requested > 0:
        return requested
    try:
        resolution = device.absinfo(ecodes.ABS_X).resolution
    except OSError:
        resolution = 0
    if resolution and resolution > 0:
        return DEFAULT_MM_DEADZONE * resolution

    try:
        info = device.absinfo(ecodes.ABS_X)
        span = abs(info.max - info.min)
    except OSError:
        span = 0
    if span:
        # Assume a plausible 100 mm of active travel for an unknown tablet.
        return span * (DEFAULT_MM_DEADZONE / 100.0)
    return DEFAULT_DEADZONE_PIXELS


# ---------------------------------------------------------------------------
# niri IPC: the absolute pointer needs to know which output to target.
#
# A virtual tablet can follow the focused output (input.tablet.map-to-*), but a
# virtual *pointer* cannot: niri's libinput devices never report an output, so
# an absolute pointer falls back to the union of all outputs. On a two-monitor
# setup that stretches the tablet over both screens, so the wheel would land on
# whichever window happens to be under that stretched position. Asking niri for
# the focused output and mapping the pen into that output's geometry keeps the
# scroll on the intended screen.
# ---------------------------------------------------------------------------

NIRI_SOCKET_ENV = "NIRI_SOCKET"


def niri_socket_path():
    """Locate niri's IPC socket, or None.

    Prefers $NIRI_SOCKET. As a system service the daemon does not inherit the
    user's session environment, and the socket name embeds niri's PID, so it
    is discovered under the runtime directory instead of being hardcoded.
    """
    path = os.environ.get(NIRI_SOCKET_ENV)
    if path and os.path.exists(path):
        return path

    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    try:
        candidates = sorted(glob.glob(os.path.join(runtime, "niri.*.sock")))
    except OSError:  # pragma: no cover - glob rarely raises
        return None
    return candidates[0] if candidates else None


def niri_request(method: str, timeout: float = 1.0):
    """Send one niri IPC request and return the decoded JSON reply.

    ``method`` is the request name, e.g. "FocusedOutput". Returns None when
    niri is unreachable so callers can fall back to the tablet-only path.
    """
    import json
    import socket

    path = niri_socket_path()
    if not path:
        return None
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(path)
            # niri reads one newline-terminated JSON value per request; without
            # the newline it waits forever for the rest of the request.
            sock.sendall(json.dumps(method).encode() + b"\n")
            chunks = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                try:
                    return json.loads(b"".join(chunks))
                except ValueError:
                    continue
    except (OSError, ValueError):
        return None
    return None


def niri_reply_payload(reply, method: str | None = None):
    """Unwrap niri's {"Ok": {Method: value}} envelope.

    niri replies with ``{"Ok": {"<Method>": <value>}}`` on success and
    ``{"Err": ...}`` on failure. Returns the inner value, or None when the
    reply is an error or an unexpected shape.
    """
    if not isinstance(reply, dict):
        return None
    if "Err" in reply:
        return None
    inner = reply.get("Ok")
    if not isinstance(inner, dict):
        return None
    if method is not None:
        return inner.get(method)
    # Exactly one key in practice; return its value.
    if len(inner) == 1:
        return next(iter(inner.values()))
    return inner


def focused_output_logical():
    """Logical geometry plus name of the focused output, or None.

    The inner value looks like {"name": ..., "logical": {"x","y","width",
    "height","scale","transform"}}.
    """
    payload = niri_reply_payload(niri_request("FocusedOutput"), "FocusedOutput")
    if not isinstance(payload, dict):
        return None
    logical = payload.get("logical")
    if not isinstance(logical, dict):
        return None
    try:
        return {
            "name": payload.get("name") or "?",
            "x": float(logical["x"]),
            "y": float(logical["y"]),
            "width": float(logical["width"]),
            "height": float(logical["height"]),
            "transform": logical.get("transform") or "Normal",
        }
    except (KeyError, TypeError, ValueError):
        return None


def map_pen_to_output(position, pen_range, output, tablet_size=None):
    """Map a raw pen position into an output's logical coordinate space.

    Mirrors niri's own tablet mapping, so the pointer lands exactly where niri
    draws the pen cursor. Getting this wrong is visible: niri preserves the
    aspect ratio by *cropping* (cover), not by letterboxing, so a fit-style
    mapping puts the pointer tens of logical pixels away from the pen tip.

    niri's algorithm (compute_tablet_position):
        normalise by the tablet range
        project into the output's (possibly rotated) coordinate space
        divide by the output size
        scale by ratio = tablet_aspect / output_aspect, on x when > 1 else on y
        multiply back by the output size, then clamp

    ``position`` is a raw (x, y) in tablet units; ``pen_range`` is
    ``{"x": (min, max), "y": (min, max)}``; ``tablet_size`` is the pen's
    (width, height) in millimetres for the aspect ratio. Returns logical
    (x, y) in niri's global space, or None when the inputs are unusable.
    """
    if not output:
        return None
    x_min, x_max = pen_range.get("x", (0.0, 1.0))
    y_min, y_max = pen_range.get("y", (0.0, 1.0))
    width = x_max - x_min
    height = y_max - y_min
    if width <= 0 or height <= 0:
        return None

    out_w = output["width"]
    out_h = output["height"]
    if out_w <= 0 or out_h <= 0:
        return None

    px, py = position
    nx = (px - x_min) / width
    ny = (py - y_min) / height

    transform = output.get("transform", "Normal")
    rotated = transform in ("90", "270", "Flipped90", "Flipped270")
    # Space the pen is mapped into once the output transform is undone
    # (niri: transform.invert().transform_size(target.size)).
    space_w, space_h = (out_h, out_w) if rotated else (out_w, out_h)

    tx, ty = nx * space_w, ny * space_h
    if transform == "90":
        tx, ty = space_h - ty, tx
    elif transform == "270":
        tx, ty = ty, space_w - tx
    elif transform in ("180", "Flipped180"):
        tx, ty = space_w - tx, space_h - ty
    elif transform == "Flipped":
        tx, ty = space_w - tx, ty

    fx, fy = tx / out_w, ty / out_h

    # niri keeps the aspect ratio by cropping to fill the output.
    if tablet_size and tablet_size[0] > 0 and tablet_size[1] > 0:
        ratio = (tablet_size[0] / tablet_size[1]) / (space_w / space_h)
        if ratio > 1.0:
            fx *= ratio
        else:
            fy /= ratio

    lx, ly = fx * out_w, fy * out_h

    scale = output.get("scale") or 1.0
    edge = 1.0 / scale if scale > 0 else 1.0
    lx = min(max(lx, 0.0), out_w - edge)
    ly = min(max(ly, 0.0), out_h - edge)
    return (lx + output["x"], ly + output["y"])


def bounding_rect_from_outputs(reply):
    """Union of all outputs' logical rectangles, or None.

    ``reply`` is niri's "Outputs" response (possibly still enveloped):
    {name: {..., "logical": {...}}}.
    """
    payload = niri_reply_payload(reply, "Outputs")
    if payload is None:
        payload = niri_reply_payload(reply)
    if payload is None:
        payload = reply
    if not isinstance(payload, dict):
        return None
    xs = []
    ys = []
    for output in payload.values():
        logical = (output or {}).get("logical")
        if not isinstance(logical, dict):
            continue
        try:
            x = float(logical["x"])
            y = float(logical["y"])
            w = float(logical["width"])
            h = float(logical["height"])
        except (KeyError, TypeError, ValueError):
            continue
        xs.append((x, x + w))
        ys.append((y, y + h))
    if not xs or not ys:
        return None
    return {
        "x": min(a for a, _ in xs),
        "y": min(a for a, _ in ys),
        "width": max(b for _, b in xs) - min(a for a, _ in xs),
        "height": max(b for _, b in ys) - min(a for a, _ in ys),
    }


def absolute_for_logical(logical, bounding, pen_range):
    """Inverse of niri's absolute-pointer mapping.

    niri maps an absolute pointer with no known output over the union of all
    outputs, scaling each axis linearly:
        logical = bound_loc + (raw - raw_min) * bound_size / raw_range
    This inverts that so the pointer lands on ``logical``.
    """
    if not logical or not bounding:
        return None
    x_min, x_max = pen_range.get("x", (0.0, 1.0))
    y_min, y_max = pen_range.get("y", (0.0, 1.0))
    x_range = x_max - x_min
    y_range = y_max - y_min
    if x_range <= 0 or y_range <= 0:
        return None
    if bounding["width"] <= 0 or bounding["height"] <= 0:
        return None

    lx, ly = logical
    raw_x = (lx - bounding["x"]) * x_range / bounding["width"] + x_min
    raw_y = (ly - bounding["y"]) * y_range / bounding["height"] + y_min
    # Keep the raw values inside the device's declared range.
    raw_x = min(max(raw_x, x_min), x_max)
    raw_y = min(max(raw_y, y_min), y_max)
    return (int(round(raw_x)), int(round(raw_y)))


def pen_axis_range(device):
    """The pen's ABS_X/ABS_Y (min, max) pairs."""
    try:
        x = device.absinfo(ABS_X)
        y = device.absinfo(ABS_Y)
    except OSError:
        return None
    return {"x": (float(x.min), float(x.max)), "y": (float(y.min), float(y.max))}


def pen_physical_size(device):
    """The pen's active area in millimetres, or None.

    niri uses the same figure (from the kernel's axis resolution) for the
    aspect-ratio correction, so it has to match to place the pointer exactly.
    """
    try:
        x = device.absinfo(ABS_X)
        y = device.absinfo(ABS_Y)
    except OSError:
        return None
    if not x.resolution or not y.resolution:
        return None
    width = (x.max - x.min) / x.resolution
    height = (y.max - y.min) / y.resolution
    if width <= 0 or height <= 0:
        return None
    return (width, height)


def make_absolute_pointer(device, name: str):
    """Virtual absolute pointer used to deliver hi-res wheel events.

    Absolute so the wheel lands under the pen rather than wherever the real
    mouse was left, and declaring the hi-res wheel axes so libinput preserves
    the fractional deltas the engine produces.
    """
    from evdev import UInput, ecodes

    def axis(code):
        info = device.absinfo(code)
        return (
            code,
            (info.value, info.min, info.max, info.fuzz, info.flat, info.resolution),
        )

    info = device.info
    return UInput(
        {
            ecodes.EV_ABS: [axis(ecodes.ABS_X), axis(ecodes.ABS_Y)],
            ecodes.EV_KEY: [ecodes.BTN_LEFT],
            ecodes.EV_REL: [
                ecodes.REL_WHEEL,
                ecodes.REL_HWHEEL,
                ecodes.REL_WHEEL_HI_RES,
                ecodes.REL_HWHEEL_HI_RES,
            ],
        },
        name=name,
        phys=VIRTUAL_PHYS,
        vendor=info.vendor,
        product=info.product,
        version=info.version,
        bustype=info.bustype,
        input_props=[ecodes.INPUT_PROP_POINTER],
    )


class _Stop(Exception):
    pass


def _install_signal_handlers() -> None:
    def handler(_signum, _frame):
        raise _Stop()

    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, handler)


class WheelSink:
    """Delivers wheel events via a hi-res absolute pointer when possible.

    The pointer channel is required for smooth scrolling: the tablet tool's
    wheel axis is integer-only, so it can only ever jump a whole notch. If the
    pointer cannot be positioned (no niri IPC, so we cannot tell which output
    to target), fall back to the tablet channel with whole notches, which is
    exactly the previous behaviour.
    """

    def __init__(self, pen_device, pointer, pen_range, out=sys.stdout, tablet_size=None):
        self.pointer = pointer
        self.pen_range = pen_range
        self.tablet_size = tablet_size
        self.out = out
        self.bounding = None
        self.output = None
        self._refresh_outputs()
        # Fractional remainder carried when falling back to whole notches.
        self._fallback_remainder = 0

    def _refresh_outputs(self):
        self.output = focused_output_logical()
        self.bounding = bounding_rect_from_outputs(niri_request("Outputs"))

    @property
    def smooth(self) -> bool:
        return self.pointer is not None and self.bounding is not None

    def position_at(self, raw_position) -> None:
        """Place the pointer under the pen before scrolling.

        Called once when the gesture engages. Doing it once (rather than every
        frame) keeps the cursor from visibly chasing the pen while scrolling.
        """
        if not self.smooth:
            return
        self._refresh_outputs()
        logical = map_pen_to_output(
            raw_position, self.pen_range, self.output, self.tablet_size
        )
        absolute = absolute_for_logical(logical, self.bounding, self.pen_range)
        if absolute is None:
            return
        self.pointer.write(EV_ABS, ABS_X, absolute[0])
        self.pointer.write(EV_ABS, ABS_Y, absolute[1])
        self.pointer.syn()

    def emit(self, mirror, code: int, v120: int) -> None:
        """Send one wheel delta on the best available channel."""
        if self.smooth:
            self.pointer.write(EV_REL, code, v120)
            self.pointer.syn()
            return
        # Fallback: the tablet axis only understands whole notches.
        if code not in (REL_WHEEL_HI_RES, REL_HWHEEL_HI_RES):
            mirror.write(EV_REL, code, v120)
            return
        self._fallback_remainder += v120
        notches = int(self._fallback_remainder / V120_PER_NOTCH)
        if notches == 0:
            return
        self._fallback_remainder -= notches * V120_PER_NOTCH
        axis = REL_WHEEL if code == REL_WHEEL_HI_RES else REL_HWHEEL
        mirror.write(EV_REL, axis, notches)

    def syn(self, mirror) -> None:
        if not self.smooth:
            mirror.syn()

    def describe(self) -> str:
        if self.smooth:
            name = (self.output or {}).get("name", "?")
            return f"hi-res pointer, target output {name}"
        return "tablet wheel (no niri IPC; whole notches)"


def run(device, engine: PenScrollEngine, out=sys.stdout) -> int:
    """Grab the pen and pump events until it disappears or we are stopped."""
    from evdev import ecodes

    engine.units_per_tick = units_per_tick_for(device, engine.units_per_tick)
    engine.deadzone_pixels = deadzone_units_for(device, engine.deadzone_pixels)
    # Build the virtual devices *before* grabbing: if this raises (typically
    # /dev/uinput permissions), the physical pen was never grabbed, so the
    # failure cannot strand the user without a working stylus.
    mirror = build_mirror(device, f"{device.name} (pen-scroll)")

    pen_range = pen_axis_range(device)
    pointer = None
    if pen_range is not None:
        try:
            pointer = make_absolute_pointer(device, "pen-scroll wheel")
        except Exception as error:  # noqa: BLE001 - fall back, never crash
            print(
                f"pen-scroll: hi-res pointer unavailable ({error}); "
                "falling back to whole notches",
                file=sys.stderr,
                flush=True,
            )
    sink = WheelSink(
        device, pointer, pen_range, out=out, tablet_size=pen_physical_size(device)
    )

    print(
        f"pen-scroll: grabbing {device.path} ({device.name}); "
        f"{engine.units_per_tick:.1f} units per wheel notch, "
        f"{engine.deadzone_pixels:.0f} units deadzone; {sink.describe()}",
        file=out,
        flush=True,
    )
    device.grab()
    pending_scroll = []
    # Tracks whether the pointer has been aimed for the current gesture, so it
    # is placed once per stroke instead of on every frame (which would make the
    # cursor visibly chase the pen).
    aimed = False
    try:
        for event in device.read_loop():
            forward, scroll = engine.handle(
                event.type, event.code, event.value
            )
            in_gesture = engine.mode == MODE_SCROLLING
            if in_gesture and not aimed:
                # First delta of a gesture: aim the pointer at the pen, then
                # prime libinput's accumulator with the leading whole notch.
                aimed = True
                sink.position_at(
                    (engine.position[ABS_X], engine.position[ABS_Y])
                )
            elif not in_gesture:
                # Gesture ended (tip lifted, or barrel released): the next
                # stroke aims the pointer again.
                aimed = False
            pending_scroll.extend(scroll)

            for etype, code, value in forward:
                mirror.write(etype, code, value)

            if event.type == ecodes.EV_SYN:
                for code, value in pending_scroll:
                    sink.emit(mirror, code, value)
                pending_scroll.clear()
                sink.syn(mirror)
                mirror.syn()

            if event.type == ecodes.EV_KEY and (
                event.code == ecodes.BTN_TOOL_PEN
            ):
                if event.value == KEY_RELEASE:
                    engine.pen_left_proximity()
    except _Stop:
        return 0
    finally:
        try:
            device.ungrab()
        except OSError:
            pass
        if pointer is not None:
            pointer.close()
        mirror.close()
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0

    engine = PenScrollEngine(
        # 0 means "derive from the device resolution at grab time".
        units_per_tick=_env_float("PEN_SCROLL_UNITS_PER_TICK", 0.0),
        deadzone_pixels=_env_float("PEN_SCROLL_DEADZONE_PIXELS", 0.0),
        natural=_env_bool("PEN_SCROLL_NATURAL", True),
        horizontal=_env_bool("PEN_SCROLL_HORIZONTAL", False),
        barrel_code=(
            BTN_STYLUS2
            if os.environ.get("PEN_SCROLL_BARREL", "lower") == "upper"
            else BTN_STYLUS
        ),
    )

    _install_signal_handlers()

    # Timestamp of the last uinput diagnostic; the retry loop uses it to avoid
    # repeating the same hint every 10 seconds while the problem persists.
    last_uinput_log = 0.0

    while True:
        problem = uinput_status()
        if problem is not None:
            # Log the first occurrence and then only occasionally: this loop
            # retries every 10s, so repeating the full hint would flood the
            # journal while the condition persists.
            now = time.monotonic()
            if now - last_uinput_log >= 60.0:
                last_uinput_log = now
                print(
                    f"pen-scroll: cannot use {UINPUT_DEVICE} "
                    f"({problem}); retrying every 10s.",
                    file=sys.stderr,
                    flush=True,
                )
                print(uinput_hint(problem), file=sys.stderr, flush=True)
            time.sleep(10.0)
            continue

        device = wait_for_pen_device(timeout_seconds=30.0)
        if device is None:
            print(
                "pen-scroll: no pen tablet found yet; retrying every 5s",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(5.0)
            continue
        try:
            return run(device, engine)
        except _Stop:
            return 0
        except retryable_errors() as error:
            # Includes evdev's UInputError (permissions / node missing), which
            # does not derive from OSError.
            print(
                f"pen-scroll: {error}; retrying in 5s",
                file=sys.stderr,
                flush=True,
            )
            try:
                device.close()
            except OSError:
                pass
            time.sleep(5.0)


if __name__ == "__main__":
    raise SystemExit(main())
