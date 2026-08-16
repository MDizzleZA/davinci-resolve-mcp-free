"""Routing tests for the consolidated grouped tools.

Mocks _get/_post to capture which bridge endpoint each (group, action) hits,
proving the dispatch table wires every action to the right implementation
without needing a live bridge.
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import resolve_mcp_bridge as rb  # noqa: E402


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self._g = mock.patch.object(
            rb, "_get", side_effect=lambda ep, params=None: self.calls.append(("GET", ep)) or {"ok": 1})
        self._p = mock.patch.object(
            rb, "_post", side_effect=lambda ep, body=None: self.calls.append(("POST", ep)) or {"ok": 1})
        self._g.start()
        self._p.start()

    def tearDown(self):
        self._g.stop()
        self._p.stop()

    def _last_ep(self):
        return self.calls[-1][1] if self.calls else None

    def test_every_action_target_is_callable(self):
        for group, actions in rb._GROUP_TABLES.items():
            for action, fn in actions.items():
                self.assertTrue(callable(fn), f"{group}.{action} not callable")

    def test_routes_to_correct_endpoint(self):
        cases = [
            (rb.resolve, {"action": "status"}, "/status"),
            (rb.resolve, {"action": "open_page", "page": "edit"}, "/page"),
            (rb.resolve, {"action": "layout_preset", "preset_action": "load", "preset_name": "p"},
             "/resolve/layout-preset"),
            (rb.project, {"action": "save"}, "/project/save"),
            (rb.project, {"action": "load", "project_name": "X"}, "/projects/load"),
            (rb.project, {"action": "navigate_folder", "folder_action": "open", "folder_name": "f"},
             "/projects/folder"),
            (rb.media_pool, {"action": "get"}, "/mediapool"),
            (rb.media_pool, {"action": "import", "file_paths": ["a.mp4"]}, "/media/import"),
            (rb.media_pool, {"action": "storage_reveal", "path": "C:/x"}, "/media-storage/reveal"),
            (rb.timeline, {"action": "create", "name": "T"}, "/timeline/create"),
            (rb.timeline, {"action": "clips", "track_type": "video", "track_index": 1}, "/timeline/clips"),
            (rb.timeline, {"action": "playhead", "timecode": "01:00:00:00"}, "/playhead"),
            (rb.timeline_edit, {"action": "insert", "clip_name": "c", "record_frame": 0}, "/media/insert"),
            (rb.timeline_edit, {"action": "append", "clip_name": "c"}, "/media/append"),
            (rb.tracks, {"action": "add", "track_type": "audio"}, "/track/add"),
            (rb.clip, {"action": "properties_set", "track_type": "video", "track_index": 1,
                       "clip_index": 0, "properties": {"Pan": 1}}, "/clip/properties"),
            (rb.markers, {"action": "timeline_add", "frameId": 10}, "/marker/add"),
            (rb.takes, {"action": "get", "track_type": "video", "track_index": 1, "clip_index": 0},
             "/clip/takes"),
            (rb.color, {"action": "set_cdl", "track_type": "video", "track_index": 1, "clip_index": 0,
                        "cdl": {"NodeIndex": "1"}}, "/color/set-cdl"),
            (rb.color_groups, {"action": "list"}, "/color/groups"),
            (rb.gallery, {"action": "albums"}, "/gallery/albums"),
            (rb.fusion, {"action": "comps", "track_type": "video", "track_index": 1, "clip_index": 0},
             "/clip/fusion-comps"),
            (rb.fairlight, {"action": "presets"}, "/fairlight/presets"),
            (rb.render, {"action": "start"}, "/render/start"),
            (rb.render, {"action": "preset", "preset_action": "save", "preset_name": "p"},
             "/render/preset"),
            (rb.metadata, {"action": "export_frame", "file_path": "x.png"}, "/project/export-frame"),
        ]
        for fn, kw, ep in cases:
            self.calls.clear()
            fn(**kw)
            self.assertEqual(self._last_ep(), ep, f"{fn.__name__}({kw}) -> {self._last_ep()} != {ep}")

    def test_extra_params_are_filtered(self):
        # track_index is irrelevant to create; it must be dropped, not error.
        self.calls.clear()
        rb.timeline(action="create", name="T", track_index=99)
        self.assertEqual(self._last_ep(), "/timeline/create")

    def test_unknown_action_errors(self):
        out = rb.timeline(action="does-not-exist")
        self.assertIn("error", out)
        self.assertEqual(self.calls, [])

    def test_ai_local_list_jobs_no_endpoint(self):
        out = rb.ai_local(action="list_jobs")
        self.assertIn("jobs", out)


if __name__ == "__main__":
    unittest.main()
