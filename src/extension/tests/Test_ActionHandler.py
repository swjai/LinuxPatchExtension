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
import datetime
import glob
import json
import os
import shutil
import tempfile
import unittest

from extension.src.ActionHandler import ActionHandler
from extension.src.Constants import Constants
from extension.src.InstallCommandHandler import InstallCommandHandler
from extension.src.ProcessHandler import ProcessHandler
from extension.src.RuntimeContextHandler import RuntimeContextHandler
from extension.src.TelemetryWriter import TelemetryWriter
from extension.src.file_handlers.CoreStateHandler import CoreStateHandler
from extension.src.file_handlers.ExtConfigSettingsHandler import ExtConfigSettingsHandler
from extension.src.file_handlers.ExtEnvHandler import ExtEnvHandler
from extension.src.file_handlers.ExtOutputStatusHandler import ExtOutputStatusHandler
from extension.src.file_handlers.ExtStateHandler import ExtStateHandler
from extension.tests.helpers.RuntimeComposer import RuntimeComposer
from extension.tests.helpers.VirtualTerminal import VirtualTerminal


class TestActionHandler(unittest.TestCase):
    def setUp(self):
        VirtualTerminal().print_lowlight("\n----------------- setup test runner -----------------")
        self.temp_dir = tempfile.mkdtemp()

        self.runtime = RuntimeComposer()
        runtime_context_handler = RuntimeContextHandler(self.runtime.logger)
        self.ext_env_handler = ExtEnvHandler(self.runtime.json_file_handler, handler_env_file_path=os.path.join(os.path.pardir, "tests", "helpers"))
        self.ext_env_handler.telemetry_supported = True
        self.setup_files_and_folders(self.temp_dir)

        self.ext_config_settings_handler = ExtConfigSettingsHandler(self.runtime.logger, self.runtime.json_file_handler, self.ext_env_handler.config_folder)
        core_state_handler = CoreStateHandler(self.ext_env_handler.config_folder, self.runtime.json_file_handler)
        ext_state_handler = ExtStateHandler(self.ext_env_handler.config_folder, self.runtime.utility, self.runtime.json_file_handler)
        ext_output_status_handler = ExtOutputStatusHandler(self.runtime.logger, self.runtime.utility, self.runtime.json_file_handler, self.ext_env_handler.status_folder)
        process_handler = ProcessHandler(self.runtime.logger, self.runtime.env_layer, ext_output_status_handler)

        self.backup_get_seq_no_from_env_var = self.ext_config_settings_handler.get_seq_no_from_env_var
        self.ext_config_settings_handler.get_seq_no_from_env_var = self.mock_get_seq_no_from_env_var
        self.action_handler = ActionHandler(self.runtime.logger, self.runtime.env_layer, self.runtime.telemetry_writer, self.runtime.utility, runtime_context_handler, self.runtime.json_file_handler, self.runtime.env_health_manager,
                                            self.ext_env_handler, self.ext_config_settings_handler, core_state_handler, ext_state_handler, ext_output_status_handler, process_handler, datetime.datetime.utcnow())
        self.ext_config_settings_handler.get_seq_no_from_env_var = self.backup_get_seq_no_from_env_var

        self.backup_get_seq_no_from_env_var = self.ext_config_settings_handler.get_seq_no_from_env_var
        self.ext_config_settings_handler.get_seq_no_from_env_var = self.mock_get_seq_no_from_env_var

        self.backup_mock_os_path_realpath = os.path.realpath
        os.path.realpath = self.mock_os_path_realpath

    def tearDown(self):
        VirtualTerminal().print_lowlight("\n----------------- tear down test runner -----------------")
        self.ext_config_settings_handler.get_seq_no_from_env_var = self.backup_get_seq_no_from_env_var
        os.path.realpath = self.backup_mock_os_path_realpath
        # delete tempdir
        shutil.rmtree(self.temp_dir)

    def setup_files_and_folders(self, temp_dir):
        config_folder = self.ext_env_handler.config_folder
        status_folder = self.ext_env_handler.status_folder
        log_folder = self.ext_env_handler.log_folder
        events_folder = self.ext_env_handler.events_folder

        # creating the required folder (e.g: config folder, log folder, status folder) under the temp directory
        config_folder_complete_path = os.path.join(temp_dir, config_folder)
        status_folder_complete_path = os.path.join(temp_dir, status_folder)
        log_folder_complete_path = os.path.join(temp_dir, log_folder)
        events_folder_complete_path = os.path.join(temp_dir, log_folder, events_folder)

        os.mkdir(config_folder_complete_path)
        os.mkdir(status_folder_complete_path)
        os.mkdir(log_folder_complete_path)
        os.mkdir(events_folder_complete_path)

        # copying a sample version of the <seqno>.settings file from the helpers folder to the temp directory
        shutil.copy(os.path.join("helpers", "1234.settings"), config_folder_complete_path)
        config_file_path = os.path.join(config_folder_complete_path, '1234.settings')

        self.ext_env_handler.config_folder = config_folder_complete_path
        self.ext_env_handler.status_folder = status_folder_complete_path
        self.ext_env_handler.log_folder = log_folder_complete_path
        self.ext_env_handler.events_folder = events_folder_complete_path

    def mock_get_seq_no_from_env_var(self):
        return 1234

    def mock_get_all_versions(self, extension_pardir):
        return [extension_pardir + '/Microsoft.CPlat.Core.LinuxPatchExtension-1.2.3',
                extension_pardir + '/Microsoft.CPlat.Core.LinuxPatchExtension-1.2.5',
                extension_pardir + '/Microsoft.CPlat.Core.LinuxPatchExtension-1.1.9']

    def mock_get_all_versions_exception(self, extension_pardir):
        raise Exception

    def mock_get_seq_no_from_env_var(self, is_enable_request=False):
        return 1234

    def mock_os_path_realpath(self, file):
        return self.ext_env_handler.config_folder

    def mock_config_settings_read_file(self, seq_no):
        ext_config_settings_handler = ExtConfigSettingsHandler(self.runtime.logger, self.runtime.json_file_handler, os.path.join(os.path.pardir, "tests", "helpers"))
        config_values = ext_config_settings_handler.read_file(seq_no)
        return config_values

    def mock_setup_throws_exception(self, action, log_message):
        raise Exception

    def mock_validate_os_type(self):
        return True

    @staticmethod
    def create_latest_extension_dir(version, test_dir):
        latest_extension_version = version
        os.mkdir(os.path.join(test_dir, latest_extension_version))
        new_version_config_folder = os.path.join(test_dir, latest_extension_version, 'config')
        os.mkdir(new_version_config_folder)
        return new_version_config_folder

    def create_previous_extension_version(self, version, test_dir):
        os.mkdir(os.path.join(test_dir, version))
        previous_version_config_folder = os.path.join(test_dir, version, 'config')
        os.mkdir(previous_version_config_folder)
        self.runtime.create_temp_file(previous_version_config_folder, Constants.CORE_STATE_FILE, content='[test]')
        self.runtime.create_temp_file(previous_version_config_folder, Constants.EXT_STATE_FILE, content='test')
        self.runtime.create_temp_file(previous_version_config_folder, 'backup.bak', content='{"testkey": "testVal"}')
        self.runtime.create_temp_file(previous_version_config_folder, 'test.txt', content='{"testkey": "testVal"}')
        return previous_version_config_folder

    def test_update_command_success(self):
        events_folder_path_backup = self.action_handler.ext_env_handler.events_folder

        # testing with versions 1.2.5, 1.2.3 and 1.1.9
        # Create a temporary directory
        test_dir = tempfile.mkdtemp()
        # create extension dir for the latest and other extension versions, to be used in the test
        latest_extension_version = 'Microsoft.CPlat.Core.LinuxPatchExtension-1.2.5'
        new_version_config_folder = self.create_latest_extension_dir(latest_extension_version, test_dir)
        previous_extension_version = 'Microsoft.CPlat.Core.LinuxPatchExtension-1.2.3'
        previous_version_config_folder = self.create_previous_extension_version(previous_extension_version, test_dir)
        other_extension_version = 'Microsoft.CPlat.Core.LinuxPatchExtension-1.1.9'
        other_version_config_folder = self.create_previous_extension_version(other_extension_version, test_dir)
        self.action_handler.ext_env_handler.config_folder = new_version_config_folder
        self.action_handler.ext_env_handler.events_folder = test_dir
        self.assertTrue(self.action_handler.update() == Constants.ExitCode.Okay)
        self.assertTrue(os.path.exists(os.path.join(new_version_config_folder, Constants.CORE_STATE_FILE)))
        self.assertTrue(os.path.exists(os.path.join(new_version_config_folder, Constants.EXT_STATE_FILE)))
        self.assertTrue(os.path.exists(os.path.join(new_version_config_folder, 'backup.bak')))
        self.assertFalse(os.path.exists(os.path.join(new_version_config_folder, 'test.txt')))
        self.validate_status_file_on_success(self.action_handler.seq_no)
        self.action_handler.ext_env_handler.events_folder = events_folder_path_backup
        self.runtime.telemetry_writer.events_folder_path = None
        # Remove the directory after the test
        shutil.rmtree(test_dir)

        # testing with versions 1.6.99 and 1.6.100
        # Create a temporary directory
        test_dir = tempfile.mkdtemp()
        # create extension dir for the latest and other extension versions, to be used in the test
        latest_extension_version = 'Microsoft.CPlat.Core.LinuxPatchExtension-1.6.100'
        new_version_config_folder = self.create_latest_extension_dir(latest_extension_version, test_dir)
        previous_extension_version = 'Microsoft.CPlat.Core.LinuxPatchExtension-1.6.99'
        previous_version_config_folder = self.create_previous_extension_version(previous_extension_version, test_dir)
        self.action_handler.ext_env_handler.config_folder = new_version_config_folder
        self.action_handler.ext_env_handler.events_folder = test_dir
        self.assertTrue(self.action_handler.update() == Constants.ExitCode.Okay)
        self.assertTrue(os.path.exists(os.path.join(new_version_config_folder, Constants.CORE_STATE_FILE)))
        self.assertTrue(os.path.exists(os.path.join(new_version_config_folder, Constants.EXT_STATE_FILE)))
        self.assertTrue(os.path.exists(os.path.join(new_version_config_folder, 'backup.bak')))
        self.assertFalse(os.path.exists(os.path.join(new_version_config_folder, 'test.txt')))
        self.validate_status_file_on_success(self.action_handler.seq_no)
        self.action_handler.ext_env_handler.events_folder = events_folder_path_backup
        self.runtime.telemetry_writer.events_folder_path = None
        # Remove the directory after the test
        shutil.rmtree(test_dir)

        # testing with versions 1.4.897 and 1.5.23
        # Create a temporary directory
        test_dir = tempfile.mkdtemp()
        # create extension dir for the latest and other extension versions, to be used in the test
        latest_extension_version = 'Microsoft.CPlat.Core.LinuxPatchExtension-1.5.23'
        new_version_config_folder = self.create_latest_extension_dir(latest_extension_version, test_dir)
        previous_extension_version = 'Microsoft.CPlat.Core.LinuxPatchExtension-1.4.897'
        previous_version_config_folder = self.create_previous_extension_version(previous_extension_version, test_dir)
        self.action_handler.ext_env_handler.config_folder = new_version_config_folder
        self.action_handler.ext_env_handler.events_folder = test_dir
        self.assertTrue(self.action_handler.update() == Constants.ExitCode.Okay)
        self.assertTrue(os.path.exists(os.path.join(new_version_config_folder, Constants.CORE_STATE_FILE)))
        self.assertTrue(os.path.exists(os.path.join(new_version_config_folder, Constants.EXT_STATE_FILE)))
        self.assertTrue(os.path.exists(os.path.join(new_version_config_folder, 'backup.bak')))
        self.assertFalse(os.path.exists(os.path.join(new_version_config_folder, 'test.txt')))
        self.validate_status_file_on_success(self.action_handler.seq_no)
        self.action_handler.ext_env_handler.events_folder = events_folder_path_backup
        self.runtime.telemetry_writer.events_folder_path = None
        # Remove the directory after the test
        shutil.rmtree(test_dir)

        # testing with versions 1.0.0 and 2.0.00
        # Create a temporary directory
        test_dir = tempfile.mkdtemp()
        # create extension dir for the latest and other extension versions, to be used in the test
        latest_extension_version = 'Microsoft.CPlat.Core.LinuxPatchExtension-2.0.00'
        new_version_config_folder = self.create_latest_extension_dir(latest_extension_version, test_dir)
        previous_extension_version = 'Microsoft.CPlat.Core.LinuxPatchExtension-1.0.0'
        previous_version_config_folder = self.create_previous_extension_version(previous_extension_version, test_dir)
        self.action_handler.ext_env_handler.config_folder = new_version_config_folder
        self.action_handler.ext_env_handler.events_folder = test_dir
        self.assertTrue(self.action_handler.update() == Constants.ExitCode.Okay)
        self.assertTrue(os.path.exists(os.path.join(new_version_config_folder, Constants.CORE_STATE_FILE)))
        self.assertTrue(os.path.exists(os.path.join(new_version_config_folder, Constants.EXT_STATE_FILE)))
        self.assertTrue(os.path.exists(os.path.join(new_version_config_folder, 'backup.bak')))
        self.assertFalse(os.path.exists(os.path.join(new_version_config_folder, 'test.txt')))
        self.validate_status_file_on_success(self.action_handler.seq_no)
        self.action_handler.ext_env_handler.events_folder = events_folder_path_backup
        self.runtime.telemetry_writer.events_folder_path = None
        # Remove the directory after the test
        shutil.rmtree(test_dir)

    def test_update_command_fail(self):
        events_folder_path_backup = self.action_handler.ext_env_handler.events_folder
        # other versions not found
        test_dir = tempfile.mkdtemp()
        self.action_handler.ext_env_handler.events_folder = test_dir
        self.action_handler.ext_env_handler.config_folder = '/test/config'
        self.assertTrue(self.action_handler.update() == Constants.ExitCode.HandlerFailed)
        self.validate_status_file_on_failure(self.action_handler.seq_no, "No earlier versions for the extension found on the machine. So, could not copy any references to the current version.")
        self.action_handler.ext_env_handler.events_folder = events_folder_path_backup
        self.runtime.telemetry_writer.events_folder_path = None
        # Remove the directory after the test
        shutil.rmtree(test_dir)

        # path to previous version artifacts not found
        # Create a temporary directory and dir for the latest version
        test_dir = tempfile.mkdtemp()
        latest_extension_version = 'Microsoft.CPlat.Core.LinuxPatchExtension-1.2.5'
        os.mkdir(os.path.join(test_dir, latest_extension_version))
        new_version_config_folder = os.path.join(test_dir, latest_extension_version, 'config')
        os.mkdir(new_version_config_folder)
        self.action_handler.ext_env_handler.config_folder = new_version_config_folder
        self.action_handler.get_all_versions = self.mock_get_all_versions
        self.action_handler.ext_env_handler.events_folder = test_dir
        self.assertTrue(self.action_handler.update() == Constants.ExitCode.HandlerFailed)
        self.validate_status_file_on_failure(self.action_handler.seq_no, "No earlier versions for the extension found on the machine. So, could not copy any references to the current version.")
        self.action_handler.ext_env_handler.events_folder = events_folder_path_backup
        self.runtime.telemetry_writer.events_folder_path = None
        # Remove the directory after the test
        shutil.rmtree(test_dir)

        # exception path
        test_dir = tempfile.mkdtemp()
        latest_extension_version = 'Microsoft.CPlat.Core.LinuxPatchExtension-1.2.5'
        os.mkdir(os.path.join(test_dir, latest_extension_version))
        new_version_config_folder = os.path.join(test_dir, latest_extension_version, 'config')
        os.mkdir(new_version_config_folder)
        self.action_handler.ext_env_handler.config_folder = new_version_config_folder
        self.action_handler.get_all_versions = self.mock_get_all_versions_exception
        self.action_handler.ext_env_handler.events_folder = test_dir
        self.assertTrue(self.action_handler.update() == Constants.ExitCode.HandlerFailed)
        self.validate_status_file_on_failure(self.action_handler.seq_no, "Error occurred during extension update")
        self.action_handler.ext_env_handler.events_folder = events_folder_path_backup
        self.runtime.telemetry_writer.events_folder_path = None
        # Remove the directory after the test
        shutil.rmtree(test_dir)

    def test_telemetry_available(self):
        self.runtime.telemetry_writer.events_folder_path = tempfile.mkdtemp()
        self.assertTrue(self.runtime.telemetry_writer.is_telemetry_supported())
        shutil.rmtree(self.runtime.telemetry_writer.events_folder_path)
        self.runtime.telemetry_writer.events_folder_path = None

    def test_telemetry_not_available_env_var_not_exists(self):
        # agent env var is not set so telemetry is not supported
        backup_os_getenv = os.getenv
        backup_telemetry_writer = self.runtime.telemetry_writer

        def mock_os_getenv(name, value=None):
            return None

        # Re-init TelemetryWriter since the env var for compatibility is only checked on init
        os.getenv = mock_os_getenv
        self.runtime.telemetry_writer = TelemetryWriter(self.runtime.logger, self.runtime.env_layer)
        self.action_handler.telemetry_writer = self.runtime.telemetry_writer

        self.assertTrue(self.action_handler.uninstall() == Constants.ExitCode.Okay)

        file_read = open(self.runtime.logger.file_logger.log_file_path, "r")
        self.assertTrue(file_read is not None)
        file_contents = file_read.read()
        self.assertTrue(Constants.TELEMETRY_AT_AGENT_NOT_COMPATIBLE_ERROR_MSG in file_contents)
        self.assertTrue(Constants.AgentEnvVarStatusCode.FAILED_TO_GET_AGENT_SUPPORTED_FEATURES in file_contents)
        file_read.close()

        with self.assertRaises(SystemExit) as sys_exit:
            self.action_handler.enable()

        os.getenv = backup_os_getenv
        self.runtime.telemetry_writer = backup_telemetry_writer
        self.action_handler.telemetry_writer = backup_telemetry_writer

    def test_telemetry_not_available_env_var_key_not_exists(self):
        # agent env var is not set so telemetry is not supported
        backup_os_getenv = os.getenv
        backup_telemetry_writer = self.runtime.telemetry_writer

        def mock_os_getenv(name, value=None):
            return '[]'

        # Re-init TelemetryWriter since the env var for compatibility is only checked on init
        os.getenv = mock_os_getenv
        self.runtime.telemetry_writer = TelemetryWriter(self.runtime.logger, self.runtime.env_layer)
        self.action_handler.telemetry_writer = self.runtime.telemetry_writer

        self.assertTrue(self.action_handler.uninstall() == Constants.ExitCode.Okay)

        file_read = open(self.runtime.logger.file_logger.log_file_path, "r")
        self.assertTrue(file_read is not None)
        file_contents = file_read.read()
        self.assertTrue(Constants.TELEMETRY_AT_AGENT_NOT_COMPATIBLE_ERROR_MSG in file_contents)
        self.assertTrue(Constants.AgentEnvVarStatusCode.FAILED_TO_GET_TELEMETRY_KEY in file_contents)
        file_read.close()

        with self.assertRaises(SystemExit) as sys_exit:
            self.action_handler.enable()

        os.getenv = backup_os_getenv
        self.runtime.telemetry_writer = backup_telemetry_writer
        self.action_handler.telemetry_writer = backup_telemetry_writer

    def test_telemetry_available_but_events_folder_not_exists(self):
        # handler actions will continue to execute after logging telemetry not supported message
        events_folder_path_backup = self.action_handler.ext_env_handler.events_folder
        shutil.rmtree(events_folder_path_backup)

        # events folder is set within HandlerEnvironment but the directory path is invalid, so Telemetry is setup but events folder wasn't created by agent. In this case, we create the events folder
        self.assertTrue(self.action_handler.uninstall() == Constants.ExitCode.Okay)
        with self.assertRaises(SystemExit) as sys_exit:
            self.action_handler.enable()

        file_read = open(self.runtime.logger.file_logger.log_file_path, "r")
        self.assertTrue(file_read is not None)
        self.assertTrue(Constants.TELEMETRY_AT_AGENT_NOT_COMPATIBLE_ERROR_MSG not in file_read.read())
        file_read.close()

        self.action_handler.ext_env_handler.events_folder = events_folder_path_backup

    def test_timestamp_for_all_actions(self):
        """ All handler actions, specially all non-enable actions should have the same timestamp in OperationId within telemetry event """
        self.action_handler.uninstall()
        self.action_handler.reset()

        event_files = glob.glob(self.action_handler.telemetry_writer.events_folder_path + '/*.json')
        for event_file in event_files:
            with open(os.path.join(self.action_handler.telemetry_writer.events_folder_path, event_file), 'r+') as f:
                events = json.load(f)
                self.assertEqual(events[0]["OperationId"], self.action_handler.operation_id_substitute_for_all_actions_in_telemetry)

    def test_write_basic_status(self):
        # no status file if seq no not found
        self.action_handler.seq_no = None
        self.action_handler.write_basic_status(Constants.INSTALL)
        self.assertFalse(os.path.exists(os.path.join(self.ext_env_handler.status_folder, '1234.status')))

        # status file will be written if seq no is found
        self.action_handler.seq_no = 6789
        self.action_handler.write_basic_status(Constants.INSTALL)
        self.assertTrue(os.path.exists(os.path.join(self.ext_env_handler.status_folder, '6789.status')))
        status_json = self.action_handler.ext_output_status_handler.read_file(self.action_handler.seq_no)
        self.assertEqual(status_json[0]["status"]["name"], "Azure Patch Management")
        self.assertEqual(status_json[0]["status"]["operation"], "")
        self.assertEqual(status_json[0]["status"]["status"], Constants.Status.Transitioning.lower())
        self.assertEqual(status_json[0]["status"]["code"], 0)
        self.assertEqual(status_json[0]["status"]["formattedMessage"]["message"], "")
        self.assertEqual(status_json[0]["status"]["substatus"], [])

        # status file write for ENABLE (adds more details to status json than non ENABLE operations)
        self.backup_config_settings_read_file = self.ext_config_settings_handler.read_file
        self.ext_config_settings_handler.read_file = self.mock_config_settings_read_file

        self.action_handler.seq_no = 1234
        self.action_handler.write_basic_status(Constants.ENABLE)
        self.assertTrue(os.path.exists(os.path.join(self.ext_env_handler.status_folder, '1234.status')))
        status_json = self.action_handler.ext_output_status_handler.read_file(self.action_handler.seq_no)
        self.assertEqual(status_json[0]["status"]["name"], "Azure Patch Management")
        self.assertEqual(status_json[0]["status"]["operation"], "Installation")
        self.assertEqual(status_json[0]["status"]["status"], Constants.Status.Transitioning.lower())
        self.assertEqual(status_json[0]["status"]["code"], 0)
        self.assertEqual(status_json[0]["status"]["formattedMessage"]["message"], "")
        self.assertEqual(status_json[0]["status"]["substatus"], [])

        self.ext_config_settings_handler.read_file = self.backup_config_settings_read_file

    def test_status_file_on_uninstall_success(self):
        """ Validate a basic status file is written if seq no exists in env var """
        # no status file if seq no not found in env var
        self.action_handler.seq_no = None
        self.action_handler.uninstall()
        self.assertFalse(os.path.exists(os.path.join(self.ext_env_handler.status_folder, '1234.status')))

        # Uninstall succeeds, seq no available in env var, status file is written
        self.action_handler.seq_no = 1234
        self.action_handler.uninstall()
        self.validate_status_file_on_success(self.action_handler.seq_no)

    def test_status_file_on_uninstall_failed(self):
        """ Validate a basic status file is written if seq no exists in env var """
        self.backup_setup = self.action_handler.setup
        self.action_handler.setup = self.mock_setup_throws_exception

        # no status file if seq no not found in env var
        self.action_handler.seq_no = None
        self.action_handler.uninstall()
        self.assertFalse(os.path.exists(os.path.join(self.ext_env_handler.status_folder, '1234.status')))

        # Uninstall fails, seq no available in env var, status file is written
        self.action_handler.seq_no = 1234
        self.action_handler.uninstall()
        self.validate_status_file_on_failure(self.action_handler.seq_no, "Error occurred during extension uninstall")

        self.action_handler.setup = self.backup_setup

    def test_status_file_on_install_success(self):
        """ Validate a basic status file is written if seq no exists in env var """
        self.backup_validate_os_type = InstallCommandHandler.validate_os_type
        InstallCommandHandler.validate_os_type = self.mock_validate_os_type

        # no status file if seq no not found in env var
        self.action_handler.seq_no = None
        self.action_handler.install()
        self.assertFalse(os.path.exists(os.path.join(self.ext_env_handler.status_folder, '1234.status')))

        # Uninstall succeeds, seq no available in env var, status file is written
        self.action_handler.seq_no = 1234
        self.action_handler.install()
        self.validate_status_file_on_success(self.action_handler.seq_no)

        InstallCommandHandler.validate_os_type = self.backup_validate_os_type

    def test_status_file_on_install_failed(self):
        """ Validate a basic status file is written if seq no exists in env var """
        self.backup_setup = self.action_handler.setup
        self.action_handler.setup = self.mock_setup_throws_exception

        # no status file if seq no not found in env var
        self.action_handler.seq_no = None
        self.action_handler.install()
        self.assertFalse(os.path.exists(os.path.join(self.ext_env_handler.status_folder, '1234.status')))

        # Uninstall fails, seq no available in env var, status file is written
        self.action_handler.seq_no = 1234
        self.action_handler.install()
        self.validate_status_file_on_failure(self.action_handler.seq_no, "Error occurred during extension install")

        self.action_handler.setup = self.backup_setup

    def test_status_file_on_disable_success(self):
        """ Validate a basic status file is written if seq no exists in env var """
        # no status file if seq no not found in env var
        self.action_handler.seq_no = None
        self.action_handler.disable()
        self.assertFalse(os.path.exists(os.path.join(self.ext_env_handler.status_folder, '1234.status')))

        # Uninstall succeeds, seq no available in env var, status file is written
        self.action_handler.seq_no = 1234
        self.action_handler.disable()
        self.validate_status_file_on_success(self.action_handler.seq_no)

    def test_status_file_on_disable_failed(self):
        """ Validate a basic status file is written if seq no exists in env var """
        self.backup_setup = self.action_handler.setup
        self.action_handler.setup = self.mock_setup_throws_exception

        # no status file if seq no not found in env var
        self.action_handler.seq_no = None
        self.action_handler.disable()
        self.assertFalse(os.path.exists(os.path.join(self.ext_env_handler.status_folder, '1234.status')))

        # Uninstall fails, seq no available in env var, status file is written
        self.action_handler.seq_no = 1234
        self.action_handler.disable()
        self.validate_status_file_on_failure(self.action_handler.seq_no, "Error occurred during extension disable")

    def test_status_file_on_reset_success(self):
        """ Validate a basic status file is written if seq no exists in env var """
        # no status file if seq no not found in env var
        self.action_handler.seq_no = None
        self.action_handler.reset()
        self.assertFalse(os.path.exists(os.path.join(self.ext_env_handler.status_folder, '1234.status')))

        # Uninstall succeeds, seq no available in env var, status file is written
        self.action_handler.seq_no = 1234
        self.action_handler.reset()
        self.validate_status_file_on_success(self.action_handler.seq_no)

    def test_status_file_on_reset_failed(self):
        """ Validate a basic status file is written if seq no exists in env var """
        self.backup_setup = self.action_handler.setup
        self.action_handler.setup = self.mock_setup_throws_exception

        # no status file if seq no not found in env var
        self.action_handler.seq_no = None
        self.action_handler.reset()
        self.assertFalse(os.path.exists(os.path.join(self.ext_env_handler.status_folder, '1234.status')))

        # Uninstall fails, seq no available in env var, status file is written
        self.action_handler.seq_no = 1234
        self.action_handler.reset()
        self.validate_status_file_on_failure(self.action_handler.seq_no, "Error occurred during extension reset")

    def test_status_file_on_enable_success(self):
        """ Check that a basic status file is written during enable handler command setup """
        with self.assertRaises(SystemExit) as sys_exit:
            self.action_handler.enable()
        self.assertTrue(os.path.exists(os.path.join(self.ext_env_handler.status_folder, '1234.status')))
        status_json = self.action_handler.ext_output_status_handler.read_file(self.action_handler.seq_no)
        self.assertEqual(status_json[0]["status"]["name"], "Azure Patch Management")
        self.assertEqual(status_json[0]["status"]["operation"], "Installation")
        self.assertEqual(status_json[0]["status"]["status"], Constants.Status.Transitioning.lower())
        self.assertEqual(status_json[0]["status"]["code"], 0)
        self.assertEqual(status_json[0]["status"]["formattedMessage"]["message"], "")
        self.assertEqual(status_json[0]["status"]["substatus"], [])

    def test_status_file_on_enable_failed(self):
        """ Validate a basic status file is written if seq no exists in env var """
        self.backup_setup = self.action_handler.setup
        self.action_handler.setup = self.mock_setup_throws_exception

        # no status file if seq no not found in env var
        self.action_handler.seq_no = None
        self.action_handler.enable()
        self.assertFalse(os.path.exists(os.path.join(self.ext_env_handler.status_folder, '1234.status')))

        # Uninstall fails, seq no available in env var, status file is written
        self.action_handler.seq_no = 1234
        self.action_handler.enable()
        self.validate_status_file_on_failure(self.action_handler.seq_no, "Error occurred during extension enable")

    @staticmethod
    def mock_path_isdir(path):
        return 'LinuxPatchExtension-' in path

    def test_filter_files_from_versions(self):
        backup_path_isdir = os.path.isdir
        os.path.isdir = self.mock_path_isdir

        """ Checks that non-folders are filtered out from list of all versions """
        all_versions_including_files = [
            '/var/lib/waagent/Microsoft.CPlat.Core.LinuxPatchExtension__1.6.35.zip',
            '/var/lib/waagent/Microsoft.CPlat.Core.LinuxPatchExtension-1.6.36',
            '/var/lib/waagent/Microsoft.CPlat.Core.LinuxPatchExtension.388.manifest.xml',
            '/var/lib/waagent/Microsoft.CPlat.Core.LinuxPatchExtension-1.6.35'
        ]

        all_versions = self.action_handler.filter_files_from_versions(all_versions_including_files);
        self.assertTrue(len(all_versions) == 2)
        self.assertTrue('/var/lib/waagent/Microsoft.CPlat.Core.LinuxPatchExtension-1.6.36' in all_versions)
        self.assertTrue('/var/lib/waagent/Microsoft.CPlat.Core.LinuxPatchExtension-1.6.35' in all_versions)
        os.path.isdir = backup_path_isdir

    def validate_status_file_on_success(self, seq_no):
        # validate status file
        self.assertTrue(os.path.exists(os.path.join(self.ext_env_handler.status_folder, str(seq_no) + '.status')))
        status_json = self.action_handler.ext_output_status_handler.read_file(seq_no)
        self.assertEqual(status_json[0]["status"]["name"], "Azure Patch Management")
        self.assertEqual(status_json[0]["status"]["operation"], "")
        self.assertEqual(status_json[0]["status"]["status"], Constants.Status.Success.lower())
        self.assertEqual(status_json[0]["status"]["code"], 0)
        self.assertEqual(status_json[0]["status"]["formattedMessage"]["message"], "")
        self.assertEqual(status_json[0]["status"]["substatus"], [])

    def validate_status_file_on_failure(self, seq_no, message, code=Constants.ExitCode.HandlerFailed):
        self.assertTrue(os.path.exists(os.path.join(self.ext_env_handler.status_folder, str(seq_no) + '.status')))
        status_json = self.action_handler.ext_output_status_handler.read_file(seq_no)
        self.assertEqual(status_json[0]["status"]["name"], "Azure Patch Management")
        self.assertEqual(status_json[0]["status"]["operation"], "")
        self.assertEqual(status_json[0]["status"]["status"], Constants.Status.Error.lower())
        self.assertEqual(status_json[0]["status"]["code"], code)
        self.assertEqual(status_json[0]["status"]["formattedMessage"]["message"], message)
        self.assertEqual(status_json[0]["status"]["substatus"], [])

