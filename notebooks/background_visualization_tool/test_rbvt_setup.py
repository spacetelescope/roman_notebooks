"""Offline regression tests; run with python -m unittest test_rbvt_setup."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
import requests

import rbt
import rbvt_notebook


class ReferenceDataTests(unittest.TestCase):
    def test_bundled_data_preserves_values(self):
        wave, thermal_wave, flux = rbt.validate_reference_data()
        refdata = Path(rbt.__file__).parent / "refdata"
        expected = np.loadtxt(refdata / rbt.get_remote_data("thermal_file"), delimiter=",")
        np.testing.assert_array_equal(thermal_wave, expected[:, 0])
        np.testing.assert_array_equal(flux, expected[:, 1])
        self.assertEqual(wave.ndim, 1)

    def test_invalid_thermal_files(self):
        with tempfile.TemporaryDirectory() as folder:
            thermal = Path(folder) / "thermal.csv"
            for contents in ["0.5\n0.6\n0.7\n", "0.5,1\n", "0.5,nan\n0.6,1\n",
                             "0.6,1\n0.5,2\n", "0.5,1,2\n0.6,2,3\n", "bad data"]:
                with self.subTest(contents=contents):
                    thermal.write_text(contents)
                    with self.assertRaisesRegex(ValueError, "Restore the refdata files"):
                        rbt.validate_reference_data(thermal_path=thermal)
            with self.assertRaisesRegex(ValueError, "Cannot read reference file"):
                rbt.validate_reference_data(thermal_path=Path(folder) / "missing.csv")

    def test_configuration_controls_cache_and_pixel_ordering(self):
        with patch.object(rbt, "_CACHE", {"cache_dir": "https://example.test/cache/",
                                         "cache_version": "test-release"}), \
                patch.object(rbt, "_HEALPIX", {"nside": 64, "ordering": "NESTED"}), \
                patch.object(rbt.background, "read_bkg_data_from_url", return_value={}), \
                patch.object(rbt.background, "make_bathtub"), \
                patch.object(rbt.healpy.pixelfunc, "ang2pix", return_value=123) as pixel:
            model = rbt.background(10, 20, 1.0)
            self.assertEqual(model.remote_dir, "https://example.test/cache/")
            self.assertEqual(model.cache_version, "test-release")
            pixel.assert_called_once_with(64, 10, 20, nest=True, lonlat=True)


class NotebookConnectionTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_explicit_origin(self):
        self.assertEqual(rbvt_notebook.notebook_show_options("http://localhost:8890"),
                         {"notebook_url": "http://localhost:8890"})
        with self.assertRaises(ValueError):
            rbvt_notebook.notebook_show_options("http://localhost:8890/?token=secret")

    def test_hub_configuration_is_preserved(self):
        os.environ["JUPYTER_BOKEH_EXTERNAL_URL"] = "https://nexus.example.test"
        self.assertEqual(rbvt_notebook.notebook_show_options(), {})

    def test_matches_kernel_among_multiple_servers(self):
        servers = [{"url": "http://localhost:8888/", "token": "first"},
                   {"url": "http://localhost:8890/base/", "token": "second"}]
        responses = [Mock(json=Mock(return_value=[{"kernel": {"id": "other"}}])),
                     Mock(json=Mock(return_value=[{"kernel": {"id": "active"}}]))]
        with patch.object(rbvt_notebook, "get_connection_file", return_value="kernel-active.json"), \
                patch.object(rbvt_notebook, "list_running_servers", return_value=servers), \
                patch.object(rbvt_notebook.requests, "get", side_effect=responses) as get:
            self.assertEqual(rbvt_notebook.notebook_show_options(),
                             {"notebook_url": "http://localhost:8890"})
            self.assertEqual(get.call_args.args[0], "http://localhost:8890/base/api/sessions")
            self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "token second"})

    def test_unavailable_server_gives_manual_instructions(self):
        with patch.object(rbvt_notebook, "get_connection_file", return_value="kernel-active.json"), \
                patch.object(rbvt_notebook, "list_running_servers",
                             return_value=[{"url": "http://localhost:8888/"}]), \
                patch.object(rbvt_notebook.requests, "get", side_effect=requests.Timeout):
            with self.assertRaisesRegex(RuntimeError, "Set NOTEBOOK_URL"):
                rbvt_notebook.notebook_show_options()


if __name__ == "__main__":
    unittest.main()
