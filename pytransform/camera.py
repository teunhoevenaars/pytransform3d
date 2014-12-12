import numpy as np
from .transformations import invert_transform, transform


def make_world_grid(n_lines=11, n_points_per_line=51, xlim=(-0.5, 0.5),
                    ylim=(-0.5, 0.5)):
    """Generate grid in world coordinate frame.

    The grid will have the form

    .. code::

        +----+----+----+----+----+
        |    |    |    |    |    |
        +----+----+----+----+----+
        |    |    |    |    |    |
        +----+----+----+----+----+
        |    |    |    |    |    |
        +----+----+----+----+----+
        |    |    |    |    |    |
        +----+----+----+----+----+
        |    |    |    |    |    |
        +----+----+----+----+----+

    on the x-y plane with z=0 for all points.

    Parameters
    ----------
    n_lines : int, optional (default: 11)
        Number of lines

    n_points_per_line : int, optional (default: 51)
        Number of points per line

    xlim : tuple, optional (default: (-0.5, 0.5))
        Range on x-axis

    ylim : tuple, optional (default: (-0.5, 0.5))
        Range on y-axis

    Returns
    -------
    world_grid : array-like, shape (2 * n_lines * n_points_per_line, 4)
        Grid as homogenous coordinate vectors
    """
    world_grid_x = np.vstack([make_world_line([xlim[0], y], [xlim[1], y],
                                              n_points_per_line)
                              for y in np.linspace(ylim[0], ylim[1], n_lines)])
    world_grid_y = np.vstack([make_world_line([x, ylim[0]], [x, ylim[1]],
                                              n_points_per_line)
                              for x in np.linspace(xlim[0], xlim[1], n_lines)])
    return np.vstack((world_grid_x, world_grid_y))


def make_world_line(p1, p2, n_points):
    """Generate line in world coordinate frame.

    Parameters
    ----------
    p1 : array-like, shape (2 or 3,)
        Start point of the line

    p2 : array-like, shape (2 or 3,)
        End point of the line

    n_points : int
        Number of points

    Returns
    -------
    line : array-like, shape (n_points, 4)
        Samples from line in world frame
    """
    if len(p1) == 2:
        p1 = [p1[0], p1[1], 0]
    if len(p2) == 2:
        p2 = [p2[0], p2[1], 0]
    return np.array([np.linspace(p1[0], p2[0], n_points),
                     np.linspace(p1[1], p2[1], n_points),
                     np.linspace(p1[2], p2[2], n_points),
                     np.ones(n_points)]).T


def cam2sensor(P_cam, focal_length, kappa=0.0):
    """Project points from 3D camera coordinate system to sensor plane.

    TODO document me
    """
    P_sensor = P_cam[:, :2] / P_cam[:, 2, np.newaxis]
    for n in range(P_sensor.shape[0]):
        P_sensor[n] *= 1.0 / (1.0 + kappa * np.linalg.norm(P_sensor[n]) ** 2)
    P_sensor *= focal_length
    return P_sensor


def sensor2img(P_sensor, sensor_size, image_size, image_center=None):
    """Project points from 2D sensor plane to image coordinate system.

    TODO document me
    """
    P_img = np.asarray(image_size) * P_sensor / np.asarray(sensor_size)
    if image_center is None:
        image_center = np.asarray(image_size) / 2
    P_img += np.asarray(image_center)
    return P_img


def world2image(P_world, cam2world, sensor_size, image_size, focal_length,
                image_center=None, kappa=0.0):
    """Project points from 3D world coordinate system to 2D image.

    TODO document me
    """
    world2cam = invert_transform(cam2world)
    P_cam = transform(world2cam, P_world)
    P_sensor = cam2sensor(P_cam, focal_length, kappa)
    P_img = sensor2img(P_sensor, sensor_size, image_size, image_center)
    return P_img
