import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "pen_scroll", Path(__file__).resolve().parents[1] / "pen-scroll.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

EV_KEY = module.EV_KEY
EV_ABS = module.EV_ABS
ABS_X = module.ABS_X
ABS_Y = module.ABS_Y
ABS_PRESSURE = module.ABS_PRESSURE
BTN_TOUCH = module.BTN_TOUCH
BTN_STYLUS = module.BTN_STYLUS
REL_WHEEL = module.REL_WHEEL


def replay(engine, events):
    """Feed events and collect (forwarded, scroll) with the engine output."""
    forwarded = []
    scrolled = []
    for etype, code, value in events:
        forward, scroll = engine.handle(etype, code, value)
        forwarded.extend(forward)
        scrolled.extend(scroll)
    return forwarded, scrolled


def stroke(x, tip=True):
    return [
        (EV_ABS, ABS_PRESSURE, 200 if tip else 0),
        (EV_KEY, BTN_TOUCH, 1 if tip else 0),
        (EV_ABS, ABS_X, x),
    ]


def contact_down():
    """Tip lands on the tablet."""
    return [(EV_ABS, ABS_PRESSURE, 200), (EV_KEY, BTN_TOUCH, 1)]


def contact_up():
    """Tip lifts off the tablet."""
    return [(EV_ABS, ABS_PRESSURE, 0), (EV_KEY, BTN_TOUCH, 0)]


class PenScrollEngineTests(unittest.TestCase):
    def make(self, **kwargs):
        kwargs.setdefault("units_per_tick", 100.0)
        return module.PenScrollEngine(**kwargs)

    def test_plain_drawing_passes_through_untouched(self):
        engine = self.make()
        events = [
            (EV_ABS, ABS_PRESSURE, 0),
            (EV_ABS, ABS_X, 100),
            (EV_ABS, ABS_Y, 100),
            (EV_ABS, ABS_PRESSURE, 250),
            (EV_KEY, BTN_TOUCH, 1),
            (EV_ABS, ABS_X, 300),
            (EV_ABS, ABS_Y, 400),
            (EV_ABS, ABS_PRESSURE, 0),
            (EV_KEY, BTN_TOUCH, 0),
        ]
        forwarded, scrolled = replay(engine, events)
        self.assertEqual(forwarded, events)
        self.assertEqual(scrolled, [])

    def test_barrel_tap_is_replayed_as_a_click(self):
        engine = self.make()
        forwarded, scrolled = replay(
            engine,
            [
                (EV_ABS, ABS_X, 500),
                (EV_ABS, ABS_Y, 500),
                (EV_KEY, BTN_STYLUS, 1),
                (EV_KEY, BTN_STYLUS, 0),
            ],
        )
        self.assertIn((EV_KEY, BTN_STYLUS, 1), forwarded)
        self.assertIn((EV_KEY, BTN_STYLUS, 0), forwarded)
        self.assertEqual(scrolled, [])

    def test_hovering_while_barrel_held_does_not_scroll(self):
        """The reported bug: hovering the pen must never scroll.

        A gesture requires the tip to be on the tablet; moving the pen
        through the air only moves the cursor.
        """
        engine = self.make(deadzone_pixels=20.0)
        _, scrolled = replay(
            engine,
            [
                (EV_ABS, ABS_X, 1000),
                (EV_ABS, ABS_Y, 1000),
                (EV_KEY, BTN_STYLUS, 1),
                # Large hover movements, tip never touches down.
                (EV_ABS, ABS_Y, 2000),
                (EV_ABS, ABS_Y, 3000),
                (EV_ABS, ABS_X, 2000),
                (EV_KEY, BTN_STYLUS, 0),
            ],
        )
        self.assertEqual(scrolled, [])

    def test_touch_down_after_hovering_reanchors_the_deadzone(self):
        """Hovering far from the press point must not count towards the deadzone."""
        engine = self.make(deadzone_pixels=20.0)
        forwarded, scrolled = replay(
            engine,
            [
                (EV_ABS, ABS_X, 0),
                (EV_ABS, ABS_Y, 0),
                (EV_KEY, BTN_STYLUS, 1),
                # Hover a long way; this must not arm the gesture.
                (EV_ABS, ABS_Y, 5000),
                *contact_down(),
                # The very first touch re-anchors at (0,5000), so a small
                # drag stays inside the deadzone.
                (EV_ABS, ABS_Y, 5010),
                (EV_KEY, BTN_STYLUS, 0),
                *contact_up(),
            ],
        )
        self.assertEqual(scrolled, [])
        self.assertNotIn((EV_ABS, ABS_PRESSURE, 200), forwarded)

    def test_barrel_hold_touch_and_drag_scrolls_without_drawing(self):
        engine = self.make()
        forwarded, scrolled = replay(
            engine,
            [
                (EV_ABS, ABS_X, 1000),
                (EV_ABS, ABS_Y, 1000),
                (EV_KEY, BTN_STYLUS, 1),
                *contact_down(),
                # Crossing the deadzone engages the gesture and emits the
                # first notch straight away (see test_first_notch_is_immediate).
                (EV_ABS, ABS_Y, 1500),
                # Later motion converts at 100 units per notch.
                (EV_ABS, ABS_Y, 2000),
                (EV_KEY, BTN_STYLUS, 0),
                *contact_up(),
            ],
        )
        # One notch on engage, then 500 units / 100 = 5 while scrolling.
        ticks = sum(value for _, value in scrolled)
        self.assertEqual(ticks, 6)
        self.assertNotIn((EV_KEY, BTN_TOUCH, 1), forwarded)
        self.assertNotIn((EV_ABS, ABS_PRESSURE, 200), forwarded)

    def test_first_notch_is_immediate(self):
        """Engaging must scroll at once, not after a whole extra notch.

        Reported as "I have to move a long way before it starts scrolling".
        The deadzone itself was only 0.2 mm; the delay came from having to
        fill a full 4 mm notch before the first wheel event.
        """
        engine = self.make(units_per_tick=400.0, deadzone_pixels=20.0)
        replay(
            engine,
            [
                (EV_ABS, ABS_X, 10000),
                (EV_ABS, ABS_Y, 10000),
                (EV_KEY, BTN_STYLUS, 1),
                *contact_down(),
            ],
        )

        # A hair past the deadzone must already produce a wheel event.
        _, scrolled = replay(engine, [(EV_ABS, ABS_Y, 10000 - 25)])
        self.assertNotEqual(scrolled, [])
        self.assertEqual(abs(sum(v for _, v in scrolled)), 1)

    def test_onset_does_not_change_the_ongoing_rate(self):
        """Engaging must not make the same drag scroll materially further."""
        def ticks_over(distance):
            engine = self.make(units_per_tick=400.0, deadzone_pixels=20.0)
            replay(
                engine,
                [
                    (EV_ABS, ABS_X, 10000),
                    (EV_ABS, ABS_Y, 10000),
                    (EV_KEY, BTN_STYLUS, 1),
                    *contact_down(),
                ],
            )
            _, scrolled = replay(
                engine,
                [
                    (EV_ABS, ABS_Y, 10000 - step)
                    for step in range(10, distance + 1, 10)
                ],
            )
            return abs(sum(v for _, v in scrolled))

        # 40 mm at 4 mm per notch, plus the single engage notch.
        ticks = ticks_over(4000)
        self.assertIn(ticks, (10, 11))

    def test_movement_inside_deadzone_does_not_scroll(self):
        engine = self.make(deadzone_pixels=50.0)
        _, scrolled = replay(
            engine,
            [
                (EV_ABS, ABS_X, 1000),
                (EV_ABS, ABS_Y, 1000),
                (EV_KEY, BTN_STYLUS, 1),
                *contact_down(),
                (EV_ABS, ABS_Y, 1010),
                (EV_ABS, ABS_Y, 1040),
                (EV_KEY, BTN_STYLUS, 0),
                *contact_up(),
            ],
        )
        self.assertEqual(scrolled, [])

    def test_tip_contact_during_gesture_is_withheld(self):
        engine = self.make(deadzone_pixels=10.0)
        forwarded, _ = replay(
            engine,
            [
                (EV_ABS, ABS_X, 0),
                (EV_ABS, ABS_Y, 0),
                (EV_KEY, BTN_STYLUS, 1),
                *contact_down(),
                # Cross the deadzone to start scrolling.
                (EV_ABS, ABS_Y, 200),
                # Pressure changes while still scrolling stay withheld.
                (EV_ABS, ABS_PRESSURE, 300),
                (EV_ABS, ABS_Y, 400),
                (EV_KEY, BTN_STYLUS, 0),
                *contact_up(),
            ],
        )
        self.assertNotIn((EV_ABS, ABS_PRESSURE, 300), forwarded)
        self.assertNotIn((EV_KEY, BTN_TOUCH, 1), forwarded)

    def test_barrel_pressed_mid_stroke_is_passthrough(self):
        engine = self.make()
        events = [
            (EV_ABS, ABS_PRESSURE, 300),
            (EV_KEY, BTN_TOUCH, 1),
            (EV_KEY, BTN_STYLUS, 1),
            (EV_ABS, ABS_X, 50),
            (EV_ABS, ABS_Y, 900),
            (EV_KEY, BTN_STYLUS, 0),
            (EV_ABS, ABS_PRESSURE, 0),
            (EV_KEY, BTN_TOUCH, 0),
        ]
        forwarded, scrolled = replay(engine, events)
        self.assertEqual(forwarded, events)
        self.assertEqual(scrolled, [])

    def test_normal_drawing_resumes_after_a_gesture(self):
        engine = self.make(deadzone_pixels=10.0)
        replay(
            engine,
            [
                (EV_ABS, ABS_X, 0),
                (EV_ABS, ABS_Y, 0),
                (EV_KEY, BTN_STYLUS, 1),
                *contact_down(),
                (EV_ABS, ABS_Y, 500),
                (EV_KEY, BTN_STYLUS, 0),
                *contact_up(),
            ],
        )

        # The very next stroke must be forwarded normally again.
        events = stroke(700)
        forwarded, scrolled = replay(engine, events)
        self.assertEqual(forwarded, events)
        self.assertEqual(scrolled, [])

    def test_direction_follows_natural_scrolling_setting(self):
        def ticks_for(natural):
            engine = self.make(natural=natural, deadzone_pixels=0.0)
            _, scrolled = replay(
                engine,
                [
                    (EV_ABS, ABS_X, 0),
                    (EV_ABS, ABS_Y, 0),
                    (EV_KEY, BTN_STYLUS, 1),
                    *contact_down(),
                    # First move only enters the gesture.
                    (EV_ABS, ABS_Y, 100),
                    # This one produces the ticks.
                    (EV_ABS, ABS_Y, 400),
                    (EV_KEY, BTN_STYLUS, 0),
                    *contact_up(),
                ],
            )
            return sum(value for _, value in scrolled)

        self.assertGreater(ticks_for(True), 0)
        self.assertLess(ticks_for(False), 0)

    def test_pen_leaving_proximity_clears_state(self):
        engine = self.make(deadzone_pixels=0.0)
        replay(
            engine,
            [
                (EV_ABS, ABS_Y, 0),
                (EV_KEY, BTN_STYLUS, 1),
                *contact_down(),
                (EV_ABS, ABS_Y, 100),
            ],
        )
        engine.pen_left_proximity()
        self.assertEqual(engine.mode, module.MODE_IDLE)
        self.assertFalse(engine.tip_down)

        events = stroke(10)
        forwarded, scrolled = replay(engine, events)
        self.assertEqual(forwarded, events)
        self.assertEqual(scrolled, [])

    def test_lifting_the_tip_end_stops_scrolling(self):
        """The reported jerk: after a stroke, drifting back must not scroll.

        The first version kept SCROLLING after the tip left the tablet while
        the barrel button was still held, so the hand's natural drift back
        scrolled the view the other way.
        """
        engine = self.make(deadzone_pixels=20.0)
        replay(
            engine,
            [
                (EV_ABS, ABS_X, 1000),
                (EV_ABS, ABS_Y, 6000),
                (EV_KEY, BTN_STYLUS, 1),
                *contact_down(),
                (EV_ABS, ABS_Y, 5000),
                (EV_ABS, ABS_Y, 4000),
                *contact_up(),
            ],
        )
        self.assertNotEqual(engine.mode, module.MODE_SCROLLING)

        # Hovering back towards the start must produce no wheel events.
        _, scrolled = replay(
            engine, [(EV_ABS, ABS_Y, 4600), (EV_ABS, ABS_Y, 5200)]
        )
        self.assertEqual(scrolled, [])

    def test_second_stroke_works_without_releasing_the_barrel_button(self):
        engine = self.make(deadzone_pixels=20.0)
        replay(
            engine,
            [
                (EV_ABS, ABS_X, 1000),
                (EV_ABS, ABS_Y, 6000),
                (EV_KEY, BTN_STYLUS, 1),
                *contact_down(),
                (EV_ABS, ABS_Y, 4000),
                *contact_up(),
            ],
        )
        self.assertEqual(engine.mode, module.MODE_ARMED)

        # Touch down again and drag: another stroke should scroll.
        _, scrolled = replay(
            engine,
            [
                *contact_down(),
                (EV_ABS, ABS_Y, 2000),
                (EV_ABS, ABS_Y, 1000),
            ],
        )
        self.assertNotEqual(scrolled, [])

    def test_releasing_after_scrolling_does_not_click(self):
        engine = self.make(deadzone_pixels=20.0)
        forwarded, _ = replay(
            engine,
            [
                (EV_ABS, ABS_X, 1000),
                (EV_ABS, ABS_Y, 6000),
                (EV_KEY, BTN_STYLUS, 1),
                *contact_down(),
                (EV_ABS, ABS_Y, 4000),
                *contact_up(),
                (EV_KEY, BTN_STYLUS, 0),
            ],
        )
        self.assertNotIn((EV_KEY, BTN_STYLUS, 1), forwarded)
        self.assertNotIn((EV_KEY, BTN_STYLUS, 0), forwarded)
        self.assertEqual(engine.mode, module.MODE_IDLE)

    def test_tap_still_clicks_after_the_stroke_fix(self):
        """Regression guard: the click replay must survive the state changes."""
        engine = self.make()
        forwarded, scrolled = replay(
            engine,
            [
                (EV_ABS, ABS_X, 500),
                (EV_KEY, BTN_STYLUS, 1),
                (EV_KEY, BTN_STYLUS, 0),
            ],
        )
        self.assertIn((EV_KEY, BTN_STYLUS, 1), forwarded)
        self.assertIn((EV_KEY, BTN_STYLUS, 0), forwarded)
        self.assertEqual(scrolled, [])


class MirrorCapabilitiesTests(unittest.TestCase):
    def sample(self):
        return {
            module.EV_KEY: [module.BTN_TOOL_PEN, module.BTN_TOUCH, module.BTN_STYLUS],
            module.EV_ABS: [
                (module.ABS_X, (0, 0, 32000, 0, 0, 100)),
                (module.ABS_Y, (0, 0, 20000, 0, 0, 100)),
                (module.ABS_PRESSURE, (0, 0, 2047, 0, 0, 0)),
            ],
            module.EV_SYN: [0, 1],
            module.EV_FF: [],
            0x04: [0],
        }

    def test_adds_both_wheel_axes(self):
        events = module.mirror_capabilities(self.sample())
        self.assertEqual(
            events[module.EV_REL], sorted([module.REL_WHEEL, module.REL_HWHEEL])
        )

    def test_filters_syn_and_ff(self):
        events = module.mirror_capabilities(self.sample())
        self.assertNotIn(module.EV_SYN, events)
        self.assertNotIn(module.EV_FF, events)
        self.assertIn(0x04, events)

    def test_preserves_absolute_axis_details(self):
        events = module.mirror_capabilities(self.sample())
        self.assertEqual(len(events[module.EV_ABS][0][1]), 6)
        self.assertIn(module.BTN_STYLUS, events[module.EV_KEY])

    def test_does_not_mutate_the_source_capabilities(self):
        caps = self.sample()
        module.mirror_capabilities(caps)
        self.assertNotIn(module.EV_REL, caps)

    def test_existing_relative_codes_are_kept(self):
        caps = self.sample()
        caps[module.EV_REL] = [module.REL_WHEEL, 0x0A]
        events = module.mirror_capabilities(caps)
        self.assertIn(0x0A, events[module.EV_REL])
        self.assertEqual(events[module.EV_REL], sorted(set(events[module.EV_REL])))


class ScrollSpeedTests(unittest.TestCase):
    """Lock the default scroll distance so it cannot drift silently.

    4 mm per notch was chosen after testing on the CTL-472: a full-height
    stroke is about 95 mm, so this scrolls roughly a screenful. The user
    asked for a faster feel than the original 6 mm.
    """

    def test_default_is_four_mm_per_notch(self):
        self.assertEqual(module.DEFAULT_MM_PER_TICK, 4.0)

    def test_tick_distance_scales_with_axis_resolution(self):
        # units_per_tick_for imports evdev; skip where it is unavailable.
        try:
            import evdev  # noqa: F401
        except ImportError:
            self.skipTest("evdev not importable in this environment")

        class FakeAbs:
            resolution = 100

        class FakeDevice:
            def absinfo(self, _code):
                return FakeAbs()

        # 100 units/mm * 4 mm = 400 units per notch.
        self.assertEqual(module.units_per_tick_for(FakeDevice(), 0.0), 400.0)

    def test_explicit_override_wins(self):
        try:
            import evdev  # noqa: F401
        except ImportError:
            self.skipTest("evdev not importable in this environment")

        class FakeDevice:
            def absinfo(self, _code):  # pragma: no cover - must not be called
                raise AssertionError("resolution should not be consulted")

        self.assertEqual(module.units_per_tick_for(FakeDevice(), 250.0), 250.0)

    def test_deadzone_is_physical_and_smaller_than_a_notch(self):
        """The deadzone must stay well below one notch.

        It only absorbs tap tremor; a deadzone near a full notch is what made
        the gesture feel like it needed a long drag before starting.
        """
        self.assertLess(module.DEFAULT_MM_DEADZONE, module.DEFAULT_MM_PER_TICK)
        self.assertGreater(module.DEFAULT_MM_DEADZONE, 0.0)

    def test_deadzone_scales_with_resolution(self):
        try:
            import evdev  # noqa: F401
        except ImportError:
            self.skipTest("evdev not importable in this environment")

        class FakeAbs:
            resolution = 100

        class FakeDevice:
            def absinfo(self, _code):
                return FakeAbs()

        # 100 units/mm * 1.5 mm = 150 units.
        self.assertEqual(module.deadzone_units_for(FakeDevice(), 0.0), 150.0)


class RetryableErrorsTests(unittest.TestCase):
    """evdev's UInputError must be caught, not crash the service.

    A real 2026-09-17 failure: /dev/uinput was not writable, UInputError was
    raised, and because it derives from Exception (not OSError) the daemon
    died with a traceback and restart-looped.
    """

    def test_uinput_error_is_retryable(self):
        errors = module.retryable_errors()
        self.assertTrue(any(issubclass(e, Exception) for e in errors))
        try:
            from evdev.uinput import UInputError
        except ImportError:  # pragma: no cover - evdev is a runtime dep
            self.skipTest("evdev not importable in this environment")
        self.assertIn(UInputError, errors)
        # The regression itself: UInputError is NOT an OSError.
        self.assertFalse(issubclass(UInputError, OSError))

    def test_oserror_is_retryable(self):
        self.assertIn(OSError, module.retryable_errors())

    def test_uinput_status_classifies_states(self):
        """The unusable states need different fixes, so they are distinct."""
        status = module.uinput_status()
        self.assertIn(status, {None, "missing", "permission", "notchar", "unreadable"})
        if status is not None:
            self.assertIn(status, {"missing", "permission", "notchar", "unreadable"})

    def test_uinput_status_missing_is_reported_when_absent(self):
        original = module.UINPUT_DEVICE
        try:
            module.UINPUT_DEVICE = "/dev/definitely-not-a-real-device-xyz"
            self.assertEqual(module.uinput_status(), "missing")
            self.assertIn("does not exist", module.uinput_hint("missing"))
        finally:
            module.UINPUT_DEVICE = original

    def test_permission_hint_reports_groups_and_relogin(self):
        hint = module.uinput_hint("permission")
        self.assertIn("groups:", hint)
        self.assertIn("uinput", hint)
        # The whole point: supplementary groups are captured at login.
        self.assertIn("log out", hint)

    def test_current_groups_is_readable(self):
        self.assertIsInstance(module.current_groups(), str)
        self.assertTrue(module.current_groups())

    def test_uinput_device_path_is_absolute(self):
        self.assertTrue(module.UINPUT_DEVICE.startswith("/dev/"))

    def test_check_runs_before_grabbing_the_pen(self):
        """A build_mirror failure must not leave the physical pen grabbed."""
        source = Path(
            Path(__file__).resolve().parents[1] / "pen-scroll.py"
        ).read_text()
        build_at = source.index("mirror = build_mirror(")
        grab_at = source.index("device.grab()")
        self.assertLess(build_at, grab_at)

    def test_no_stale_supplementary_groups_message(self):
        """The abandoned SupplementaryGroups approach must not be advertised."""
        source = Path(
            Path(__file__).resolve().parents[1] / "pen-scroll.py"
        ).read_text()
        self.assertNotIn("SupplementaryGroups=uinput is set", source)


if __name__ == "__main__":
    unittest.main()
