# Copyright 2020 Microsoft Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requires Python 2.7+

import os
import subprocess
import unittest
from extension.src.Constants import Constants
from extension.src.EnvLayer import EnvLayer
from extension.src.file_handlers.ExtOutputStatusHandler import ExtOutputStatusHandler
from extension.src.file_handlers.ExtConfigSettingsHandler import ExtConfigSettingsHandler
from extension.src.file_handlers.ExtEnvHandler import ExtEnvHandler
from extension.src.ProcessHandler import ProcessHandler
from extension.tests.helpers.RuntimeComposer import RuntimeComposer
from extension.tests.helpers.VirtualTerminal import VirtualTerminal


class TestProcessHandler(unittest.TestCase):

    def setUp(self):
        VirtualTerminal().print_lowlight("\n----------------- setup test runner -----------------")
        runtime = RuntimeComposer()
        self.logger = runtime.logger
        self.telemetry_writer = runtime.telemetry_writer
        self.logger.telemetry_writer = self.telemetry_writer
        self.utility = runtime.utility
        self.json_file_handler = runtime.json_file_handler
        self.env_layer = runtime.env_layer
        dir_path = os.path.join(os.path.pardir, "tests", "helpers")
        self.ext_output_status_handler = ExtOutputStatusHandler(self.logger, self.utility, self.json_file_handler, dir_path)
        self.process = subprocess.Popen(["echo", "Hello World!"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def tearDown(self):
        VirtualTerminal().print_lowlight("\n----------------- tear down test runner -----------------")
        self.process.kill()

    def mock_is_process_running_to_return_true(self, pid):
        return True

    def mock_os_kill_to_raise_exception(self, pid, sig):
        raise OSError

    def mock_run_command_output_for_python(self, cmd, no_output=False, chk_err=False):
        return 0, "/usr/bin/python"

    def mock_run_command_output_for_python3(self, cmd, no_output=False, chk_err=False):
        return 0, "/usr/bin/python3"

    def mock_run_command_output_for_python_not_found(self, cmd, no_output=False, chk_err=False):
        return 1, "which: no python in test"

    def mock_get_python_cmd(self):
        return "python"

    def mock_run_command_to_set_auto_assess_shell_file_permission(self, cmd, no_output=False, chk_err=False):
        return 0, "permissions set"

    def mock_subprocess_popen_process_not_running_after_launch(self, command, shell, stdout, stderr):
        self.process.pid = 1
        self.process.poll = self.mock_process_poll_return_Not_None
        return self.process

    def mock_subprocess_popen_process_not_launched(self, command, shell, stdout, stderr):
        self.process.pid = None
        self.process.poll = self.mock_process_poll_return_None
        return self.process

    def mock_subprocess_popen_process_launched_with_no_issues(self, command, shell, stdout, stderr):
        self.process.pid = 1
        self.process.poll = self.mock_process_poll_return_None
        return self.process

    def mock_process_poll_return_None(self):
        return None

    def mock_process_poll_return_Not_None(self):
        return 0

    def test_get_public_config_settings(self):
        ext_config_settings_handler = ExtConfigSettingsHandler(self.logger, self.json_file_handler, os.path.join(os.path.pardir, "tests", "helpers"))
        seq_no = "1234"
        config_settings = ext_config_settings_handler.read_file(seq_no)
        process_handler = ProcessHandler(self.logger, self.env_layer, self.ext_output_status_handler)
        public_config_settings = process_handler.get_public_config_settings(config_settings)
        self.assertTrue(public_config_settings is not None)
        self.assertEqual(public_config_settings.get(Constants.ConfigPublicSettingsFields.operation), "Installation")
        self.assertEqual(public_config_settings.get(Constants.ConfigPublicSettingsFields.maintenance_run_id), "2019-07-20T12:12:14Z")
        self.assertEqual(public_config_settings.get(Constants.ConfigPublicSettingsFields.patch_mode), "AutomaticByPlatform")

    def test_get_env_settings(self):
        handler_env_file_path = os.path.join(os.path.pardir, "tests", "helpers")
        ext_env_handler = ExtEnvHandler(self.json_file_handler, handler_env_file_path=handler_env_file_path)
        process_handler = ProcessHandler(self.logger, self.env_layer, self.ext_output_status_handler)
        env_settings = process_handler.get_env_settings(ext_env_handler)
        self.assertTrue(env_settings is not None)
        self.assertEqual(env_settings.get(Constants.EnvSettingsFields.log_folder), "mockLog")

    def test_kill_process(self):
        # setting mocks
        is_process_running_backup = ProcessHandler.is_process_running
        ProcessHandler.is_process_running = self.mock_is_process_running_to_return_true
        os_kill_backup = os.kill
        os.kill = self.mock_os_kill_to_raise_exception

        # error in terminating process
        pid = 123
        process_handler = ProcessHandler(self.logger, self.env_layer, self.ext_output_status_handler)
        self.assertRaises(OSError, process_handler.kill_process, pid)

        # reseting mocks
        ProcessHandler.is_process_running = is_process_running_backup
        os.kill = os_kill_backup

    def test_get_python_cmd(self):
        # setting mocks
        run_command_output_backup = EnvLayer.run_command_output
        process_handler = ProcessHandler(self.logger, self.env_layer, self.ext_output_status_handler)

        # testing for 'python' command
        EnvLayer.run_command_output = self.mock_run_command_output_for_python
        self.assertEqual(process_handler.get_python_cmd(), "python")

        # testing for 'python3' command
        EnvLayer.run_command_output = self.mock_run_command_output_for_python3
        self.assertEqual(process_handler.get_python_cmd(), "python3")

        # testing when python is not found on machine
        EnvLayer.run_command_output = self.mock_run_command_output_for_python_not_found
        self.assertEqual(process_handler.get_python_cmd(), Constants.PYTHON_NOT_FOUND)

        # resetting mocks
        EnvLayer.run_command_output = run_command_output_backup

    def test_start_daemon(self):
        # setting mocks
        get_python_cmd_backup = ProcessHandler.get_python_cmd
        ProcessHandler.get_python_cmd = self.mock_get_python_cmd
        subprocess_popen_backup = subprocess.Popen

        # Initializing config env
        ext_config_settings_handler = ExtConfigSettingsHandler(self.logger, self.json_file_handler, os.path.join(os.path.pardir, "tests", "helpers"))
        seq_no = "1234"
        config_settings = ext_config_settings_handler.read_file(seq_no)
        handler_env_file_path = os.path.join(os.path.pardir, "tests", "helpers")
        ext_env_handler = ExtEnvHandler(self.json_file_handler, handler_env_file_path=handler_env_file_path)

        # process was not launched
        subprocess.Popen = self.mock_subprocess_popen_process_not_launched
        process_handler = ProcessHandler(self.logger, self.env_layer, self.ext_output_status_handler)
        process = process_handler.start_daemon(seq_no, config_settings, ext_env_handler)
        self.assertTrue(process is None)

        # process launched with no issues
        subprocess.Popen = self.mock_subprocess_popen_process_launched_with_no_issues
        process_handler = ProcessHandler(self.logger, self.env_layer, self.ext_output_status_handler)
        process = process_handler.start_daemon(seq_no, config_settings, ext_env_handler)
        self.assertTrue(process is not None)

        # process launched but is not running soon after
        subprocess.Popen = self.mock_subprocess_popen_process_not_running_after_launch
        process_handler = ProcessHandler(self.logger, self.env_layer, self.ext_output_status_handler)

        # todo mock auto assess run command the way core has, where individual commands and expected output for each
        # mock run command output for Auto Assess shell file permission change
        run_command_output_backup = process_handler.env_layer.run_command_output
        process_handler.env_layer.run_command_output = self.mock_run_command_to_set_auto_assess_shell_file_permission

        process = process_handler.start_daemon(seq_no, config_settings, ext_env_handler)
        self.assertTrue(process is None)

        # resetting mocks
        ProcessHandler.get_python_cmd = get_python_cmd_backup
        subprocess.Popen = subprocess_popen_backup
        process_handler.env_layer.run_command_output = run_command_output_backup


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(TestProcessHandler)
    unittest.TextTestRunner(verbosity=2).run(SUITE)

