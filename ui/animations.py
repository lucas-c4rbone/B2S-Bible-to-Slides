from __future__ import annotations

import logging
import math
import tkinter as tk
from typing import Any

from ui.theme import (
    ANIM_ENTRANCE,
    ANIM_FAST,
    ANIM_FPS,
    ANIM_NORMAL,
    ANIM_PRESS_RESTORE,
    ANIM_REVEAL_OUT_MULTIPLIER,
    ANIM_SLOW,
    ANIM_STATUS,
    ANIM_WINDOW_PULSE,
    BG_APP,
    BG_TILE,
    CARD_BORDER,
    GRAD_MID,
    GRAD_START,
    INPUT_BORDER,
    INPUT_BORDER_FOC,
)

logger = logging.getLogger(__name__)


class FluentAnimations:
    """Provide reusable animation helpers for CustomTkinter widgets."""

    def _begin_animation(self, widget, channel: str) -> list[bool]:
        """Cancel any running animation for widget/channel and return a fresh token."""
        if not hasattr(self, "_anim_tokens"):
            self._anim_tokens = {}
        key = (id(widget), channel)
        old_token = self._anim_tokens.get(key)
        if old_token is not None:
            old_token[0] = True
        token = [False]
        self._anim_tokens[key] = token
        return token

    @staticmethod
    def _coerce_hex(raw: Any, fallback: str) -> str:
        if isinstance(raw, (list, tuple)):
            raw = raw[1] if len(raw) > 1 else raw[0]
        value = str(raw)
        if value.startswith("#") and len(value) in (4, 7):
            return value
        return fallback

    def _widget_color(self, widget, attr: str, fallback: str) -> str:
        try:
            return FluentAnimations._coerce_hex(widget.cget(attr), fallback)
        except (tk.TclError, AttributeError, ValueError, TypeError):
            return fallback

    @staticmethod
    def ease_out_cubic(t: float) -> float:
        return 1 - (1 - t) ** 3

    @staticmethod
    def ease_in_cubic(t: float) -> float:
        return t ** 3

    @staticmethod
    def ease_in_out_quint(t: float) -> float:
        if t < 0.5:
            return 16 * t ** 5
        return 1 - (-2 * t + 2) ** 5 / 2

    @staticmethod
    def ease_spring(t: float) -> float:
        c4 = (2 * math.pi) / 3
        if t == 0:
            return 0
        if t == 1:
            return 1
        return 2 ** (-8 * t) * math.sin((t * 10 - 0.75) * c4) + 1

    @staticmethod
    def blend_hex(c1: str, c2: str, t: float) -> str:
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def tween(
        self,
        duration_ms: int,
        on_update,
        ease=None,
        on_done=None,
        fps: int = ANIM_FPS,
        cancel_token: list | None = None,
    ) -> None:
        if ease is None:
            ease = self.ease_out_cubic
        interval = max(1, 1000 // fps)
        steps = max(1, duration_ms // interval)
        step_ref = [0]

        def _tick() -> None:
            if cancel_token is not None and cancel_token[0]:
                return
            step_ref[0] += 1
            raw = step_ref[0] / steps
            t = min(raw, 1.0)
            try:
                on_update(ease(t))
            except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                logger.debug("Ignored animation operation error: %s", exc, exc_info=True)
            if t < 1.0:
                self.after(interval, _tick)
            elif on_done:
                try:
                    on_done()
                except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                    logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

        self.after(0, _tick)

    def fade_widget(
        self,
        widget,
        from_color: str,
        to_color: str,
        duration_ms: int = ANIM_NORMAL,
        attr: str = "text_color",
        on_done=None,
        cancel_token: list | None = None,
    ) -> None:
        def _update(t: float) -> None:
            try:
                widget.configure(**{attr: self.blend_hex(from_color, to_color, t)})
            except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

        self.tween(duration_ms, _update, ease=self.ease_in_out_quint, on_done=on_done, cancel_token=cancel_token)

    def entrance_animation(
        self,
        widget,
        parent_grid_kw: dict[str, Any],
        delay_ms: int = 0,
        slide_px: int = 18,
        slide_x_px: int = 0,
        ease=None,
        on_done=None,
    ) -> None:
        """Keep entrance timing while using visual border reveal only."""
        del parent_grid_kw, slide_px, slide_x_px
        token = FluentAnimations._begin_animation(self, widget, "entrance")
        border_to = FluentAnimations._widget_color(self, widget, "border_color", CARD_BORDER)
        border_from = self.blend_hex(BG_APP, border_to, 0.72)

        def _update(t: float) -> None:
            try:
                widget.configure(border_color=self.blend_hex(border_from, border_to, t))
            except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

        self.after(
            delay_ms,
            lambda: self.tween(
                ANIM_ENTRANCE,
                _update,
                ease=ease or self.ease_out_cubic,
                on_done=on_done,
                cancel_token=token,
            ),
        )

    def scale_in_window(self) -> None:
        """Keep startup emphasis without geometry changes."""
        token = FluentAnimations._begin_animation(self, self, "window_pulse")
        try:
            alpha = float(self.attributes("-alpha"))
        except (tk.TclError, AttributeError, ValueError, TypeError, RuntimeError):
            return

        start_alpha = min(max(alpha, 0.92), 1.0)

        def _update(t: float) -> None:
            try:
                self.attributes("-alpha", start_alpha + (1.0 - start_alpha) * t)
            except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

        self.tween(ANIM_WINDOW_PULSE, _update, ease=self.ease_spring, cancel_token=token)

    def attach_reveal(
        self,
        widget,
        normal_border: str = CARD_BORDER,
        reveal_border: str = GRAD_START,
        duration_ms: int = ANIM_PRESS_RESTORE,
    ) -> None:
        _token: list[bool] = [False]
        _current_border: list[str] = [normal_border]
        _inside: list[bool] = [False]

        def _on_enter(_e) -> None:
            nonlocal _token
            if _inside[0]:
                return
            _inside[0] = True
            _token = FluentAnimations._begin_animation(self, widget, "reveal")
            from_color = _current_border[0]

            def _update(t: float) -> None:
                c = self.blend_hex(from_color, reveal_border, t)
                _current_border[0] = c
                try:
                    widget.configure(border_color=c)
                except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                    logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

            self.tween(duration_ms, _update, ease=self.ease_out_cubic, cancel_token=_token)

        def _on_leave(_e) -> None:
            nonlocal _token
            if not _inside[0]:
                return
            _inside[0] = False
            _token = FluentAnimations._begin_animation(self, widget, "reveal")
            from_color = _current_border[0]

            def _update(t: float) -> None:
                c = self.blend_hex(from_color, normal_border, t)
                _current_border[0] = c
                try:
                    widget.configure(border_color=c)
                except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                    logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

            self.tween(duration_ms * ANIM_REVEAL_OUT_MULTIPLIER, _update, ease=self.ease_out_cubic, cancel_token=_token)

        try:
            widget.bind("<Enter>", _on_enter, add="+")
            widget.bind("<Leave>", _on_leave, add="+")
        except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
            logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

    def attach_focus_reveal(
        self,
        widget,
        normal_border: str = CARD_BORDER,
        reveal_border: str = GRAD_START,
        duration_ms: int = ANIM_STATUS,
    ) -> None:
        _token: list[bool] = [False]
        _current: list[str] = [normal_border]

        def _on_focus_in(_e) -> None:
            nonlocal _token
            _token = FluentAnimations._begin_animation(self, widget, "focus_reveal")
            from_color = _current[0]

            def _update(t: float) -> None:
                c = self.blend_hex(from_color, reveal_border, t)
                _current[0] = c
                try:
                    widget.configure(border_color=c)
                except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                    logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

            self.tween(duration_ms, _update, ease=self.ease_out_cubic, cancel_token=_token)

        def _on_focus_out(_e) -> None:
            nonlocal _token
            _token = FluentAnimations._begin_animation(self, widget, "focus_reveal")
            from_color = _current[0]

            def _update(t: float) -> None:
                c = self.blend_hex(from_color, normal_border, t)
                _current[0] = c
                try:
                    widget.configure(border_color=c)
                except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                    logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

            self.tween(duration_ms, _update, ease=self.ease_out_cubic, cancel_token=_token)

        try:
            widget.bind("<FocusIn>", _on_focus_in, add="+")
            widget.bind("<FocusOut>", _on_focus_out, add="+")
        except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
            logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

    def attach_hover_lift(
        self,
        widget,
        lift_px: int = 3,
        duration_ms: int = ANIM_FAST,
    ) -> None:
        """Keep hover-lift feeling via color animation without layout reflow."""
        del lift_px

        _token: list[bool] = [False]
        _lifted = [False]
        base_color = FluentAnimations._widget_color(self, widget, "fg_color", BG_TILE)
        hover_color = self.blend_hex(base_color, GRAD_START, 0.12)
        current_color = [base_color]

        def _on_enter(_e) -> None:
            nonlocal _token
            if _lifted[0]:
                return
            _lifted[0] = True
            _token = FluentAnimations._begin_animation(self, widget, "hover_lift")
            from_color = current_color[0]

            def _up(t: float) -> None:
                try:
                    c = self.blend_hex(from_color, hover_color, t)
                    current_color[0] = c
                    widget.configure(fg_color=c)
                except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                    logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

            self.tween(duration_ms, _up, ease=self.ease_out_cubic, cancel_token=_token)

        def _on_leave(_e) -> None:
            nonlocal _token
            if not _lifted[0]:
                return
            _lifted[0] = False
            _token = FluentAnimations._begin_animation(self, widget, "hover_lift")
            from_color = current_color[0]

            def _down(t: float) -> None:
                try:
                    c = self.blend_hex(from_color, base_color, t)
                    current_color[0] = c
                    widget.configure(fg_color=c)
                except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                    logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

            self.tween(duration_ms * ANIM_REVEAL_OUT_MULTIPLIER, _down, ease=self.ease_out_cubic, cancel_token=_token)

        try:
            widget.bind("<Enter>", _on_enter, add="+")
            widget.bind("<Leave>", _on_leave, add="+")
        except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
            logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

    def attach_hover_brighten(self, widget, amount: float = 0.18, duration_ms: int = ANIM_FAST) -> None:
        """Animate a subtle brighten effect on hover for buttons."""
        _token: list[bool] = [False]
        _inside = [False]
        _current = [FluentAnimations._widget_color(self, widget, "fg_color", GRAD_START)]
        base_color = _current[0]

        def _on_enter(_e) -> None:
            nonlocal _token
            if _inside[0]:
                return
            _inside[0] = True
            _token = FluentAnimations._begin_animation(self, widget, "hover_brighten")
            from_color = _current[0]
            to_color = self.blend_hex(base_color, "#ffffff", max(0.0, min(0.4, amount)))

            def _up(t: float) -> None:
                try:
                    c = self.blend_hex(from_color, to_color, t)
                    _current[0] = c
                    widget.configure(fg_color=c)
                except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                    logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

            self.tween(duration_ms, _up, ease=self.ease_out_cubic, cancel_token=_token)

        def _on_leave(_e) -> None:
            nonlocal _token
            if not _inside[0]:
                return
            _inside[0] = False
            _token = FluentAnimations._begin_animation(self, widget, "hover_brighten")
            from_color = _current[0]
            to_color = base_color

            def _down(t: float) -> None:
                try:
                    c = self.blend_hex(from_color, to_color, t)
                    _current[0] = c
                    widget.configure(fg_color=c)
                except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                    logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

            self.tween(duration_ms * ANIM_REVEAL_OUT_MULTIPLIER, _down, ease=self.ease_out_cubic, cancel_token=_token)

        try:
            widget.bind("<Enter>", _on_enter, add="+")
            widget.bind("<Leave>", _on_leave, add="+")
        except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
            logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

    def attach_press_animation(self, widget) -> None:
        _token: list[bool] = [False]

        def _on_press(_e) -> None:
            nonlocal _token
            _token = FluentAnimations._begin_animation(self, widget, "press")
            try:
                widget.configure(fg_color=GRAD_MID)
            except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

        def _on_release(_e) -> None:
            nonlocal _token
            _token = FluentAnimations._begin_animation(self, widget, "press")
            from_color = FluentAnimations._widget_color(self, widget, "fg_color", GRAD_MID)

            def _restore(t: float) -> None:
                try:
                    widget.configure(fg_color=self.blend_hex(from_color, GRAD_START, t))
                except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                    logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

            self.tween(ANIM_PRESS_RESTORE, _restore, ease=self.ease_spring, cancel_token=_token)

        try:
            widget.bind("<ButtonPress-1>", _on_press, add="+")
            widget.bind("<ButtonRelease-1>", _on_release, add="+")
        except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
            logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

    def attach_acrylic_focus(self, widget) -> None:
        _token: list[bool] = [False]
        _current: list[str] = [INPUT_BORDER]

        def _on_focus_in(_e) -> None:
            nonlocal _token
            _token = FluentAnimations._begin_animation(self, widget, "acrylic_focus")
            from_color = _current[0]

            def _up(t: float) -> None:
                c = self.blend_hex(from_color, INPUT_BORDER_FOC, t)
                _current[0] = c
                try:
                    widget.configure(border_color=c)
                except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                    logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

            self.tween(ANIM_STATUS, _up, ease=self.ease_out_cubic, cancel_token=_token)

        def _on_focus_out(_e) -> None:
            nonlocal _token
            _token = FluentAnimations._begin_animation(self, widget, "acrylic_focus")
            from_color = _current[0]

            def _down(t: float) -> None:
                c = self.blend_hex(from_color, INPUT_BORDER, t)
                _current[0] = c
                try:
                    widget.configure(border_color=c)
                except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
                    logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

            self.tween(ANIM_SLOW, _down, ease=self.ease_out_cubic, cancel_token=_token)

        try:
            widget.bind("<FocusIn>", _on_focus_in, add="+")
            widget.bind("<FocusOut>", _on_focus_out, add="+")
        except (tk.TclError, AttributeError, ValueError, TypeError) as exc:
            logger.debug("Ignored animation operation error: %s", exc, exc_info=True)

    def _attach_floating_shadow(self, widget, parent, radius: int = 26, blur: int = 18, alpha: int = 130, offset: tuple[int, int] = (0, 10)) -> None:
        """Keep API compatibility; shadow effect remains optional/no-op for stability."""
        del widget, parent, radius, blur, alpha, offset
        return
