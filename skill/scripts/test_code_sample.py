"""Tests for code_sample.py — heuristic logic (no API calls)."""
import pytest
from code_sample import find_dep_file, ENTRY_POINT_FILES, DEP_FILES


class TestFindDepFile:
    def test_java_pom(self):
        directory = [{"name": "pom.xml", "type": "file"}, {"name": "src", "type": "dir"}]
        assert find_dep_file(directory, "Java") == "pom.xml"

    def test_java_gradle(self):
        directory = [{"name": "build.gradle", "type": "file"}, {"name": "src", "type": "dir"}]
        assert find_dep_file(directory, "Java") == "build.gradle"

    def test_python_requirements(self):
        directory = [{"name": "requirements.txt", "type": "file"}]
        assert find_dep_file(directory, "Python") == "requirements.txt"

    def test_python_pyproject(self):
        directory = [{"name": "pyproject.toml", "type": "file"}]
        assert find_dep_file(directory, "Python") == "pyproject.toml"

    def test_no_dep_file(self):
        directory = [{"name": "README.md", "type": "file"}]
        assert find_dep_file(directory, "Java") is None

    def test_typescript_package_json(self):
        directory = [{"name": "package.json", "type": "file"}]
        assert find_dep_file(directory, "TypeScript") == "package.json"

    def test_go_mod(self):
        directory = [{"name": "go.mod", "type": "file"}, {"name": "main.go", "type": "file"}]
        assert find_dep_file(directory, "Go") == "go.mod"

    def test_rust_cargo(self):
        directory = [{"name": "Cargo.toml", "type": "file"}]
        assert find_dep_file(directory, "Rust") == "Cargo.toml"

    def test_unknown_language_fallback(self):
        directory = [{"name": "package.json", "type": "file"}]
        assert find_dep_file(directory, "Haskell") == "package.json"


class TestEntryPointPatterns:
    def test_all_languages_have_patterns(self):
        for lang in ["Java", "Python", "TypeScript", "JavaScript", "Go", "Rust"]:
            assert lang in ENTRY_POINT_FILES
            assert lang in DEP_FILES
            assert len(ENTRY_POINT_FILES[lang]) > 0
            assert len(DEP_FILES[lang]) > 0

    def test_kotlin_and_csharp_covered(self):
        assert "Kotlin" in ENTRY_POINT_FILES
        assert "C#" in ENTRY_POINT_FILES
        assert "Kotlin" in DEP_FILES
        assert "C#" in DEP_FILES
