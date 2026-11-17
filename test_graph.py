import os
import subprocess
import unittest
from unittest import mock

import graph


def result(code=0, out="", err=""):
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=out, stderr=err)


class CallTests(unittest.TestCase):
    def setUp(self):
        p = mock.patch("graph.az_cmd", return_value=["az"])
        p.start()
        self.addCleanup(p.stop)

    def test_missing_object_is_none(self):
        with mock.patch("subprocess.run", return_value=result(1, err="ERROR: Not Found({...})")):
            self.assertIsNone(graph.get("/users/nobody@lab"))

    def test_free_tenant_premium_report_is_none(self):
        err = 'ERROR: Forbidden({"error":{"code":"Authentication_RequestFromNonPremiumTenantOrB2CTenant"}})'
        with mock.patch("subprocess.run", return_value=result(1, err=err)):
            self.assertIsNone(graph.get("/reports/authenticationMethods/userRegistrationDetails"))

    def test_other_errors_stop(self):
        with mock.patch("subprocess.run", return_value=result(1, err="ERROR: Forbidden(scope missing)")):
            with self.assertRaises(SystemExit):
                graph.get("/identityProtection/riskyUsers")

    def test_delete_with_no_body_returns_empty(self):
        with mock.patch("subprocess.run", return_value=result(0, out="")):
            self.assertEqual(graph.call("delete", "/x"), {})

    def test_body_file_removed_even_when_call_fails(self):
        seen = {}

        def fake_run(cmd, **kw):
            seen["path"] = cmd[cmd.index("--body") + 1][1:]
            self.assertTrue(os.path.exists(seen["path"]))
            return result(1, err="ERROR: Bad Request")

        with mock.patch("subprocess.run", side_effect=fake_run):
            with self.assertRaises(SystemExit):
                graph.post("/users", {"displayName": 'has "quotes" & ampersand'})
        self.assertFalse(os.path.exists(seen["path"]))


class GetAllTests(unittest.TestCase):
    def test_follows_next_link(self):
        pages = [
            {"value": [1, 2], "@odata.nextLink": graph.GRAPH + "/users?$skiptoken=abc"},
            {"value": [3]},
        ]
        with mock.patch("graph.get", side_effect=pages) as get:
            self.assertEqual(graph.get_all("/users"), [1, 2, 3])
        self.assertEqual(get.call_args_list[1].args[0], "/users?$skiptoken=abc")

    def test_missing_collection_is_empty(self):
        with mock.patch("graph.get", return_value=None):
            self.assertEqual(graph.get_all("/groups/x/members"), [])


class AzCmdTests(unittest.TestCase):
    def test_windows_msi_uses_bundled_python(self):
        az = os.path.join("C:\\", "cli", "wbin", "az.cmd")
        py = os.path.join("C:\\", "cli", "python.exe")
        with mock.patch("shutil.which", return_value=az), mock.patch("os.path.exists", return_value=True):
            self.assertEqual(graph.az_cmd(), [py, "-IBm", "azure.cli"])

    def test_no_cli_stops(self):
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaises(SystemExit):
                graph.az_cmd()


if __name__ == "__main__":
    unittest.main()
