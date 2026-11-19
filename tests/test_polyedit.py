import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from polyedit import (edge_map, grabcut_polygon, nearest_vertex, point_in_polygon,  # noqa: E402
                      refresh_bbox, snap_to_edge)


def test_point_in_polygon_square():
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert point_in_polygon(sq, 5, 5)
    assert not point_in_polygon(sq, 15, 5)


def test_nearest_vertex_within_tolerance_only():
    pts = [(0, 0), (10, 0), (10, 10)]
    assert nearest_vertex(pts, 1, 1, tol=3) == 0
    assert nearest_vertex(pts, 5, 5, tol=3) is None


def test_refresh_bbox_matches_points():
    e = [0, 0, 0, 0, 0, [0.1, 0.1, 0.5, 0.1, 0.5, 0.3, 0.1, 0.3]]
    refresh_bbox(e)
    assert abs(e[1] - 0.3) < 1e-9 and abs(e[2] - 0.2) < 1e-9
    assert abs(e[3] - 0.4) < 1e-9 and abs(e[4] - 0.2) < 1e-9


def test_snap_moves_point_onto_edge():
    img = np.zeros((100, 100, 3), np.uint8)
    cv2.rectangle(img, (40, 40), (60, 60), (255, 255, 255), 2)
    edges = edge_map(img)
    sx, sy = snap_to_edge(edges, 42, 50, radius=8)
    assert abs(sx - 40) <= 2 or abs(sx - 41) <= 2


def test_grabcut_finds_bright_disc():
    img = np.full((200, 200, 3), 60, np.uint8)
    cv2.circle(img, (100, 100), 50, (230, 230, 230), -1)
    pts = grabcut_polygon(img, (40, 40, 120, 120))
    assert pts is not None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    assert 45 <= min(xs) <= 55 and 145 <= max(xs) <= 155
    assert 45 <= min(ys) <= 55 and 145 <= max(ys) <= 155


def test_click_grabcut_extracts_clicked_object():
    from polyedit import click_grabcut
    img = np.full((240, 240, 3), 70, np.uint8)
    cv2.circle(img, (120, 120), 60, (235, 235, 235), -1)
    pts = click_grabcut(img, fg_pts=[(120, 120)], bg_pts=[(5, 5)])
    assert pts is not None
    xs = [p[0] for p in pts]
    assert 50 <= min(xs) <= 70 and 170 <= max(xs) <= 190


def test_sam_is_unavailable_without_checkpoint():
    from polyedit import load_sam
    assert load_sam("/nonexistent/sam.pth") is None


def test_click_grabcut_iou_on_large_disc():
    from polyedit import click_grabcut
    img = np.full((400, 600, 3), 60, np.uint8)
    cv2.circle(img, (300, 200), 120, (230, 230, 230), -1)
    gt = np.zeros((400, 600), np.uint8)
    cv2.circle(gt, (300, 200), 120, 255, -1)
    pts = click_grabcut(img, [(300, 200)], [(5, 5)])
    m = np.zeros_like(gt)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 255)
    assert (m & gt).sum() / (m | gt).sum() > 0.9
