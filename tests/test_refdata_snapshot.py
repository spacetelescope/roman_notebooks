"""Small offline fixtures exercise the same bytes/parts/install path as releases."""

import copy
import functools
import http.server
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import patch

import yaml

from shared import notebook_data_dependencies as ndd
from shared import refdata_snapshot as snapshot


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.tar.gz"
        with tarfile.open(self.source, "w:gz") as archive:
            item = tarfile.TarInfo("fixture/data.txt")
            content = b"reference data" * 50
            item.size = len(content)
            archive.addfile(item, io.BytesIO(content))
        self.manifest = self.root / "dependencies.yaml"
        definition = dict(version="2026.1", data_url=["https://upstream.invalid/data.gz"],
                          environment_variable="ROMAN_TEST_DATA", install_path=str(self.root / "installed"),
                          data_path="fixture")
        self.document = dict(install_files={"pandeia_data": definition,
                                           "pandeia_psf": copy.deepcopy(definition)},
                             other_variables={"ROMAN_TEST_OTHER": "${HOME}/test"},
                             remote_data={"example": {"url": "https://example.invalid"}})
        self.manifest.write_text(yaml.safe_dump(self.document), encoding="utf-8")
        self.assets = self.root / "assets"
        self.environment = patch.dict(os.environ)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        for key in ("ROMAN_TEST_DATA", "ROMAN_TEST_OTHER", "ROMAN_REFDATA_MANIFEST"):
            os.environ.pop(key, None)

    def prepare(self, part_size=32):
        with patch.object(snapshot, "download", side_effect=lambda url, target: shutil.copyfile(self.source, target)):
            return snapshot.prepare(self.manifest, self.assets, "mgough-970/roman_notebooks", "2026.1.2",
                                    part_size=part_size)

    def test_split_verify_install_and_environment(self):
        lock_path = self.prepare()
        lock = snapshot.load_lock(lock_path)
        self.assertEqual(set(lock["install_files"]), {"pandeia_data", "pandeia_psf"})
        archive = lock["install_files"]["pandeia_data"]["archives"][0]
        self.assertGreater(len(archive["parts"]), 1)
        snapshot.verify(lock_path, self.assets)
        urls = []

        def fetch(url, target):
            urls.append(url)
            shutil.copyfile(self.assets / url.rsplit("/", 1)[-1], target)

        with patch.object(snapshot, "download", side_effect=fetch):
            result = ndd.install_files(lock_path, verbose=False, packages=["pandeia_data"])
        self.assertEqual((self.root / "installed/fixture/data.txt").read_bytes(), b"reference data" * 50)
        self.assertTrue(all("/releases/download/2026.1.2/" in url for url in urls))
        self.assertFalse(result["ROMAN_TEST_DATA"]["pre_installed"])
        ndd.setup_env(result, dependencies=lock_path, verbose=False)
        self.assertEqual(os.environ["ROMAN_TEST_DATA"], result["ROMAN_TEST_DATA"]["path"])
        self.assertTrue(os.environ["ROMAN_TEST_OTHER"].endswith("/test"))
        with patch.object(snapshot, "download", side_effect=AssertionError("must skip preinstalled")):
            self.assertTrue(ndd.install_files(lock_path, verbose=False, packages="pandeia_data")
                            ["ROMAN_TEST_DATA"]["pre_installed"])
        self.assertEqual(ndd.get_remote_data("example", lock_path), self.document["remote_data"]["example"])

    def test_unsplit(self):
        path = self.prepare(part_size=1024**2)
        snapshot.verify(path, self.assets)
        archive = snapshot.load_lock(path)["install_files"]["pandeia_data"]["archives"][0]
        self.assertEqual(len(archive["parts"]), 1)
        self.assertEqual(archive["name"], archive["parts"][0]["name"])

    def test_corrupt_part_rejected_before_extraction_and_cleaned_up(self):
        path = self.prepare()
        lock = snapshot.load_lock(path)
        part = lock["install_files"]["pandeia_data"]["archives"][0]["parts"][0]
        target = self.assets / part["name"]
        target.write_bytes(b"x" * part["size"])
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            snapshot.verify(path, self.assets)
        with patch.object(snapshot, "download", side_effect=lambda url, target: shutil.copyfile(self.assets / url.rsplit("/", 1)[-1], target)):
            with patch.object(tarfile, "open", side_effect=AssertionError("must not extract")):
                with self.assertRaises(ValueError):
                    ndd.install_files(path, verbose=False, packages="pandeia_data")
        self.assertEqual(list((self.root / "installed").iterdir()), [])

    def test_whole_archive_digest_is_checked(self):
        path = self.prepare()
        lock = snapshot.load_lock(path)
        lock["install_files"]["pandeia_data"]["archives"][0]["sha256"] = "0" * 64
        path.write_text(json.dumps(lock))
        with self.assertRaises(ValueError):
            snapshot.verify(path, self.assets)

    def test_missing_part_and_unknown_package(self):
        path = self.prepare()
        with self.assertRaisesRegex(ValueError, "absent"):
            ndd.install_files(path, packages=["synphot"])
        next(self.assets.glob("*.part*")).unlink()
        with self.assertRaises(FileNotFoundError):
            snapshot.verify(path, self.assets)

    def test_development_yaml_override(self):
        self.prepare()
        os.environ["ROMAN_REFDATA_MANIFEST"] = str(self.manifest)
        with patch.object(snapshot, "download", side_effect=lambda url, target: shutil.copyfile(self.source, target)) as fetch:
            ndd.install_files(packages=["pandeia_data"], verbose=False)
        self.assertEqual(fetch.call_args.args[0], "https://upstream.invalid/data.gz")

    def test_lock_resolution_and_invalid_lock_no_fallback(self):
        path = self.prepare()
        with patch.object(ndd, "__file__", str(self.root / "shared/notebook_data_dependencies.py")):
            shutil.copyfile(path, self.root / "refdata-lock.json")
            shutil.copyfile(self.manifest, self.root / "refdata_dependencies.yaml")
            self.assertTrue(ndd._resolve_dependencies().endswith("refdata-lock.json"))
            (self.root / "refdata-lock.json").write_text('{"schema_version": 99}')
            with self.assertRaises(ValueError):
                ndd.install_files(packages="pandeia_data")
            self.assertEqual(ndd._resolve_dependencies(self.manifest), str(self.manifest))

    def test_validation_and_stale_output(self):
        with self.assertRaises(ValueError):
            snapshot.prepare(self.manifest, self.assets, "owner/repo", "test", part_size=2**31)
        with self.assertRaises(ValueError):
            snapshot.prepare(self.manifest, self.assets, "owner/repo", "test", packages=["typo"])
        path = self.prepare()
        with self.assertRaises(ValueError):
            self.prepare()
        lock = snapshot.load_lock(path)
        lock["install_files"]["pandeia_data"]["archives"][0]["parts"][0]["name"] = "../escape"
        path.write_text(json.dumps(lock))
        with self.assertRaises(ValueError):
            snapshot.load_lock(path)

    def test_http_download_preserves_archive_bytes(self):
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(self.root))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            target = self.root / "downloaded"
            snapshot.download(f"http://127.0.0.1:{server.server_port}/{self.source.name}", target)
            self.assertEqual(target.read_bytes(), self.source.read_bytes())
            for definition in self.document["install_files"].values():
                definition["data_url"] = [f"http://127.0.0.1:{server.server_port}/{self.source.name}"]
            self.manifest.write_text(yaml.safe_dump(self.document), encoding="utf-8")
            subprocess.run([
                sys.executable, "-m", "shared.refdata_snapshot", "prepare",
                "--manifest", str(self.manifest), "--output", str(self.assets),
                "--repository", "owner/repo", "--release", "test", "--part-size", "32",
            ], check=True)
            subprocess.run([
                sys.executable, "-m", "shared.refdata_snapshot", "verify",
                "--lock", str(self.assets / "refdata-lock.json"), "--assets", str(self.assets),
            ], check=True)
            with self.assertRaises(Exception):
                snapshot.download(f"http://127.0.0.1:{server.server_port}/missing", target)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_multiple_archives_and_explicit_scope(self):
        self.document["install_files"]["synphot"] = copy.deepcopy(self.document["install_files"]["pandeia_data"])
        self.document["install_files"]["synphot"]["data_url"] *= 2
        self.manifest.write_text(yaml.safe_dump(self.document), encoding="utf-8")
        with patch.object(snapshot, "download", side_effect=lambda url, target: shutil.copyfile(self.source, target)):
            path = snapshot.prepare(self.manifest, self.assets, "owner/repo", "test", packages=["synphot"])
        lock = snapshot.load_lock(path)
        self.assertEqual(set(lock["install_files"]), {"synphot"})
        self.assertEqual(len(lock["install_files"]["synphot"]["archives"]), 2)
        snapshot.verify(path, self.assets)

    def test_http_200_non_archive_rejected(self):
        with patch.object(snapshot, "download", side_effect=lambda url, target: Path(target).write_bytes(b"<html>error</html>")):
            path = snapshot.prepare(self.manifest, self.assets, "owner/repo", "test")
        with self.assertRaises(tarfile.ReadError):
            snapshot.verify(path, self.assets)

    def test_stpsf_stips_repository_definitions_install_and_setup_env(self):
        """The new release datasets retain their real directory/env conventions."""
        repository = Path(__file__).resolve().parents[1]
        document = yaml.safe_load((repository / "refdata_dependencies.yaml").read_text())
        packages = ["stpsf", "stips"]
        definitions = {name: document["install_files"][name] for name in packages}
        document["install_files"] = definitions
        self.manifest.write_text(yaml.safe_dump(document), encoding="utf-8")
        os.environ["HOME"] = str(self.root / "home")
        sources = {}
        for package, definition in definitions.items():
            os.environ.pop(definition["environment_variable"], None)
            path = self.root / f"{package}.tgz"
            with tarfile.open(path, "w:gz") as archive:
                member = tarfile.TarInfo(f"{definition['data_path']}/fixture.txt")
                data = package.encode()
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
            sources[definition["data_url"][0]] = path
        with patch.object(snapshot, "download", side_effect=lambda url, target: shutil.copyfile(sources[url], target)):
            path = snapshot.prepare(self.manifest, self.assets, "owner/repo", "next-release", packages=packages)
        snapshot.verify(path, self.assets)
        lock = snapshot.load_lock(path)
        self.assertEqual(set(lock["install_files"]), set(packages))
        for package in packages:
            self.assertEqual(lock["install_files"][package]["version"], definitions[package]["version"])
        os.environ["ROMAN_REFDATA_MANIFEST"] = str(path)

        def fetch(url, target):
            self.assertIn("/releases/download/next-release/", url)
            shutil.copyfile(self.assets / url.rsplit("/", 1)[-1], target)

        with patch.object(snapshot, "download", side_effect=fetch):
            result = ndd.install_files(packages=packages, verbose=False)
        for key in document.get("other_variables", {}):
            os.environ.pop(key, None)
        ndd.setup_env(result, verbose=False)
        self.assertEqual(set(result), {"STPSF_PATH", "stips_data"})
        for package, definition in definitions.items():
            expected = self.root / "home/refdata" / definition["data_path"]
            variable = definition["environment_variable"]
            self.assertEqual(Path(os.environ[variable]), expected)
            self.assertEqual((expected / "fixture.txt").read_text(), package)
            self.assertFalse(result[variable]["pre_installed"])

    def test_reassembly_removes_each_part_before_fetching_the_next(self):
        path = self.prepare(part_size=32)
        archive = snapshot.load_lock(path)["install_files"]["pandeia_data"]["archives"][0]

        def fetch(part, target):
            self.assertEqual(list(target.parent.iterdir()), [])
            shutil.copyfile(self.assets / part["name"], target)

        destination = self.root / "joined.tar.gz"
        snapshot.assemble(archive, destination, fetch)
        self.assertEqual(destination.read_bytes(), self.source.read_bytes())

    def test_synphot_nine_archives_share_one_installation_and_environment(self):
        repository = Path(__file__).resolve().parents[1]
        document = yaml.safe_load((repository / "refdata_dependencies.yaml").read_text())
        definition = document["install_files"]["synphot"]
        document["install_files"] = {"synphot": definition}
        urls = definition["data_url"]
        self.assertEqual(len(urls), 9)
        sources = {}
        files = ["mtab/graph.fits", "grid/bz77/model.fits", "grid/ck04models/catalog.fits",
                 "grid/k93models/catalog.fits", "grid/phoenix/catalog.fits",
                 "calspec/alpha_lyr_stis_011.fits", "grid/etc_models/model.fits",
                 "mtab/throughput.fits", "grid/pickles/model.fits"]
        for index, (url, name) in enumerate(zip(urls, files), 1):
            source = self.root / f"synphot-{index}.tar"
            with tarfile.open(source, "w") as archive:
                data = f"fixture {index}".encode()
                member = tarfile.TarInfo(f"{definition['data_path']}/{name}")
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
            sources[url] = source
        self.manifest.write_text(yaml.safe_dump(document), encoding="utf-8")
        with patch.object(snapshot, "download", side_effect=lambda url, target: shutil.copyfile(sources[url], target)):
            path = snapshot.prepare(self.manifest, self.assets, "owner/repo", "synphot-test",
                                    packages=["synphot"], part_size=4096)
        lock = snapshot.load_lock(path)
        self.assertEqual(len(lock["install_files"]["synphot"]["archives"]), 9)
        snapshot.verify(path, self.assets)
        os.environ["HOME"] = str(self.root / "home")
        os.environ["ROMAN_REFDATA_MANIFEST"] = str(path)
        os.environ.pop("PYSYN_CDBS", None)
        downloads = []

        def fetch(url, target):
            self.assertIn("/releases/download/synphot-test/", url)
            downloads.append(url)
            shutil.copyfile(self.assets / url.rsplit("/", 1)[-1], target)

        with patch.object(snapshot, "download", side_effect=fetch):
            result = ndd.install_files(packages=["synphot"], verbose=False)
        self.assertEqual(set(result), {"PYSYN_CDBS"})
        self.assertFalse(result["PYSYN_CDBS"]["pre_installed"])
        expected = self.root / "home/refdata" / definition["data_path"]
        for index, name in enumerate(files, 1):
            self.assertEqual((expected / name).read_text(), f"fixture {index}")
        ndd.setup_env(result, verbose=False)
        self.assertEqual(Path(os.environ["PYSYN_CDBS"]), expected)
        self.assertEqual(len(downloads), sum(len(a["parts"]) for a in lock["install_files"]["synphot"]["archives"]))
        with patch.object(snapshot, "download", side_effect=AssertionError("must skip")):
            self.assertTrue(ndd.install_files(packages="synphot", verbose=False)["PYSYN_CDBS"]["pre_installed"])


if __name__ == "__main__":
    unittest.main()
