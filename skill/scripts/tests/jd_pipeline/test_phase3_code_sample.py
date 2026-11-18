"""Phase 3: Code Sample — test dependency detection and fetch output schema."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import jsonschema

from code_sample import find_dep_file


class TestDependencyDetection:
    def test_javascript_package_json(self):
        directory = [{"name": "package.json", "type": "file"}, {"name": "src", "type": "dir"}]
        assert find_dep_file(directory, "JavaScript") == "package.json"

    def test_typescript_package_json(self):
        directory = [{"name": "package.json", "type": "file"}, {"name": "tsconfig.json", "type": "file"}]
        assert find_dep_file(directory, "TypeScript") == "package.json"

    def test_java_pom_xml(self):
        directory = [{"name": "pom.xml", "type": "file"}, {"name": "src", "type": "dir"}]
        assert find_dep_file(directory, "Java") == "pom.xml"

    def test_python_requirements(self):
        directory = [{"name": "requirements.txt", "type": "file"}, {"name": "app.py", "type": "file"}]
        assert find_dep_file(directory, "Python") == "requirements.txt"

    def test_go_mod(self):
        directory = [{"name": "go.mod", "type": "file"}, {"name": "main.go", "type": "file"}]
        assert find_dep_file(directory, "Go") == "go.mod"

    def test_rust_cargo(self):
        directory = [{"name": "Cargo.toml", "type": "file"}, {"name": "src", "type": "dir"}]
        assert find_dep_file(directory, "Rust") == "Cargo.toml"

    def test_unknown_language_none(self):
        directory = [{"name": "main.xyz", "type": "file"}]
        result = find_dep_file(directory, "Brainfuck")
        assert result is None

    def test_empty_directory(self):
        result = find_dep_file([], "JavaScript")
        assert result is None


class TestFetchOutputSchema:
    def test_all_developers_valid(self, golden_fetch, schema_fetch_developer):
        for dev in golden_fetch:
            jsonschema.validate(dev, schema_fetch_developer)

    def test_all_devs_have_source_files(self, golden_fetch):
        for dev in golden_fetch:
            for repo in dev["topRepos"]:
                assert "sourceFiles" in repo, f"{dev['login']}/{repo['name']} missing sourceFiles"

    def test_all_devs_have_commits(self, golden_fetch):
        for dev in golden_fetch:
            for repo in dev["topRepos"]:
                assert "commits" in repo
                assert len(repo["commits"]) >= 1

    def test_profile_urls_correct(self, golden_fetch):
        for dev in golden_fetch:
            assert dev["profileUrl"] == f"https://github.com/{dev['login']}"
