"""Unit tests for CLI module."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from pyghtcast.cli import cli, get_connection


class TestCLI:
    """Test CLI functionality."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    def test_cli_version(self, runner):
        """Test version display."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_help(self, runner):
        """Test help display."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "pyghtcast" in result.output
        assert "discover" in result.output
        assert "query" in result.output

    @patch.dict(os.environ, {}, clear=True)
    def test_get_connection_missing_env_vars(self):
        """Test connection fails with missing environment variables."""
        with pytest.raises(SystemExit) as exc_info:
            get_connection()
        assert exc_info.value.code == 1

    @patch.dict(os.environ, {"LCAPI_USER": "test_user", "LCAPI_PASS": "test_pass"})
    @patch("pyghtcast.cli.CoreLMIConnection")
    def test_get_connection_success(self, mock_conn_class):
        """Test successful connection creation."""
        mock_conn = MagicMock()
        mock_conn_class.return_value = mock_conn

        result = get_connection()

        mock_conn_class.assert_called_once_with("test_user", "test_pass")
        assert result == mock_conn

    @patch("pyghtcast.cli.get_connection")
    def test_discover_datasets_json(self, mock_get_conn, runner):
        """Test discover datasets with JSON output."""
        mock_conn = MagicMock()
        mock_conn.get_meta.return_value = {
            "datasets": {
                "emsi.us.occupation": {
                    "title": "US Occupation Data",
                    "description": "Occupation-level employment data",
                    "versions": ["2025.3", "2025.2", "2025.1"],
                }
            }
        }
        mock_get_conn.return_value = mock_conn

        result = runner.invoke(cli, ["discover", "datasets", "--json"])
        assert result.exit_code == 0
        output_json = json.loads(result.output)
        assert "datasets" in output_json
        assert "emsi.us.occupation" in output_json["datasets"]

    @patch("pyghtcast.cli.get_connection")
    def test_discover_datasets_formatted(self, mock_get_conn, runner):
        """Test discover datasets with formatted output."""
        mock_conn = MagicMock()
        mock_conn.get_meta.return_value = {
            "datasets": {
                "emsi.us.occupation": {
                    "title": "US Occupation Data",
                    "description": "Occupation-level employment data",
                    "versions": ["2025.3", "2025.2", "2025.1"],
                }
            }
        }
        mock_get_conn.return_value = mock_conn

        result = runner.invoke(cli, ["discover", "datasets"])
        assert result.exit_code == 0
        assert "emsi.us.occupation" in result.output
        assert "US Occupation Data" in result.output

    @patch("pyghtcast.cli.get_connection")
    def test_discover_dimensions(self, mock_get_conn, runner):
        """Test discover dimensions command."""
        mock_conn = MagicMock()
        mock_conn.get_meta_dataset.return_value = {
            "dimensions": {
                "Area": {"title": "Geographic Area", "description": "Geographic regions", "hierarchyLevels": 5},
                "Occupation": {"title": "Occupation", "description": "Job categories", "hierarchyLevels": 6},
            },
            "metrics": {"Jobs.2022": {"title": "Total Jobs 2022"}},
        }
        mock_get_conn.return_value = mock_conn

        result = runner.invoke(
            cli, ["discover", "dimensions", "--dataset", "emsi.us.occupation", "--datarun", "2025.3"]
        )
        assert result.exit_code == 0
        assert "Area" in result.output
        assert "Occupation" in result.output
        assert "Jobs.2022" in result.output

    @patch("pyghtcast.cli.get_connection")
    def test_discover_hierarchy_csv(self, mock_get_conn, runner):
        """Test discover hierarchy with CSV output."""
        mock_conn = MagicMock()
        mock_df = MagicMock()
        mock_df.to_csv.return_value = "id,name,level\n00-0000,All Occupations,0\n"
        mock_df.__len__ = MagicMock(return_value=1)
        mock_df.head = MagicMock(return_value=mock_df)
        mock_conn.get_dimension_hierarchy_df.return_value = mock_df
        mock_get_conn.return_value = mock_conn

        result = runner.invoke(
            cli,
            [
                "discover",
                "hierarchy",
                "--dataset",
                "emsi.us.occupation",
                "--dimension",
                "Occupation",
                "--datarun",
                "2025.3",
                "--csv",
            ],
        )
        assert result.exit_code == 0
        assert "id,name,level" in result.output

    @patch("pyghtcast.cli.get_connection")
    def test_discover_hierarchy_formatted(self, mock_get_conn, runner):
        """Test discover hierarchy with formatted output."""
        mock_conn = MagicMock()
        mock_conn.get_meta_dataset_dimension.return_value = {
            "hierarchy": [
                {"id": "00-0000", "name": "All Occupations", "level": 0},
                {"id": "11-0000", "name": "Management Occupations", "level": 1},
            ]
        }
        mock_get_conn.return_value = mock_conn

        result = runner.invoke(
            cli,
            [
                "discover",
                "hierarchy",
                "--dataset",
                "emsi.us.occupation",
                "--dimension",
                "Occupation",
                "--datarun",
                "2025.3",
                "--limit",
                "2",
            ],
        )
        assert result.exit_code == 0
        assert "All Occupations" in result.output
        assert "00-0000" in result.output

    @patch("pyghtcast.cli.get_connection")
    def test_discover_definitions(self, mock_get_conn, runner):
        """Test discover definitions command."""
        mock_conn = MagicMock()
        mock_conn.get_meta_definitions.return_value = {"version": "1.0", "description": "API definitions"}
        mock_get_conn.return_value = mock_conn

        result = runner.invoke(cli, ["discover", "definitions"])
        assert result.exit_code == 0
        assert "version" in result.output

    def test_query_build(self, runner):
        """Test query build command (placeholder)."""
        result = runner.invoke(cli, ["query", "build", "--dataset", "emsi.us.occupation"])
        assert result.exit_code == 0
        assert "Interactive query builder" in result.output
        assert "coming soon" in result.output

    def test_query_example_occupation(self, runner):
        """Test query example for occupation."""
        result = runner.invoke(cli, ["query", "example", "--dataset", "occupation"])
        assert result.exit_code == 0
        assert "Occupation Query" in result.output
        assert "emsi.us.occupation" in result.output

    def test_query_example_industry(self, runner):
        """Test query example for industry."""
        result = runner.invoke(cli, ["query", "example", "--dataset", "industry"])
        assert result.exit_code == 0
        assert "Industry Query" in result.output
        assert "emsi.us.industry" in result.output

    @patch("pyghtcast.cli.get_connection")
    def test_error_handling(self, mock_get_conn, runner):
        """Test error handling in CLI."""
        mock_conn = MagicMock()
        mock_conn.get_meta.side_effect = Exception("API Error")
        mock_get_conn.return_value = mock_conn

        result = runner.invoke(cli, ["discover", "datasets"])
        assert result.exit_code == 1
        assert "Error fetching datasets: API Error" in result.output
