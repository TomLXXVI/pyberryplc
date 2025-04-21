from __future__ import annotations
from typing import Callable
import sympy as sp
import numpy as np
from scipy.integrate import solve_ivp
from . import Quantity

Q_ = Quantity


# ------------------------------------------------------------------------------
def velocity(
    t: float,
    a: Callable[[float], float],
    t0: float = 0.0,
    v0: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """Calculates values of the velocity between time moments `t0` and `t`
    (where `t` > `t0`) when the acceleration `a` is given as a function of time
    (i.e. the function `a` should be called as `a(t)`). `v0` is the known
    velocity at time moment `t0`.

    Returns
    -------
    Tuple of two Numpy arrays. The first array contains the time values at which
    the velocity is determined. The second array contains the corresponding
    values of the velocity.
    """
    # noinspection PyUnusedLocal
    def fun(t: float, v: np.ndarray) -> np.ndarray:
        v_dot = np.zeros(1)
        v_dot[0] = a(t)
        return v_dot

    sol = solve_ivp(fun, (t0, t), [v0], method='LSODA', t_eval=np.linspace(t0, t))
    return sol.t, sol.y[0]


# ------------------------------------------------------------------------------
def position(
    t: float,
    a: Callable[[float], float],
    t0: float = 0.0,
    v0: float = 0.0,
    s0: float = 0.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculates values of position between time moments `t0` and `t`
    (where `t` > `t0`) when the acceleration `a` is given as a function of time
    (i.e. the function `a` should be called as `a(t)`). `v0` and `s0` are
    respectively the known velocity and the known position at time moment `t0`.

    Returns
    -------
    Tuple of three Numpy arrays. The first array contains the time values at
    which the position is determined. The second array contains the corresponding
    values of the position. In the third array, the corresponding values of the
    velocity are also returned.
    """
    def fun(t: float, s: np.ndarray) -> np.ndarray:
        s_dot = np.zeros(2)
        s_dot[0] = s[1]
        s_dot[1] = a(t)
        return s_dot

    sol = solve_ivp(fun, (t0, t), [s0, v0], method='LSODA', t_eval=np.linspace(t0, t))
    return sol.t, sol.y[0], sol.y[1]


# ------------------------------------------------------------------------------
class ConstantAcceleratedMotion:
    """Implements two kinematic equations which are valid when acceleration is
    uniform (constant). The two equations are implemented with Sympy, and they
    are encapsulated in two classes. Class `VelocityEquation` contains the
    equation for calculating the velocity at a given time moment. Class
    `PositionEquation` contains the equation for calculating the position at
    a given time moment.
    """
    class VelocityEquation:
        """Implements the velocity equation."""

        def __init__(self, v0: float, t0: float) -> None:
            """Creates a `VelocityEquation` object.

            Parameters
            ----------
            v0:
                The known initial velocity at time moment `t0`.
            t0:
                Initial time moment where the velocity must already be known.
            """
            self._v0 = v0
            self._t0 = t0
            self._t = sp.Symbol('t')
            self._v = sp.Symbol('v')
            self._a = sp.Symbol('a')
            self._eq = sp.Eq(self._v - self._v0 - self._a * (self._t - self._t0), 0)

        def solve(
            self,
            t: float | None = None,
            v: float | None = None,
            a: float | None = None
        ) -> float | None:
            """Solves the velocity equation.

            Parameters
            ----------
            t:
                Time moment at which the velocity needs to be determined.
            v:
                The velocity at time moment `t` if known, else `None`.
            a:
                The constant acceleration at time moment `t` if known, else
                `None`.

            The values of two parameters must be specified. The equation will
            solve for the value of the third parameter. E.g. if time moment
            `t` and constant acceleration `a` are specified and parameter `v`
            is left to `None`, method `solve` will return the corresponding
            velocity at time moment `t`.
            """
            unknown = None
            if t is not None:
                t = t
                self._eq = self._eq.subs(self._t, t)
            else:
                unknown = self._t
            if v is not None:
                v = v
                self._eq = self._eq.subs(self._v, v)
            else:
                unknown = self._v
            if a is not None:
                a = a
                self._eq = self._eq.subs(self._a, a)
            else:
                unknown = self._a
            if unknown is not None:
                sol = sp.solve(self._eq, unknown)
                if sol and isinstance(sol, list):
                    sol = float(sol[0])
                    if unknown is self._t:
                        self._t = sol
                        return self._t
                    elif unknown is self._v:
                        self._v = sol
                        return self._v
                    elif unknown is self._a:
                        self._a = sol
                        return self._a
            return None

    class PositionEquation:
        """Implements the position equation."""

        def __init__(self, s0: float, v0: float, t0: float) -> None:
            """Creates a `VelocityEquation` object.

            Parameters
            ----------
            s0:
                The known initial position at time moment `t0`.
            v0:
                The known initial velocity at time moment `t0`.
            t0:
                Initial time moment where the position and velocity must
                already be known.
            """
            self._s0 = s0
            self._v0 = v0
            self._t0 = t0
            self._s = sp.Symbol('s')
            self._t = sp.Symbol('t')
            self._a = sp.Symbol('a')
            self._eq = sp.Eq(
                (self._s - self._s0
                 - self._v0 * (self._t - self._t0)
                 - 0.5 * self._a * (self._t - self._t0) ** 2),
                0
            )

        def solve(
            self,
            t: float | None = None,
            s: float | None = None,
            a: float | None = None
        ) -> float | None:
            """Solves the position equation.

            Parameters
            ----------
            t:
                Time moment at which the position needs to be determined.
            s:
                The position at time moment `t` if known, else `None`.
            a:
                The constant acceleration at time moment `t` if known, else
                `None`.

            The values of two parameters must be specified. The equation will
            solve for the value of the third parameter. E.g. if time moment
            `t` and constant acceleration `a` are specified and parameter `s`
            is left to `None`, method `solve` will return the corresponding
            position at time moment `t`.
            """
            unknown = None
            if t is not None:
                t = t
                self._eq = self._eq.subs(self._t, t)
            else:
                unknown = self._t
            if s is not None:
                s = s
                self._eq = self._eq.subs(self._s, s)
            else:
                unknown = self._s
            if a is not None:
                a = a
                self._eq = self._eq.subs(self._a, a)
            else:
                unknown = self._a
            if unknown is not None:
                sol = sp.solve(self._eq, unknown)
                if isinstance(sol, list):
                    sol = float(sol[0])
                if unknown is self._t:
                    self._t = sol
                    return self._t
                elif unknown is self._s:
                    self._s = sol
                    return self._s
                elif unknown is self._a:
                    self._a = sol
                    return self._a
            return None


# ------------------------------------------------------------------------------
def counts_to_angular_speed(
    num_counts: int,
    counts_per_rev: int,
    time_unit: str = 'ms'
) -> Quantity:
    omega = 2 * np.pi * num_counts * (1 / counts_per_rev)  # radians / time_unit
    omega = Q_(omega, f'rad / {time_unit}')
    return omega
