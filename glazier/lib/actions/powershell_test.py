# Lint as: python3
# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for glazier.lib.actions.powershell."""

from absl.testing import absltest
from glazier.lib import buildinfo
from glazier.lib.actions import powershell
import mock


class PowershellTest(absltest.TestCase):

  def setUp(self):
    super(PowershellTest, self).setUp()
    buildinfo.constants.FLAGS.config_server = 'https://glazier/'
    self.bi = buildinfo.BuildInfo()

  @mock.patch.object(
      powershell.powershell.PowerShell, 'RunLocal', autospec=True)
  @mock.patch.object(powershell.cache.Cache, 'CacheFromLine', autospec=True)
  def testPSScript(self, cache, run):
    cache.return_value = r'C:\Cache\Some-Script.ps1'
    ps = powershell.PSScript(['#Some-Script.ps1', ['-Flag1']], self.bi)
    run.return_value = 0
    ps.Run()
    cache.assert_called_with(mock.ANY, '#Some-Script.ps1', self.bi)
    run.assert_called_with(
        mock.ANY, r'C:\Cache\Some-Script.ps1', args=['-Flag1'])
    run.side_effect = powershell.powershell.PowerShellError
    self.assertRaises(powershell.ActionError, ps.Run)
    # Cache error
    run.side_effect = None
    cache.side_effect = powershell.cache.CacheError
    self.assertRaises(powershell.ActionError, ps.Run)

  @mock.patch.object(
      powershell.powershell.PowerShell, 'RunLocal', autospec=True)
  @mock.patch.object(powershell.cache.Cache, 'CacheFromLine', autospec=True)
  def testPSScriptSuccessCodes(self, cache, run):
    cache.return_value = r'C:\Cache\Some-Script.ps1'
    ps = powershell.PSScript(['#Some-Script.ps1', ['-Flag1'], [1337, 1338]],
                             self.bi)
    run.return_value = 0
    self.assertRaises(powershell.ActionError, ps.Run)
    run.return_value = 1337
    ps.Run()

  @mock.patch.object(
      powershell.powershell.PowerShell, 'RunLocal', autospec=True)
  @mock.patch.object(powershell.cache.Cache, 'CacheFromLine', autospec=True)
  def testPSScriptRebootNoRetry(self, cache, run):
    cache.return_value = r'C:\Cache\Some-Script.ps1'
    ps = powershell.PSScript(
        ['#Some-Script.ps1', ['-Flag1'], [0], [1337, 1338]], self.bi)
    run.return_value = 1337
    self.assertRaises(powershell.RestartEvent, ps.Run)

  @mock.patch.object(
      powershell.powershell.PowerShell, 'RunLocal', autospec=True)
  @mock.patch.object(powershell.cache.Cache, 'CacheFromLine', autospec=True)
  def testPSScriptRebootRetry(self, cache, run):
    cache.return_value = r'C:\Cache\Some-Script.ps1'
    ps = powershell.PSScript(
        ['#Some-Script.ps1', ['-Flag1'], [0], [1337, 1338], True], self.bi)
    run.return_value = 1337
    self.assertRaises(powershell.RestartEvent, ps.Run)
    cache.assert_called_with(mock.ANY, '#Some-Script.ps1', self.bi)

  def testPSScriptValidateType(self):
    ps = powershell.PSScript(30, None)
    self.assertRaises(powershell.ValidationError, ps.Validate)

    ps = powershell.PSScript(['#Some-Script.ps1', '-Verbose'], None)
    self.assertRaises(powershell.ValidationError, ps.Validate)

    ps = powershell.PSScript(['#Some-Script.ps1', ['-Verbose'], 0], None)
    self.assertRaises(powershell.ValidationError, ps.Validate)

    ps = powershell.PSScript(
        ['#Some-Script.ps1', ['-Verbose'], [0], 1337], None)
    self.assertRaises(powershell.ValidationError, ps.Validate)

    ps = powershell.PSScript(
        ['#Some-Script.ps1', ['-Verbose'], [0], [1337], 'True'], None)
    self.assertRaises(powershell.ValidationError, ps.Validate)

  def testPSScriptValidateLen(self):
    ps = powershell.PSScript([], None)
    self.assertRaises(powershell.ValidationError, ps.Validate)

    ps = powershell.PSScript([1, 2, 3, 4, 5, 6], None)
    self.assertRaises(powershell.ValidationError, ps.Validate)

  def testPSScriptValidate(self):
    ps = powershell.PSScript([
        '#Some-Script.ps1', ['-Verbose', '-InformationAction', 'Continue'], [0],
        [1337, 1338], True
    ], None)
    ps.Validate()

  @mock.patch.object(
      powershell.powershell.PowerShell, 'RunCommand', autospec=True)
  def testPSCommand(self, run):
    ps = powershell.PSCommand(['Write-Verbose Foo -Verbose', [1337]], self.bi)
    run.return_value = 1337
    ps.Run()
    run.assert_called_with(
        mock.ANY, ['Write-Verbose', 'Foo', '-Verbose'], [1337])

  @mock.patch.object(
      powershell.powershell.PowerShell, 'RunCommand', autospec=True)
  def testPSCommandSuccessError(self, run):
    ps = powershell.PSCommand(['Write-Verbose Foo -Verbose', [0]], self.bi)
    run.return_value = 1337
    self.assertRaises(powershell.ActionError, ps.Run)

  @mock.patch.object(
      powershell.powershell.PowerShell, 'RunCommand', autospec=True)
  @mock.patch.object(powershell.cache.Cache, 'CacheFromLine', autospec=True)
  def testPSCommandCache(self, cache, run):
    cache.return_value = r'C:\Cache\Some-Script.ps1'
    ps = powershell.PSCommand(['#Some-Script.ps1 -confirm:$false'], self.bi)
    run.return_value = 0
    ps.Run()
    run.assert_called_with(mock.ANY,
                           ['C:\\Cache\\Some-Script.ps1', '-confirm:$false'],
                           [0])
    cache.assert_called_with(mock.ANY, '#Some-Script.ps1', self.bi)

  @mock.patch.object(
      powershell.powershell.PowerShell, 'RunCommand', autospec=True)
  @mock.patch.object(powershell.cache.Cache, 'CacheFromLine', autospec=True)
  def testPSCommandCacheError(self, cache, run):
    ps = powershell.PSCommand(['#Some-Script.ps1 -confirm:$false'], self.bi)
    run.side_effect = None
    cache.side_effect = powershell.cache.CacheError
    self.assertRaises(powershell.ActionError, ps.Run)

  @mock.patch.object(
      powershell.powershell.PowerShell, 'RunCommand', autospec=True)
  def testPSCommandRebootNoRetry(self, run):
    ps = powershell.PSCommand(['Write-Verbose Foo -Verbose', [0], [1337, 1338]],
                              self.bi)
    run.return_value = 1337
    self.assertRaises(powershell.RestartEvent, ps.Run)

  @mock.patch.object(
      powershell.powershell.PowerShell, 'RunCommand', autospec=True)
  def testPSCommandRebootRetry(self, run):
    ps = powershell.PSCommand(
        ['Write-Verbose Foo -Verbose', [0], [1337, 1338], True], self.bi)
    run.return_value = 1337
    self.assertRaises(powershell.RestartEvent, ps.Run)

  @mock.patch.object(
      powershell.powershell.PowerShell, 'RunCommand', autospec=True)
  def testPSCommandError(self, run):
    ps = powershell.PSCommand(['Write-Verbose Foo -Verbose', [1337]], None)
    run.side_effect = powershell.powershell.PowerShellError
    self.assertRaises(powershell.ActionError, ps.Run)

  def testPSCommandValidate(self):
    ps = powershell.PSCommand(30, None)
    self.assertRaises(powershell.ValidationError, ps.Validate)
    ps = powershell.PSCommand([], None)
    self.assertRaises(powershell.ValidationError, ps.Validate)
    ps = powershell.PSCommand([30, 40], None)
    ps = powershell.PSCommand(['Write-Verbose Foo -Verbose', [0], 1337], None)
    self.assertRaises(powershell.ValidationError, ps.Validate)
    ps = powershell.PSCommand(
        ['Write-Verbose Foo -Verbose', [0], [1337], 'True'], None)
    self.assertRaises(powershell.ValidationError, ps.Validate)
    ps = powershell.PSCommand(['Write-Verbose Foo -Verbose'], None)
    ps.Validate()
    ps = powershell.PSCommand(['Write-Verbose Foo -Verbose', [1337]],
                              None)
    ps.Validate()

if __name__ == '__main__':
  absltest.main()
