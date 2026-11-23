from unittest import mock

import pytest

import koji
from kojihub.migrations import config


class TestLoadDbOpts:

    def write_conf(self, tmp_path, text):
        conf = tmp_path / 'hub.conf'
        conf.write_text(text)
        return str(conf)

    def test_basic(self, tmp_path):
        conf = self.write_conf(tmp_path, """
[hub]
DBName = koji
DBUser = koji
DBHost = db.example.com
DBPort = 5432
DBPass = secret
""")
        opts = config.load_db_opts(config_file=conf, config_dir=str(tmp_path / 'none'))
        assert opts == {
            'DBName': 'koji',
            'DBUser': 'koji',
            'DBHost': 'db.example.com',
            'DBPort': '5432',
            'DBPass': 'secret',
        }

    def test_dbhost_alias(self, tmp_path):
        conf = self.write_conf(tmp_path, """
[hub]
DBName = koji
DBhost = db.example.com
""")
        opts = config.load_db_opts(config_file=conf, config_dir=str(tmp_path / 'none'))
        assert opts['DBHost'] == 'db.example.com'

    def test_dbhost_lowercase(self, tmp_path):
        # configparser option names are case insensitive, so the legacy
        # DBhost spelling is read as DBHost
        conf = self.write_conf(tmp_path, """
[hub]
DBName = koji
DBhost = old.example.com
""")
        opts = config.load_db_opts(config_file=conf, config_dir=str(tmp_path / 'none'))
        assert opts['DBHost'] == 'old.example.com'

    def test_empty_values_omitted(self, tmp_path):
        conf = self.write_conf(tmp_path, """
[hub]
DBName = koji
DBUser =
DBPass =
""")
        opts = config.load_db_opts(config_file=conf, config_dir=str(tmp_path / 'none'))
        assert opts == {'DBName': 'koji'}

    def test_connection_string(self, tmp_path):
        conf = self.write_conf(tmp_path, """
[hub]
DBConnectionString = dbname=koji user=koji host=db.example.com
""")
        opts = config.load_db_opts(config_file=conf, config_dir=str(tmp_path / 'none'))
        assert opts['DBConnectionString'] == 'dbname=koji user=koji host=db.example.com'

    def test_missing_file(self, tmp_path):
        with pytest.raises(koji.ConfigurationError):
            config.load_db_opts(config_file=str(tmp_path / 'missing.conf'),
                                config_dir=str(tmp_path / 'none'))

    def test_env_override(self, tmp_path, monkeypatch):
        conf = self.write_conf(tmp_path, """
[hub]
DBName = koji
""")
        monkeypatch.setenv('KOJI_HUB_CONFIG', conf)
        monkeypatch.setenv('KOJI_HUB_CONFIG_DIR', str(tmp_path / 'none'))
        opts = config.load_db_opts()
        assert opts == {'DBName': 'koji'}

    def test_config_dir(self, tmp_path):
        confdir = tmp_path / 'hub.conf.d'
        confdir.mkdir()
        (confdir / 'db.conf').write_text("[hub]\nDBName = koji\n")
        conf = self.write_conf(tmp_path, "[hub]\n")
        opts = config.load_db_opts(config_file=conf, config_dir=str(confdir))
        assert opts == {'DBName': 'koji'}


class TestGetDbUrl:

    def test_full_opts(self):
        opts = {
            'DBName': 'koji',
            'DBUser': 'koji',
            'DBHost': 'db.example.com',
            'DBPort': '5432',
            'DBPass': 'secret',
        }
        url = config.get_db_url(opts)
        assert url == 'postgresql+psycopg2://koji:secret@db.example.com:5432/koji'

    def test_minimal_opts(self):
        # psycopg2 defaults apply for omitted values
        assert config.get_db_url({}) == 'postgresql+psycopg2://'
        assert config.get_db_url({'DBName': 'koji'}) == 'postgresql+psycopg2:///koji'

    def test_password_escaping(self):
        url = config.get_db_url({'DBName': 'koji', 'DBUser': 'u', 'DBPass': 'p@ss:/word'})
        assert url == 'postgresql+psycopg2://u:p%40ss%3A%2Fword@/koji'

    def test_connection_string_uri(self):
        opts = {'DBConnectionString': 'postgresql://koji:secret@db.example.com/koji'}
        assert config.get_db_url(opts) == \
            'postgresql+psycopg2://koji:secret@db.example.com/koji'

    def test_connection_string_postgres_scheme(self):
        opts = {'DBConnectionString': 'postgres://koji@db.example.com/koji'}
        assert config.get_db_url(opts) == 'postgresql+psycopg2://koji@db.example.com/koji'

    def test_connection_string_with_driver(self):
        opts = {'DBConnectionString': 'postgresql+psycopg2://koji@db.example.com/koji'}
        assert config.get_db_url(opts) == 'postgresql+psycopg2://koji@db.example.com/koji'

    def test_connection_string_key_value(self):
        opts = {'DBConnectionString': 'dbname=koji user=koji host=db.example.com port=5433'}
        assert config.get_db_url(opts) == \
            'postgresql+psycopg2://koji@db.example.com:5433/koji'

    def test_connection_string_precedence(self):
        opts = {
            'DBConnectionString': 'postgresql://koji@db.example.com/koji',
            'DBName': 'other',
            'DBHost': 'other.example.com',
        }
        assert config.get_db_url(opts) == 'postgresql+psycopg2://koji@db.example.com/koji'

    def test_loads_opts_when_omitted(self):
        with mock.patch('kojihub.migrations.config.load_db_opts',
                        return_value={'DBName': 'koji'}) as load:
            url = config.get_db_url(config_file='/some/hub.conf', config_dir='/some/dir')
        load.assert_called_once_with('/some/hub.conf', '/some/dir')
        assert url == 'postgresql+psycopg2:///koji'
