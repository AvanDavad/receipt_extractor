import numpy as np
import cv2
from PIL import Image
from pathlib import Path
import json
from scipy.optimize import least_squares

np.set_printoptions(suppress=True, precision=3)

def get_obj_points(height):
    objp = np.array([[0, 0, 0], [9, 0, 0], [55, 0, 0], [64, 0, 0], [0, height, 0], [64, height, 0]])
    return objp

def decode_x(x):
    rvec = x[0:3]
    tvec = x[3:6]
    height = x[6]
    obj_pts = get_obj_points(height)
    return rvec, tvec, height, obj_pts

def residual_function(x, gt_points, camera_matrix, dist_coeffs):
    rvec, tvec, _, obj_pts = decode_x(x)

    img_pts, _ = cv2.projectPoints(obj_pts, rvec, tvec, camera_matrix, dist_coeffs)
    img_pts = img_pts.reshape(-1, 2)

    return (img_pts - gt_points).flatten()

def warp_perspective(img, img_pts, camera_matrix, dist_coeffs, scale_factor=10.0, verbose=True):

    assert img_pts.shape == (6, 2), f"img_pts.shape is {img_pts.shape}, expected (6, 2)"
    ret = least_squares(
        fun=residual_function,
        x0=np.array([-0.1, 0.1, 0.1, -10, -10, 100.0, 50.0]),
        jac="3-point",
        args=(img_pts, camera_matrix, dist_coeffs),
    )
    assert ret.success, f"least_squares failed with message: {ret.message}"

    rvec, tvec, height, obj_pts = decode_x(ret.x)
    if verbose:
        print(f"rotation vector: {rvec}")
        print(f"translation vector: {tvec}")
        print(f"height: {height}")

    img_pts, _ = cv2.projectPoints(obj_pts, rvec, tvec, camera_matrix, dist_coeffs)

    dst = obj_pts[[0,3,4,5], :2].astype(np.float32)*scale_factor
    dst += np.array([5., 5.]) * scale_factor

    dst_width = int(dst[:, 0].max() + 5*scale_factor)
    dst_height = int(dst[:, 1].max() + 20*scale_factor)

    M = cv2.getPerspectiveTransform(img_pts[[0,3,4,5],0,:].astype(np.float32), dst)

    src_img = np.array(img)
    out = cv2.warpPerspective(src_img, M, (dst_width, dst_height))
    out_img = Image.fromarray(out)

    new_img_pts = cv2.perspectiveTransform(img_pts.reshape(-1, 1, 2), M).reshape(-1, 2)
    return out_img, new_img_pts, M

