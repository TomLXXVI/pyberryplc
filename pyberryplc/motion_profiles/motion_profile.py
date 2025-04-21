"""
Definition of motion profiles for single-axis motion.

Two types of profiles are implemented in this module:
- Class `TrapezoidalProfile` defines a trapezoidal motion profile.
- Class `SCurvedProfile` defines a pure S-curve motion profile.

References
----------
Gürocak, H. (2016), Industrial Motion Control, John Wiley & Sons.
"""
from __future__ import annotations
from typing import Callable
from abc import ABC, abstractmethod

import numpy as np
import scipy
import pint

from . import Quantity, LineChart
from .kinematics import position, velocity, ConstantAcceleratedMotion


Q_ = Quantity
CAM = ConstantAcceleratedMotion


class ConfigError(Exception):
    pass


class DistanceError(Exception):
    pass


class TimingError(Exception):
    pass


class MotionProfile(ABC):
    """
    Base class for defining a symmetrical single-axis motion profile.
    The acceleration and deceleration region of the velocity profile have the
    same shape and dimensions.

    After instantiation of the class, following properties of the motion profile
    are available:

    Attributes
    ----------
    `v_m`:
        Top velocity.
    `a_m`:
        Maximum acceleration.
    `ds_tot`:
        Total travel distance.
    `dt_tot`:
        Total travel time.
    `dt_acc`:
        Acceleration time.
    `ds_acc`:
        Acceleration distance.
    `dt_dec`:
        Deceleration time (always equal to acceleration time).
    `ds_dec`:
        Deceleration distance (always equal to acceleration distance).
    `dt_cov`:
        Constant velocity time, i.e. the time between the acceleration time
        and the deceleration time when the axis moves at constant speed.
    `ds_cov`:
        Constant velocity distance.

    Also, a time profile of velocity, position, and acceleration can be
    calculated using methods `velocity_profile()`, `position_profile()`, and
    `acceleration_profile()`. These profiles can then be drawn on a line chart
    using the functions `draw_velocity_profiles`, `draw_position_profiles`, and
    `draw_acceleration_profiles`.
    """

    # noinspection PyUnresolvedReferences
    def __init__(
        self,
        v_m: Quantity | None = None,
        a_m: Quantity | None = None,
        dt_tot: Quantity | None = None,
        ds_tot: Quantity | None = None,
        dt_acc: Quantity | None = None,
        translation: bool = False
    ) -> None:
        """Creates a `MotionProfile` object.

        Parameters
        ----------
        v_m:
            Top velocity of the single-axis motion.
        a_m:
            Maximum (allowable) acceleration during the motion.
        dt_tot:
            Total travel time (motion time).
        ds_tot:
            Total travel distance.
        dt_acc:
            Acceleration time.
        translation:
            Indicates whether the motion is translational (`True`) or rotational
            (`False`). Default is `False`.

        A motion profile can be defined in four different ways:
        1.  Either `v_m`, `a_m` (or `dt_acc`), and `ds_tot` are specified (other
            parameters left to `None`);
        2.  Either `v_m`, `a_m` (or `dt_acc`), and `dt_tot` are specified;
        3.  Either `dt_acc`, `dt_tot`, and `ds_tot` are specified;
        4.  Or only `ds_tot` and `dt_tot` are specified.

        In the 1st case, the total travel time can be determined. In the 2nd
        case, the total travel distance can be determined. In the 3rd case,
        the required acceleration can be determined. In the 4th case, the
        minimum possible acceleration can be determined (motion profile without
        a constant-velocity phase, i.e. a triangular velocity profile).
        """
        self._translation = translation
        _u_t = {
            'v': 'm / s',
            'a': 'm / s**2',
            'x': 'm'
        }
        _u_r = {
            'v': 'rad / s',
            'a': 'rad / s**2',
            'x': 'rad'
        }
        self._u = _u_t if self._translation else _u_r

        self._v_m = None
        self._a_m = None
        self._ds_tot = None
        self._dt_tot = None
        self._ds_acc = None
        self._dt_acc = None
        self._ds_dec = None
        self._dt_dec = None
        self._ds_cov = None
        self._dt_cov = None
        self._accel_fun = None
        self._decel_fun = None

        if isinstance(v_m, Quantity):
            self._v_m = v_m.to(self._u['v']).magnitude
        if isinstance(a_m, Quantity):
            self._a_m = a_m.to(self._u['a']).magnitude
        elif a_m is None and self._v_m is not None and isinstance(dt_acc, Quantity):
            self._dt_acc = dt_acc.to('s').magnitude
            self._a_m = self._calc_accel()
        if isinstance(ds_tot, Quantity):
            self._ds_tot = ds_tot.to(self._u['x']).magnitude
        if isinstance(dt_tot, Quantity):
            self._dt_tot = dt_tot.to('s').magnitude
        if isinstance(dt_acc, Quantity):
            self._dt_acc = dt_acc.to('s').magnitude
        elif dt_acc is None and isinstance(a_m, Quantity):
            self._dt_acc = self._calc_accel_duration()

        # Use case 1 - Determine total travel time.
        # Given: v_m, a_m, and ds_tot.
        if all([self._v_m, self._a_m, self._ds_tot]):
            self._calc_total_travel_time()

        # Use case 2 - Determine total travel distance.
        # Given: v_m, a_m, and dt_tot. 
        elif all([self._v_m, self._a_m, self._dt_tot]):
            self._calc_total_travel_distance()

        # Use case 3 - Determine required acceleration.
        elif all([self._dt_acc, self._dt_tot, self._ds_tot]):
            self._calc_required_acceleration()

        # Use case 4 - Determine minimum acceleration and
        # corresponding top velocity. Given: ds_tot, dt_tot
        elif all([self._dt_tot, self._ds_tot]):
            self._calc_minimum_acceleration()
        else:
            raise ConfigError(
                "Cannot create the motion profile. Parameters are missing or "
                "wrong parameters are given."
            )
    
    @property
    def v_m(self) -> Quantity | None:
        """Top velocity."""
        if isinstance(self._v_m, float):
            return Q_(self._v_m, self._u['v'])
        return None

    @property
    def a_m(self) -> Quantity | None:
        """Maximum acceleration."""
        if isinstance(self._a_m, float):
            return Q_(self._a_m, self._u['a'])
        return None

    @property
    def ds_tot(self) -> Quantity | None:
        """Total travel distance."""
        if isinstance(self._ds_tot, float):
            return Q_(self._ds_tot, self._u['x'])
        return None

    @property
    def dt_tot(self) -> Quantity | None:
        """Total travel time."""
        if isinstance(self._dt_tot, float):
            return Q_(self._dt_tot, 's')
        return None

    @property
    def ds_acc(self) -> Quantity | None:
        """Acceleration distance."""
        if isinstance(self._ds_acc, float):
            return Q_(self._ds_acc, self._u['x'])
        return None

    @property
    def dt_acc(self) -> Quantity | None:
        """Acceleration time."""
        if isinstance(self._dt_acc, float):
            return Q_(self._dt_acc, 's')
        return None

    @property
    def ds_dec(self) -> Quantity | None:
        """Deceleration distance."""
        if isinstance(self._ds_dec, float):
            return Q_(self._ds_dec, self._u['x'])
        return None

    @property
    def dt_dec(self) -> Quantity | None:
        """Deceleration time."""
        if isinstance(self._dt_dec, float):
            return Q_(self._dt_dec, 's')
        return None

    @property
    def ds_cov(self) -> Quantity | None:
        """Constant-velocity distance."""
        if isinstance(self._ds_cov, float):
            return Q_(self._ds_cov, self._u['x'])
        return None

    @property
    def dt_cov(self) -> Quantity | None:
        """Constant-velocity time."""
        if isinstance(self._dt_cov, float):
            return Q_(self._dt_cov, 's')
        return None

    @abstractmethod
    def _create_accel_fun(self) -> Callable[[float], float]:
        ...

    @abstractmethod
    def _create_decel_fun(self) -> Callable[[float], float]:
        ...

    @abstractmethod
    def _calc_accel_duration(self) -> float:
        ...

    @abstractmethod
    def _calc_decel_duration(self) -> float:
        ...

    @abstractmethod
    def _calc_accel(self) -> float:
        ...

    def _calc_total_travel_time(self) -> None:
        # acceleration phase
        # self._dt_acc = self._calc_accel_duration()
        self._accel_fun = self._create_accel_fun()
        self._ds_acc = self._calc_accel_distance()
        # deceleration phase
        self._dt_dec = self._calc_decel_duration()
        self._ds_dec = self._ds_acc
        # constant velocity phase
        self._ds_cov = self._ds_tot - self._ds_acc - self._ds_dec
        if self._ds_cov < 0:
            raise DistanceError(
                "Not enough travel distance available for acceleration "
                "and deceleration."
            )
        self._dt_cov = self._calc_cst_veloc_duration()
        # total travel time
        self._dt_tot = self._dt_acc + self._dt_cov + self._dt_dec
        self._decel_fun = self._create_decel_fun()

    def _calc_total_travel_distance(self) -> None:
        # acceleration phase
        # self._dt_acc = self._calc_accel_duration()
        self._accel_fun = self._create_accel_fun()
        self._ds_acc = self._calc_accel_distance()
        # deceleration phase
        self._dt_dec = self._dt_acc
        self._ds_dec = self._ds_acc
        # constant velocity phase
        self._dt_cov = self._dt_tot - self._dt_acc - self._dt_dec
        if self._dt_cov < 0:
            raise TimingError(
                "Not enough travel time available for acceleration and "
                "deceleration."
            )
        self._ds_cov = self._calc_cst_veloc_distance()
        # total travel distance
        self._ds_tot = self._ds_acc + self._ds_cov + self._ds_dec
        self._decel_fun = self._create_decel_fun()

    def _calc_minimum_acceleration(self) -> None:
        self._v_m = 2 * self._ds_tot / self._dt_tot
        self._a_m = 2 * self._v_m / self._dt_tot
        # acceleration phase
        # self._dt_acc = self._calc_accel_duration()
        self._accel_fun = self._create_accel_fun()
        self._ds_acc = self._calc_accel_distance()
        # deceleration phase
        self._dt_dec = self._dt_acc
        self._ds_dec = self._ds_acc
        # constant velocity phase
        self._dt_cov = 0.0
        self._ds_cov = 0.0
        self._decel_fun = self._create_decel_fun()
    
    def _calc_required_acceleration(self):
        self._dt_dec = self._dt_acc
        self._dt_cov = self._dt_tot - self._dt_acc - self._dt_dec
        self._v_m = self._ds_tot / (self._dt_cov + self._dt_acc)
        self._ds_cov = self._v_m * self._dt_cov
        self._ds_acc = (self._ds_tot - self._ds_cov) / 2
        self._ds_dec = self._ds_acc
        self._a_m = self._calc_accel()
        self._accel_fun = self._create_accel_fun()
        self._decel_fun = self._create_decel_fun()

    def _calc_accel_distance(self) -> float:
        t0 = 0.0
        t1 = t0 + self._dt_acc
        v0 = 0.0
        s0 = 0.0
        _, s, _ = position(t1, self._accel_fun, t0, v0, s0)
        s1 = float(s[-1])
        ds_acc = s1 - s0
        return ds_acc

    def _calc_cst_veloc_duration(self) -> float:
        pos_eq = CAM.PositionEquation(s0=0.0, v0=self._v_m, t0=0.0)
        dt_cov = pos_eq.solve(s=self._ds_cov, a=0.0)
        return dt_cov

    def _calc_cst_veloc_distance(self) -> float:
        pos_eq = CAM.PositionEquation(s0=0.0, v0=self._v_m, t0=0.0)
        ds_cov = pos_eq.solve(t=self._dt_cov, a=0.0)
        return ds_cov

    def velocity_profile(self) -> tuple[Quantity, Quantity]:
        """Calculates the velocity profile.

        Returns
        -------
        A tuple with two `Quantity` arrays. The first array are time values.
        The second array are the corresponding values of the velocity.
        """
        # acceleration phase
        t0, v0 = 0.0, 0.0
        t1 = t0 + self._dt_acc
        t1_arr, v1_arr = velocity(t1, self._accel_fun, t0, v0)
        # constant velocity phase
        t1, v1 = float(t1_arr[-1]), float(v1_arr[-1])
        t2 = t1 + self._dt_cov
        if t2 > t1:
            t2_arr, v2_arr = velocity(t2, lambda t: 0.0, t1, v1)
            t2, v2 = float(t2_arr[-1]), float(v2_arr[-1])
        else:
            t2_arr, v2_arr = None, None
            t2, v2 = float(t1_arr[-1]), float(v1_arr[-1])
        # deceleration phase
        t3 = t2 + self._dt_dec
        t3_arr, v3_arr = velocity(t3, self._decel_fun, t2, v2)
        if t2_arr is None:
            t_arr = Q_(np.concatenate((t1_arr, t3_arr)), 's')
        else:
            t_arr = Q_(np.concatenate((t1_arr, t2_arr, t3_arr)), 's')
        if v2_arr is None:
            v_arr = Q_(np.concatenate((v1_arr, v3_arr)), self._u['v'])
        else:
            v_arr = Q_(np.concatenate((v1_arr, v2_arr, v3_arr)), self._u['v'])
        return t_arr, v_arr

    def position_profile(self) -> tuple[Quantity, Quantity]:
        """Calculates the position profile.

        Returns
        -------
        A tuple with two `Quantity` arrays. The first array are time values.
        The second array are the corresponding values of the position.
        """
        # acceleration phase
        t0, v0, s0 = 0.0, 0.0, 0.0
        t1 = t0 + self._dt_acc
        t1_arr, s1_arr, v1_arr = position(t1, self._accel_fun, t0, v0, s0)
        # constant velocity phase
        t1, v1, s1 = float(t1_arr[-1]), float(v1_arr[-1]), float(s1_arr[-1])
        t2 = t1 + self._dt_cov
        if t2 > t1:
            t2_arr, s2_arr, v2_arr = position(t2, lambda t: 0.0, t1, v1, s1)
            t2, v2, s2 = float(t2_arr[-1]), float(v2_arr[-1]), float(s2_arr[-1])
        else:
            t2_arr, s2_arr, v2_arr = None, None, None
            t2, v2, s2 = float(t1_arr[-1]), float(v1_arr[-1]), float(s1_arr[-1])
        # deceleration phase
        t3 = t2 + self._dt_dec
        t3_arr, s3_arr, _ = position(t3, self._decel_fun, t2, v2, s2)
        if t2_arr is None:
            t_arr = Q_(np.concatenate((t1_arr, t3_arr)), 's')
        else:
            t_arr = Q_(np.concatenate((t1_arr, t2_arr, t3_arr)), 's')
        if s2_arr is None:
            s_arr = Q_(np.concatenate((s1_arr, s3_arr)), self._u['x'])
        else:
            s_arr = Q_(np.concatenate((s1_arr, s2_arr, s3_arr)), self._u['x'])
        return t_arr, s_arr

    def acceleration_profile(self) -> tuple[Quantity, Quantity]:
        """Calculates the acceleration profile.

        Returns
        -------
        A tuple with two `Quantity` arrays. The first array are time values.
        The second array are the corresponding values of the acceleration.
        """
        # acceleration phase
        t0, a0 = 0.0, 0.0
        t1 = t0 + self._dt_acc
        t1_arr = np.linspace(t0, t1, endpoint=True)
        a1_arr = np.array([self._accel_fun(t) for t in t1_arr])
        # constant velocity phase
        t1, a1 = float(t1_arr[-1]), float(a1_arr[-1])
        t2 = t1 + self._dt_cov
        if t2 > t1:
            t2_arr = np.linspace(t1, t2, endpoint=True)
            a2_arr = np.array([0.0 for _ in t2_arr])
            t2, a2 = float(t2_arr[-1]), float(a2_arr[-1])
        else:
            t2_arr = None
            a2_arr = None
            t2, a2 = float(t1_arr[-1]), float(a1_arr[-1])
        # deceleration phase
        t3 = t2 + self._dt_dec
        t3_arr = np.linspace(t2, t3, endpoint=True)
        a3_arr = np.array([self._decel_fun(t) for t in t3_arr])
        if t2_arr is None:
            t_arr = Q_(np.concatenate((t1_arr, t3_arr)), 's')
        else:
            t_arr = Q_(np.concatenate((t1_arr, t2_arr, t3_arr)), 's')
        if a2_arr is None:
            a_arr = Q_(np.concatenate((a1_arr, a2_arr, a3_arr)), self._u['a'])
        else:
            a_arr = Q_(np.concatenate((a1_arr, a2_arr, a3_arr)), self._u['a'])
        return t_arr, a_arr

    def velocity_from_time_fn(
        self,
        N: Quantity | None = None
    ) -> Callable[[Quantity], Quantity]:
        """Returns a function that takes a time moment (`Quantity` object) and
        returns the velocity (`Quantity` object) at that time moment.

        Parameters
        ----------
        N:
            Transmission ratio. If not `None`, the velocity will be converted
            to angular speed based on this value, which is the ratio of motor
            speed (e.g. rpm) to load speed (e.g. m/s).
        """
        if self._translation:
            t_ax, v_ax = self.velocity_profile()
            if N is not None and N.check('1 / [length]'):
                # translation --> rotation:
                w_ax = N * v_ax
                interp = scipy.interpolate.interp1d(
                    t_ax.to('s').m,
                    w_ax.to('rad / s').m
                )

                def fun(t: Quantity) -> Quantity:
                    t_ = t.to('s').m
                    try:
                        w_ = interp(t_)
                    except ValueError:
                        return Q_(0.0, 'rad / s')
                    return Q_(w_, 'rad / s')

            elif N is not None and N.check('[length] / [length]'):
                # translation --> translation
                v_ax = N * v_ax
                interp = scipy.interpolate.interp1d(
                    t_ax.to('s').m,
                    v_ax.to('m / s').m
                )

                def fun(t: Quantity) -> Quantity:
                    t_ = t.to('s').m
                    try:
                        v_ = interp(t_)
                    except ValueError:
                        return Q_(0.0, 'm / s')
                    return Q_(v_, 'm / s')

            else:
                # translation --> translation:
                interp = scipy.interpolate.interp1d(
                    t_ax.to('s').m,
                    v_ax.to('m / s').m
                )

                def fun(t: Quantity) -> Quantity:
                    t_ = t.to('s').m
                    try:
                        v_ = interp(t_)
                    except ValueError:
                        return Q_(0.0, 'm / s')
                    return Q_(v_, 'm / s')

        else:
            t_ax, w_ax = self.velocity_profile()
            if N is not None and N.check(''):
                # rotation --> rotation:
                w_ax = N * w_ax
                interp = scipy.interpolate.interp1d(
                    t_ax.to('s').m,
                    w_ax.to('rad / s').m
                )

                def fun(t: Quantity) -> Quantity:
                    t_ = t.to('s').m
                    try:
                        w_ = interp(t_)
                    except ValueError:
                        return Q_(0.0, 'rad / s')
                    return Q_(w_, 'rad / s')

            elif N is not None and N.check('1 / [length]'):
                # rotation --> translation
                v_ax = N * w_ax
                interp = scipy.interpolate.interp1d(
                    t_ax.to('s').m,
                    v_ax.to('m / s').m
                )

                def fun(t: Quantity) -> Quantity:
                    t_ = t.to('s').m
                    try:
                        v_ = interp(t_)
                    except ValueError:
                        return Q_(0.0, 'm / s')
                    return Q_(v_, 'm / s')

            else:
                # rotation -> rotation
                interp = scipy.interpolate.interp1d(
                    t_ax.to('s').m,
                    w_ax.to('rad / s').m
                )

                def fun(t: Quantity) -> Quantity:
                    t_ = t.to('s').m
                    try:
                        w_ = interp(t_)
                    except ValueError:
                        return Q_(0.0, 'rad / s')
                    return Q_(w_, 'rad / s')

        return fun

    def position_from_time_fn(
        self,
        N: Quantity | None = None
    ) -> Callable[[Quantity], Quantity]:
        """Returns a function that takes a time moment (`Quantity` object) and
        returns the position (`Quantity` object) at that time moment.

        Parameters
        ----------
        N:
            Transmission ratio. If not `None`, the position will be converted
            to an angle based on this value, which is the ratio of motor speed
            (e.g. rpm) to load speed (e.g. m/s).
        """
        if self._translation:
            t_ax, s_ax = self.position_profile()
            if N is not None and N.check('1 / [length]'):
                # translation --> rotation:
                theta_ax = N * s_ax
                interp = scipy.interpolate.interp1d(
                    t_ax.to('s').m,
                    theta_ax.to('rad').m
                )

                def fun(t: Quantity) -> Quantity:
                    t_ = t.to('s').m
                    try:
                        theta_ = interp(t_)
                    except ValueError:
                        return theta_ax[-1]
                    return Q_(theta_, 'rad')

            elif N is not None and N.check('[length] / [length]'):
                # translation --> translation
                s_ax = N * s_ax
                interp = scipy.interpolate.interp1d(
                    t_ax.to('s').m,
                    s_ax.to('m').m
                )

                def fun(t: Quantity) -> Quantity:
                    t_ = t.to('s').m
                    try:
                        s_ = interp(t_)
                    except ValueError:
                        return s_ax[-1]
                    return Q_(s_, 'm')

            else:
                # translation --> translation:
                interp = scipy.interpolate.interp1d(
                    t_ax.to('s').m,
                    s_ax.to('m').m
                )

                def fun(t: Quantity) -> Quantity:
                    t_ = t.to('s').m
                    try:
                        s_ = interp(t_)
                    except ValueError:
                        return s_ax[-1]
                    return Q_(s_, 'm')

        else:
            t_ax, theta_ax = self.position_profile()
            if N is not None and N.check(''):
                # rotation --> rotation:
                theta_ax = N * theta_ax
                interp = scipy.interpolate.interp1d(
                    t_ax.to('s').m,
                    theta_ax.to('rad').m
                )

                def fun(t: Quantity) -> Quantity:
                    t_ = t.to('s').m
                    try:
                        theta_ = interp(t_)
                    except ValueError:
                        return theta_ax[-1]
                    return Q_(theta_, 'rad')

            elif N is not None and N.check('1 / [length]'):
                # rotation --> translation
                s_ax = N * theta_ax
                interp = scipy.interpolate.interp1d(
                    t_ax.to('s').m,
                    s_ax.to('m').m
                )

                def fun(t: Quantity) -> Quantity:
                    t_ = t.to('s').m
                    try:
                        s_ = interp(t_)
                    except ValueError:
                        return s_ax[-1]
                    return Q_(s_, 'm')

            else:
                # rotation -> rotation
                interp = scipy.interpolate.interp1d(
                    t_ax.to('s').m,
                    theta_ax.to('rad').m
                )

                def fun(t: Quantity) -> Quantity:
                    t_ = t.to('s').m
                    try:
                        theta_ = interp(t_)
                    except ValueError:
                        return theta_ax[-1]
                    return Q_(theta_, 'rad')

        return fun
    
    def time_from_position_fn(
        self,
        N: Quantity | None = None
    ) -> Callable[[Quantity], Quantity]:
        """Returns a function that takes a position (`Quantity` object) and
        returns the time moment (`Quantity` object) at that position.

        Parameters
        ----------
        N:
            Transmission ratio. If not `None`, the position will be converted
            to an angle based on this value, which is the ratio of motor speed
            (e.g. rpm) to load speed (e.g. m/s).
        """
        if self._translation:
            t_ax, s_ax = self.position_profile()
            if N is not None and N.check('1 / [length]'):
                # translation --> rotation:
                theta_ax = N * s_ax
                interp = scipy.interpolate.interp1d(
                    theta_ax.to('rad').m,
                    t_ax.to('s').m
                )

                def fun(theta: Quantity) -> Quantity:
                    theta_ = theta.to('rad').m
                    try:
                        t_ = interp(theta_)
                    except ValueError:
                        return t_ax[-1]
                    return Q_(t_, 's')

            elif N is not None and N.check('[length] / [length]'):
                # translation --> translation
                s_ax = N * s_ax
                interp = scipy.interpolate.interp1d(
                    s_ax.to('m').m,
                    t_ax.to('s').m,
                )

                def fun(s: Quantity) -> Quantity:
                    s_ = s.to('m').m
                    try:
                        t_ = interp(s_)
                    except ValueError:
                        return t_ax[-1]
                    return Q_(t_, 's')

            else:
                # translation --> translation:
                interp = scipy.interpolate.interp1d(
                    s_ax.to('m').m,
                    t_ax.to('s').m
                )

                def fun(s: Quantity) -> Quantity:
                    s_ = s.to('m').m
                    try:
                        t_ = interp(s_)
                    except ValueError:
                        return t_ax[-1]
                    return Q_(t_, 's')

        else:
            t_ax, theta_ax = self.position_profile()
            if N is not None and N.check(''):
                # rotation --> rotation:
                theta_ax = N * theta_ax
                interp = scipy.interpolate.interp1d(
                    theta_ax.to('rad').m,
                    t_ax.to('s').m
                )
                
                def fun(theta: Quantity) -> Quantity:
                    theta_ = theta.to('rad').m
                    try:
                        t_ = interp(theta_)
                    except ValueError:
                        return t_ax[-1]
                    return Q_(t_, 's')

            elif N is not None and N.check('1 / [length]'):
                # rotation --> translation
                s_ax = N * theta_ax
                interp = scipy.interpolate.interp1d(
                    s_ax.to('m').m,
                    t_ax.to('s').m
                )

                def fun(s: Quantity) -> Quantity:
                    s_ = s.to('m').m
                    try:
                        t_ = interp(s_)
                    except ValueError:
                        return t_ax[-1]
                    return Q_(t_, 's')

            else:
                # rotation -> rotation
                interp = scipy.interpolate.interp1d(
                    theta_ax.to('rad').m,
                    t_ax.to('s').m
                )

                def fun(theta: Quantity) -> Quantity:
                    theta_ = theta.to('rad').m
                    try:
                        t_ = interp(theta_)
                    except ValueError:
                        return t_ax[-1]
                    return Q_(t_, 's')

        return fun


class TrapezoidalProfile(MotionProfile):
    """
    Use this class to define a trapezoidal motion profile.
    """
    def _create_accel_fun(self) -> Callable[[float], float]:
        # noinspection PyUnusedLocal
        def a(t: float) -> float:
            return self._a_m
        return a

    def _create_decel_fun(self) -> Callable[[float], float]:
        # noinspection PyUnusedLocal
        def a(t: float) -> float:
            return -self._a_m
        return a

    def _calc_accel_duration(self) -> float:
        dt_acc = self._v_m / self._a_m
        return dt_acc

    def _calc_decel_duration(self) -> float:
        return self._dt_acc

    def _calc_accel(self) -> float:
        return self._v_m / self._dt_acc


class SCurvedProfile(MotionProfile):
    """
    Use this class to define a pure S-curve motion profile.
    """
    def _create_accel_fun(self) -> Callable[[float], float]:
        c1 = self._a_m ** 2 / self._v_m
        t0 = 0.0
        t1 = t0 + self._dt_acc / 2
        t2 = t1 + self._dt_acc / 2

        def a(t: float) -> float:
            if t0 <= t <= t1:
                return c1 * t
            elif t1 < t <= t2:
                return -c1 * (t - t2)
            else:
                return 0.0
        return a

    def _create_decel_fun(self) -> Callable[[float], float]:
        c1 = self._a_m ** 2 / self._v_m
        t0 = self._dt_acc + self._dt_cov
        t1 = t0 + self._dt_dec / 2
        t2 = t1 + self._dt_dec / 2

        def a(t: float) -> float:
            if t0 <= t <= t1:
                return -c1 * (t - t0)
            elif t1 < t <= t2:
                return c1 * (t - t2)
            else:
                return 0.0
        return a

    def _calc_accel_duration(self) -> float:
        dt_acc = 2 * self._v_m / self._a_m
        return dt_acc

    def _calc_decel_duration(self) -> float:
        return self._dt_acc

    def _calc_accel(self) -> float:
        return 2 * self._v_m / self._dt_acc


def _set_units(units: dict[str, str] | None = None) -> dict[str, str]:
    default_units = {
        'time': 's',
        'position': 'm',
        'velocity': 'm / s',
        'acceleration': 'm / s**2'
    }
    if isinstance(units, dict):
        default_units.update(units)
    return default_units


def draw_velocity_profiles(
    profiles: list[tuple[Quantity, Quantity]],
    units: dict[str, str] | None = None
) -> LineChart:
    """Given a list of velocity profiles (as returned from
    `MotionProfile.velocity_profile()`), draws them on a `LineChart` object and
    returns this object.

    Parameter `units` can be dictionary with the units that need to be used
    for drawing the charts. The default dictionary (when parameter `units` is
    left to `None`) is:
    ```
    default_units = {
        'time': 's',
        'position': 'm',
        'velocity': 'm / s',
        'acceleration': 'm / s**2'
    }
    ```
    To change any of the default units, it suffices to pass a dictionary with
    the appropriate keys and the desired units. E.g. to only change the units of
    velocity to 'in / s' (instead of 'm / s'), pass a dict to parameter `units`
    defined as `{'velocity': 'in / s'}`.
    """
    units = _set_units(units)
    vp = LineChart()
    i = 0
    for t_arr, v_arr in profiles:
        vp.add_xy_data(
            label=f'velocity profile {i + 1}',
            x1_values=t_arr.to(units['time']).magnitude,
            y1_values=v_arr.to(units['velocity']).magnitude
        )
        i += 1
    vp.x1.add_title(f"time ({pint.Unit(units['time']):~P})")
    vp.y1.add_title(f"velocity ({pint.Unit(units['velocity']):~P})")
    return vp


def draw_position_profiles(
    profiles: list[tuple[Quantity, Quantity]],
    units: dict[str, str] | None = None
) -> LineChart:
    """Given a list of position profiles (as returned from
    `MotionProfile.position_profile()`), draws them on a `LineChart` object and
    returns this object.

    Parameter `units` can be dictionary with the units that need to be used
    for drawing the charts. The default dictionary (when parameter `units` is
    left to `None`) is:
    ```
    default_units = {
        'time': 's',
        'position': 'm',
        'velocity': 'm / s',
        'acceleration': 'm / s**2'
    }
    ```
    To change any of the default units, it suffices to pass a dictionary with
    the appropriate keys and the desired units. E.g. to only change the units of
    velocity to 'in / s' (instead of 'm / s'), pass a dict to parameter `units`
    defined as `{'velocity': 'in / s'}`.
    """
    units = _set_units(units)
    pp = LineChart()
    i = 0
    for t_arr, s_arr in profiles:
        pp.add_xy_data(
            label=f'position profile {i + 1}',
            x1_values=t_arr.to(units['time']).magnitude,
            y1_values=s_arr.to(units['position']).magnitude
        )
        i += 1
    pp.x1.add_title(f"time ({pint.Unit(units['time']):~P})")
    pp.y1.add_title(f"position ({pint.Unit(units['position']):~P})")
    return pp


def draw_acceleration_profiles(
    profiles: list[tuple[Quantity, Quantity]],
    units: dict[str, str] | None = None
) -> LineChart:
    """Given a list of acceleration profiles (as returned from
    `MotionProfile.acceleration_profile()`), draws them on a `LineChart` object
    and returns this object.

    Parameter `units` can be dictionary with the units that need to be used
    for drawing the charts. The default dictionary (when parameter `units` is
    left to `None`) is:
    ```
    default_units = {
        'time': 's',
        'position': 'm',
        'velocity': 'm / s',
        'acceleration': 'm / s**2'
    }
    ```
    To change any of the default units, it suffices to pass a dictionary with
    the appropriate keys and the desired units. E.g. to only change the units of
    velocity to 'in / s' (instead of 'm / s'), pass a dict to parameter `units`
    defined as `{'velocity': 'in / s'}`.
    """
    units = _set_units(units)
    ap = LineChart()
    i = 0
    for t_arr, a_arr in profiles:
        ap.add_xy_data(
            label=f'acceleration profile {i + 1}',
            x1_values=t_arr.to(units['time']).magnitude,
            y1_values=a_arr.to(units['acceleration']).magnitude
        )
        i += 1
    ap.x1.add_title(f"time ({pint.Unit(units['time']):~P})")
    ap.y1.add_title(f"acceleration ({pint.Unit(units['acceleration']):~P})")
    return ap
