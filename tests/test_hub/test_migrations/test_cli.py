from unittest import mock

from kojihub.migrations import cli


class TestGetConfig:

    def parse(self, *argv):
        return cli.get_parser().parse_args(list(argv))

    def test_url_override(self):
        args = self.parse('--url', 'postgresql+psycopg2://u:p%40ss@host/db', 'current')
        cfg = cli.get_config(args)
        # percent signs are escaped for configparser storage;
        # get_main_option interpolates them back
        assert cfg.get_main_option('sqlalchemy.url') == \
            'postgresql+psycopg2://u:p%40ss@host/db'

    def test_config_x_args(self):
        args = self.parse('--config', '/some/hub.conf', '--config-dir', '/some/dir',
                          'current')
        cfg = cli.get_config(args)
        assert cfg.cmd_opts.x == ['config=/some/hub.conf', 'config_dir=/some/dir']

    def test_no_x_args(self):
        args = self.parse('current')
        cfg = cli.get_config(args)
        assert cfg.cmd_opts.x == []


class TestMain:

    def test_upgrade_default_head(self):
        with mock.patch('kojihub.migrations.cli.command') as cmd:
            assert cli.main(['upgrade']) == 0
        cmd.upgrade.assert_called_once()
        assert cmd.upgrade.call_args[0][1] == 'head'
        assert cmd.upgrade.call_args[1] == {'sql': False}

    def test_upgrade_revision_sql(self):
        with mock.patch('kojihub.migrations.cli.command') as cmd:
            cli.main(['upgrade', '+1', '--sql'])
        assert cmd.upgrade.call_args[0][1] == '+1'
        assert cmd.upgrade.call_args[1] == {'sql': True}

    def test_downgrade(self):
        with mock.patch('kojihub.migrations.cli.command') as cmd:
            cli.main(['downgrade', 'base'])
        assert cmd.downgrade.call_args[0][1] == 'base'

    def test_stamp(self):
        with mock.patch('kojihub.migrations.cli.command') as cmd:
            cli.main(['stamp', 'head'])
        cmd.stamp.assert_called_once()
        assert cmd.stamp.call_args[0][1] == 'head'

    def test_current(self):
        with mock.patch('kojihub.migrations.cli.command') as cmd:
            cli.main(['current'])
        cmd.current.assert_called_once()

    def test_history(self):
        with mock.patch('kojihub.migrations.cli.command') as cmd:
            cli.main(['history'])
        cmd.history.assert_called_once()

    def test_heads(self):
        with mock.patch('kojihub.migrations.cli.command') as cmd:
            cli.main(['heads'])
        cmd.heads.assert_called_once()

    def test_check(self):
        with mock.patch('kojihub.migrations.cli.command') as cmd:
            cli.main(['check'])
        cmd.check.assert_called_once()
