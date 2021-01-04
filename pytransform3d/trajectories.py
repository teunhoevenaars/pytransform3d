"""Trajectories in three dimensions (position and orientation)."""
import numpy as np
from .plot_utils import Trajectory, make_3d_axis
from .batch_rotations import norm_vectors, matrices_from_quaternions, quaternions_from_matrices, matrix_from_compact_axis_angles
from .transformations import transform_from_exponential_coordinates


def transforms_from_pqs(P, normalize_quaternions=True):
    """Get sequence of homogeneous matrices from positions and quaternions.

    Parameters
    ----------
    P : array-like, shape (n_steps, 7)
        Sequence of poses represented by positions and quaternions in the
        order (x, y, z, w, vx, vy, vz) for each step

    normalize_quaternions : bool, optional (default: True)
        Normalize quaternions before conversion

    Returns
    -------
    H : array, shape (n_steps, 4, 4)
        Sequence of poses represented by homogeneous matrices
    """
    P = np.asarray(P)
    H = np.empty((len(P), 4, 4))
    H[:, :3, 3] = P[:, :3]
    H[:, 3, :3] = 0.0
    H[:, 3, 3] = 1.0

    if normalize_quaternions:
        Q = norm_vectors(P[:, 3:])
    else:
        Q = P[:, 3:]

    matrices_from_quaternions(Q, out=H[:, :3, :3])

    return H


matrices_from_pos_quat = transforms_from_pqs


def pqs_from_transforms(H):
    """Get sequence of positions and quaternions from homogeneous matrices.

    Parameters
    ----------
    H : array-like, shape (n_steps, 4, 4)
        Sequence of poses represented by homogeneous matrices

    Returns
    -------
    P : array, shape (n_steps, 7)
        Sequence of poses represented by positions and quaternions in the
        order (x, y, z, w, vx, vy, vz) for each step
    """
    H = np.asarray(H)
    P = np.empty((len(H), 7))
    P[:, :3] = H[:, :3, 3]
    quaternions_from_matrices(H[:, :3, :3], out=P[:, 3:])
    return P


def transforms_from_exponential_coordinates(Sthetas):
    """TODO"""
    Sthetas = np.asarray(Sthetas)
    if Sthetas.ndim == 1:
        return transform_from_exponential_coordinates(Sthetas)

    instances_shape = Sthetas.shape[:-1]

    t = np.linalg.norm(Sthetas[..., :3], axis=-1)

    H = np.empty(instances_shape + (4, 4))
    H[..., 3, :] = (0, 0, 0, 1)

    ind_only_translation = t == 0.0

    if not np.all(ind_only_translation):
        t[ind_only_translation] = 1.0
        screw_axes = Sthetas / t[..., np.newaxis]

        matrix_from_compact_axis_angles(axes=screw_axes[..., :3], angles=t, out=H[..., :3, :3])

        # from sympy import *
        # omega0, omega1, omega2, vx, vy, vz, theta = symbols("omega_0 omega_1 omega_2 v_x v_y v_z theta")
        # w = Matrix([[0, -omega2, omega1], [omega2, 0, -omega0], [-omega1, omega0, 0]])
        # v = Matrix([[vx], [vy], [vz]])
        # p = (eye(3) * theta + (1 - cos(theta)) * w + (theta - sin(theta)) * w * w) * v
        #
        # Result:
        # -v_x*(omega_1**2*(theta - sin(theta)) + omega_2**2*(theta - sin(theta)) - theta)
        #     + v_y*(omega_0*omega_1*(theta - sin(theta)) + omega_2*(cos(theta) - 1))
        #     + v_z*(omega_0*omega_2*(theta - sin(theta)) - omega_1*(cos(theta) - 1))
        # v_x*(omega_0*omega_1*(theta - sin(theta)) - omega_2*(cos(theta) - 1))
        #     - v_y*(omega_0**2*(theta - sin(theta)) + omega_2**2*(theta - sin(theta)) - theta)
        #     + v_z*(omega_0*(cos(theta) - 1) + omega_1*omega_2*(theta - sin(theta)))
        # v_x*(omega_0*omega_2*(theta - sin(theta)) + omega_1*(cos(theta) - 1))
        #     - v_y*(omega_0*(cos(theta) - 1) - omega_1*omega_2*(theta - sin(theta)))
        #     - v_z*(omega_0**2*(theta - sin(theta)) + omega_1**2*(theta - sin(theta)) - theta)

        tms = t - np.sin(t)
        cm1 = np.cos(t) - 1.0
        o0 = screw_axes[..., 0]
        o1 = screw_axes[..., 1]
        o2 = screw_axes[..., 2]
        v0 = screw_axes[..., 3]
        v1 = screw_axes[..., 4]
        v2 = screw_axes[..., 5]
        o01tms = o0 * o1 * tms
        o12tms = o1 * o2 * tms
        o02tms = o0 * o2 * tms
        o0cm1 = o0 * cm1
        o1cm1 = o1 * cm1
        o2cm1 = o2 * cm1
        o00tms = o0 * o0 * tms
        o11tms = o1 * o1 * tms
        o22tms = o2 * o2 * tms
        if instances_shape:
            v0 = v0.reshape(*instances_shape)
            v1 = v1.reshape(*instances_shape)
            v2 = v2.reshape(*instances_shape)
        H[..., 0, 3] = (-v0 * (o11tms + o22tms - t)
                        + v1 * (o01tms + o2cm1)
                        + v2 * (o02tms - o1cm1))
        H[..., 1, 3] = (v0 * (o01tms - o2cm1)
                        - v1 * (o00tms + o22tms - t)
                        + v2 * (o0cm1 + o12tms))
        H[..., 2, 3] = (v0 * (o02tms + o1cm1)
                        - v1 * (o0cm1 - o12tms)
                        - v2 * (o00tms + o11tms - t))

    H[ind_only_translation, :3, :3] = np.eye(3)
    H[ind_only_translation, :3, 3] = Sthetas[ind_only_translation, 3:]

    return H


def plot_trajectory(ax=None, P=None, normalize_quaternions=True, show_direction=True, n_frames=10, s=1.0, ax_s=1, **kwargs):
    """Plot pose trajectory.

    Parameters
    ----------
    ax : Matplotlib 3d axis, optional (default: None)
        If the axis is None, a new 3d axis will be created

    P : array-like, shape (n_steps, 7), optional (default: None)
        Sequence of poses represented by positions and quaternions in the
        order (x, y, z, w, vx, vy, vz) for each step

    normalize_quaternions : bool, optional (default: True)
        Normalize quaternions before plotting

    show_direction : bool, optional (default: True)
        Plot an arrow to indicate the direction of the trajectory

    n_frames : int, optional (default: 10)
        Number of frames that should be plotted to indicate the rotation

    s : float, optional (default: 1)
        Scaling of the frames that will be drawn

    ax_s : float, optional (default: 1)
        Scaling of the new matplotlib 3d axis

    kwargs : dict, optional (default: {})
        Additional arguments for the plotting functions, e.g. alpha

    Returns
    -------
    ax : Matplotlib 3d axis
        New or old axis
    """
    if P is None or len(P) == 0:
        raise ValueError("Trajectory does not contain any elements.")

    if ax is None:
        ax = make_3d_axis(ax_s)

    H = transforms_from_pqs(P, normalize_quaternions)
    trajectory = Trajectory(H, show_direction, n_frames, s, **kwargs)
    trajectory.add_trajectory(ax)

    return ax
