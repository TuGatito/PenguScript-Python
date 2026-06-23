import unittest
import os
import sys
import tempfile
import json
from unittest.mock import patch
from io import StringIO

from driver.utils import run_command, print_success, print_error, print_warning, print_info
from driver.config import load_config, save_config, validate_config, ConfigError
from driver.cli import main

class TestDriverUtils(unittest.TestCase):
    def test_run_command(self):
        code, stdout, stderr = run_command([sys.executable, "-c", "print('hello')"])
        self.assertEqual(code, 0)
        self.assertIn("hello", stdout)
        self.assertEqual(stderr.strip(), "")

    def test_print_helpers(self):
        with patch('sys.stdout', new=StringIO()) as fake_out:
            print_success("yey")
            print_info("info")
            print_warning("warn")
            output = fake_out.getvalue()
            self.assertIn("Success", output)
            self.assertIn("Info", output)
            self.assertIn("Warning", output)

        with patch('sys.stderr', new=StringIO()) as fake_err:
            print_error("nay")
            self.assertIn("Error", fake_err.getvalue())

class TestDriverConfig(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.tmpdir.name, "penguscript.json")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_validate_config_defaults(self):
        raw = {"name": "test_proj"}
        validated = validate_config(raw)
        self.assertEqual(validated["name"], "test_proj")
        self.assertEqual(validated["version"], "0.1.0")
        self.assertEqual(validated["type"], "executable")
        self.assertEqual(validated["main"], "src/main.pengu")
        self.assertEqual(validated["profile"], "debug")

    def test_validate_config_errors(self):
        with self.assertRaises(ConfigError):
            validate_config({})
        
        with self.assertRaises(ConfigError):
            validate_config({"name": "a", "type": "invalid"})

        with self.assertRaises(ConfigError):
            validate_config({"name": "a", "compiler": "invalid"})

        with self.assertRaises(ConfigError):
            validate_config({"name": "a", "type": "executable", "main": ""})

        with self.assertRaises(ConfigError):
            validate_config({"name": "a", "src_dirs": "not-a-list"})

        with self.assertRaises(ConfigError):
            validate_config({"name": "a", "external_sources": "not-a-list"})

        with self.assertRaises(ConfigError):
            validate_config({"name": "a", "profile": "invalid-profile"})

    def test_load_save_config(self):
        data = {"name": "hello_world", "type": "cpp_only"}
        save_config(self.config_path, data)
        self.assertTrue(os.path.exists(self.config_path))

        loaded = load_config(self.config_path)
        self.assertEqual(loaded["name"], "hello_world")
        self.assertEqual(loaded["type"], "cpp_only")
        self.assertEqual(loaded["main"], "")

class TestDriverProject(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_create_project_structure(self):
        from driver.project import create_project_structure
        
        # Test executable structure
        target = os.path.join(self.tmpdir.name, "exe_proj")
        cfg = create_project_structure(target, "executable", "exe_proj")
        self.assertEqual(cfg["type"], "executable")
        self.assertTrue(os.path.exists(os.path.join(target, "src/main.pengu")))
        self.assertTrue(os.path.exists(os.path.join(target, "include")))
        self.assertTrue(os.path.exists(os.path.join(target, "lib")))
        self.assertTrue(os.path.exists(os.path.join(target, "build")))

        # Test static_lib structure
        target_lib = os.path.join(self.tmpdir.name, "lib_proj")
        cfg_lib = create_project_structure(target_lib, "static_lib", "lib_proj")
        self.assertEqual(cfg_lib["type"], "static_lib")
        self.assertTrue(os.path.exists(os.path.join(target_lib, "src/lib.pengu")))
        self.assertFalse(os.path.exists(os.path.join(target_lib, "build")))

        # Test cpp_only structure
        target_cpp = os.path.join(self.tmpdir.name, "cpp_proj")
        cfg_cpp = create_project_structure(target_cpp, "cpp_only", "cpp_proj")
        self.assertEqual(cfg_cpp["type"], "cpp_only")
        self.assertTrue(os.path.exists(os.path.join(target_cpp, "src/main.pengu")))
        self.assertFalse(os.path.exists(os.path.join(target_cpp, "include")))

class TestDriverCLI(unittest.TestCase):
    def setUp(self):
        self.old_cwd = os.getcwd()
        self.tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self.tmpdir.name)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmpdir.cleanup()

    def test_cli_init_default(self):
        code = main(["init"])
        self.assertEqual(code, 0)
        
        config_path = "penguscript.json"
        self.assertTrue(os.path.exists(config_path))
        with open(config_path, "r") as f:
            cfg = json.load(f)
        
        dir_name = os.path.basename(self.tmpdir.name)
        self.assertEqual(cfg["name"], dir_name)
        self.assertEqual(cfg["type"], "executable")
        
        self.assertTrue(os.path.exists("src/main.pengu"))
        self.assertTrue(os.path.exists("include"))
        self.assertTrue(os.path.exists("lib"))

    @patch('sys.stdin.isatty', return_value=True)
    @patch('builtins.input', side_effect=["prompted_project", "2"])
    def test_cli_init_prompted(self, mock_input, mock_isatty):
        code = main(["init"])
        self.assertEqual(code, 0)
        
        config_path = "prompted_project/penguscript.json"
        self.assertTrue(os.path.exists(config_path))
        with open(config_path, "r") as f:
            cfg = json.load(f)
            
        self.assertEqual(cfg["name"], "prompted_project")
        self.assertEqual(cfg["type"], "static_lib")
        self.assertTrue(os.path.exists("prompted_project/src/lib.pengu"))

    @patch('sys.stdin.isatty', return_value=True)
    @patch('builtins.input', side_effect=KeyboardInterrupt)
    def test_cli_init_prompted_cancel(self, mock_input, mock_isatty):
        code = main(["init"])
        self.assertEqual(code, 1)

    def test_cli_init_custom(self):
        code = main(["init", "my_lib", "--type", "static_lib"])
        self.assertEqual(code, 0)
        
        config_path = "my_lib/penguscript.json"
        self.assertTrue(os.path.exists(config_path))
        with open(config_path, "r") as f:
            cfg = json.load(f)
        
        self.assertEqual(cfg["name"], "my_lib")
        self.assertEqual(cfg["type"], "static_lib")
        self.assertFalse(os.path.exists("my_lib/src/main.pengu"))
        self.assertTrue(os.path.exists("my_lib/src"))

    def test_cli_placeholders_fail_if_no_config(self):
        self.assertEqual(main(["build"]), 1)
        self.assertEqual(main(["run"]), 1)
        self.assertEqual(main(["clean"]), 1)
        self.assertEqual(main(["test"]), 1)

    def test_cli_placeholders_success_with_config(self):
        main(["init", "--type", "executable"])
        self.assertEqual(main(["build"]), 0)
        self.assertEqual(main(["clean"]), 0)
        self.assertEqual(main(["run"]), 0)
        self.assertEqual(main(["test"]), 0)

    @patch('driver.commands.build_project')
    def test_cli_profile_override(self, mock_build_project):
        main(["init", "--type", "executable"])
        
        # Test build with release profile
        code = main(["build", "--profile", "release"])
        self.assertEqual(code, 0)
        config_path = os.path.join(os.getcwd(), "penguscript.json")
        mock_build_project.assert_called_with(config_path, profile_override="release")
        
        mock_build_project.reset_mock()
        
        # Test run with release profile
        # For cmd_run, it first loads config, builds, then executes.
        # We need a file to exist so run doesn't fail early.
        name = os.path.basename(self.tmpdir.name)
        is_windows = (sys.platform == "win32")
        binary = name + ".exe" if is_windows else name
        with open(binary, "w") as f:
            f.write("")
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            code = main(["run", "--profile", "release"])
            self.assertEqual(code, 0)
            mock_build_project.assert_called_with(config_path, profile_override="release")

class TestDriverCompiler(unittest.TestCase):
    @patch('shutil.which')
    def test_detect_compiler_preferred_found(self, mock_which):
        from driver.compiler import detect_compiler
        mock_which.side_effect = lambda x: f"/bin/{x}" if x == "g++" else None
        
        c_type, c_path = detect_compiler("g++")
        self.assertEqual(c_type, "g++")
        self.assertEqual(c_path, "/bin/g++")

    @patch('shutil.which', return_value=None)
    def test_detect_compiler_preferred_not_found(self, mock_which):
        from driver.compiler import detect_compiler, CompilerNotFoundError
        with self.assertRaises(CompilerNotFoundError):
            detect_compiler("clang++")

    @patch('shutil.which')
    def test_detect_compiler_auto(self, mock_which):
        from driver.compiler import detect_compiler
        # Simulate finding clang++ but not cl or g++ on Windows, or just finding clang++
        mock_which.side_effect = lambda x: f"/bin/{x}" if x == "clang++" else None
        
        c_type, c_path = detect_compiler("auto")
        self.assertEqual(c_type, "clang++")
        self.assertEqual(c_path, "/bin/clang++")

    @patch('subprocess.run')
    def test_compile_cpp_args_gcc(self, mock_run):
        from driver.compiler import compile_cpp
        mock_run.return_value.returncode = 0
        
        compile_cpp(["src/main.cpp"], "build/main.o", ["-O3"], "c++20", "g++", "/bin/g++")
        
        expected_cmd = ["/bin/g++", "-O3", "-std=c++20", "-c", "-o", "build/main.o", "src/main.cpp"]
        mock_run.assert_called_once_with(
            expected_cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

    @patch('subprocess.run')
    def test_compile_cpp_args_msvc(self, mock_run):
        from driver.compiler import compile_cpp
        mock_run.return_value.returncode = 0
        
        compile_cpp(["src/main.cpp"], "build/main.obj", ["/O2"], "c++20", "msvc", "cl.exe")
        
        expected_cmd = ["cl.exe", "/nologo", "/EHsc", "/O2", "/std:c++20", "/c", "/Fobuild/main.obj", "src/main.cpp"]
        mock_run.assert_called_once_with(
            expected_cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

    @patch('subprocess.run')
    def test_link_files_gcc(self, mock_run):
        from driver.compiler import link_files
        mock_run.return_value.returncode = 0
        
        link_files(["build/main.o"], "build/app", ["-lpthread"], "g++", "/bin/g++")
        
        expected_cmd = ["/bin/g++", "build/main.o", "-o", "build/app", "-lpthread"]
        mock_run.assert_called_once_with(
            expected_cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

    @patch('subprocess.run')
    def test_link_files_msvc(self, mock_run):
        from driver.compiler import link_files
        mock_run.return_value.returncode = 0
        
        link_files(["build/main.obj"], "build/app.exe", ["/DEBUG"], "msvc", "cl.exe")
        
        expected_cmd = ["cl.exe", "/nologo", "/EHsc", "build/main.obj", "/Febuild/app.exe", "/link", "/DEBUG"]
        mock_run.assert_called_once_with(
            expected_cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

class TestDriverBuilder(unittest.TestCase):
    def setUp(self):
        self.old_cwd = os.getcwd()
        self.tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self.tmpdir.name)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmpdir.cleanup()

    @patch('driver.builder.detect_compiler', return_value=("g++", "/bin/g++"))
    @patch('driver.builder.compile_cpp')
    @patch('driver.builder.link_files')
    @patch('driver.builder.Lexer')
    @patch('driver.builder.DeclarationParser')
    @patch('driver.builder.SemanticAnalyzer')
    @patch('driver.builder.CppGenerator')
    def test_build_project_flow(self, mock_gen, mock_sem, mock_parser, mock_lexer, mock_link, mock_compile, mock_detect):
        # Create a valid project first
        main(["init", "my_test_proj"])
        os.chdir("my_test_proj")

        # Mock semantic analysis success (empty diagnostic list)
        mock_sem.return_value.analyze.return_value = []

        from driver.builder import build_project
        build_project("penguscript.json")

        # Verify compiler front-end pipeline invocation
        mock_lexer.assert_called_once()
        mock_parser.assert_called_once()
        mock_sem.return_value.analyze.assert_called_once()
        mock_gen.return_value.generate.assert_called_once()

        # Verify C++ compilation and link invocation
        mock_compile.assert_called_once()
        mock_link.assert_called_once()

    @patch('driver.builder.detect_compiler', return_value=("g++", "/bin/g++"))
    @patch('driver.builder.compile_cpp')
    @patch('driver.builder.link_files')
    @patch('driver.builder.Lexer')
    @patch('driver.builder.DeclarationParser')
    @patch('driver.builder.SemanticAnalyzer')
    @patch('driver.builder.CppGenerator')
    def test_build_project_with_external_sources(self, mock_gen, mock_sem, mock_parser, mock_lexer, mock_link, mock_compile, mock_detect):
        # Create a valid project first
        main(["init", "my_test_proj"])
        os.chdir("my_test_proj")
        
        # Create an external source file
        os.makedirs("src_extra", exist_ok=True)
        extra_cpp = "src_extra/extra.cpp"
        with open(extra_cpp, "w") as f:
            f.write("int helper() { return 1; }")
            
        # Update config to include external sources
        with open("penguscript.json", "r") as f:
            cfg = json.load(f)
        cfg["external_sources"] = [extra_cpp]
        with open("penguscript.json", "w") as f:
            json.dump(cfg, f)

        # Mock semantic analysis success (empty diagnostic list)
        mock_sem.return_value.analyze.return_value = []

        from driver.builder import build_project
        build_project("penguscript.json")

        # Verify C++ compile was called twice (once for generated main.cc, once for extra.cpp)
        self.assertEqual(mock_compile.call_count, 2)
        mock_link.assert_called_once()

    @patch('driver.builder.compile_cpp')
    @patch('driver.builder.link_files')
    @patch('driver.builder.Lexer')
    @patch('driver.builder.DeclarationParser')
    @patch('driver.builder.SemanticAnalyzer')
    @patch('driver.builder.CppGenerator')
    def test_build_project_profile_flags(self, mock_gen, mock_sem, mock_parser, mock_lexer, mock_link, mock_compile):
        from driver.builder import build_project
        # Mock semantic analysis success
        mock_sem.return_value.analyze.return_value = []

        # Create a valid project first
        main(["init", "my_test_proj_flags"])
        os.chdir("my_test_proj_flags")

        # Test Case 1: debug profile, compiler g++
        with patch('driver.builder.detect_compiler', return_value=("g++", "/bin/g++")):
            build_project("penguscript.json", profile_override="debug")
            # Verify compile_cpp was called with "-O0", "-g"
            args, kwargs = mock_compile.call_args
            self.assertIn("-O0", kwargs["flags"])
            self.assertIn("-g", kwargs["flags"])
            self.assertNotIn("-O2", kwargs["flags"])
            # Verify link_files was called with "-g"
            args, kwargs = mock_link.call_args
            self.assertIn("-g", kwargs["ld_flags"])
            
        mock_compile.reset_mock()
        mock_link.reset_mock()

        # Test Case 2: release profile, compiler g++
        with patch('driver.builder.detect_compiler', return_value=("g++", "/bin/g++")):
            build_project("penguscript.json", profile_override="release")
            # Verify compile_cpp was called with "-O2", "-DNDEBUG"
            args, kwargs = mock_compile.call_args
            self.assertIn("-O2", kwargs["flags"])
            self.assertIn("-DNDEBUG", kwargs["flags"])
            self.assertNotIn("-O0", kwargs["flags"])
            # Verify link_files was NOT called with "-g"
            args, kwargs = mock_link.call_args
            self.assertNotIn("-g", kwargs["ld_flags"])

        mock_compile.reset_mock()
        mock_link.reset_mock()

        # Test Case 3: debug profile, compiler msvc
        with patch('driver.builder.detect_compiler', return_value=("msvc", "cl.exe")):
            build_project("penguscript.json", profile_override="debug")
            # Verify compile_cpp was called with "/Od", "/Zi"
            args, kwargs = mock_compile.call_args
            self.assertIn("/Od", kwargs["flags"])
            self.assertIn("/Zi", kwargs["flags"])
            self.assertNotIn("/O2", kwargs["flags"])
            # Verify link_files was called with "/DEBUG"
            args, kwargs = mock_link.call_args
            self.assertIn("/DEBUG", kwargs["ld_flags"])

        mock_compile.reset_mock()
        mock_link.reset_mock()

        # Test Case 4: release profile, compiler msvc
        with patch('driver.builder.detect_compiler', return_value=("msvc", "cl.exe")):
            build_project("penguscript.json", profile_override="release")
            # Verify compile_cpp was called with "/O2", "/DNDEBUG"
            args, kwargs = mock_compile.call_args
            self.assertIn("/O2", kwargs["flags"])
            self.assertIn("/DNDEBUG", kwargs["flags"])
            self.assertNotIn("/Od", kwargs["flags"])
            # Verify link_files was NOT called with "/DEBUG"
            args, kwargs = mock_link.call_args
            self.assertNotIn("/DEBUG", kwargs["ld_flags"])

    @patch('driver.commands.build_project')
    @patch('subprocess.run')
    def test_cmd_run_success(self, mock_run, mock_build):
        main(["init", "my_test_proj"])
        os.chdir("my_test_proj")
        
        is_windows = (sys.platform == "win32")
        binary = "my_test_proj.exe" if is_windows else "my_test_proj"
        with open(binary, "w") as f:
            f.write("")
        
        mock_run.return_value.returncode = 42
        code = main(["run"])
        self.assertEqual(code, 42)
        mock_run.assert_called_once()

    def test_cmd_clean(self):
        main(["init", "my_test_proj"])
        os.chdir("my_test_proj")

        os.makedirs("build", exist_ok=True)
        is_windows = (sys.platform == "win32")
        binary = "my_test_proj.exe" if is_windows else "my_test_proj"
        with open(binary, "w") as f:
            f.write("")
            
        self.assertTrue(os.path.exists("build"))
        self.assertTrue(os.path.exists(binary))
        
        code = main(["clean"])
        self.assertEqual(code, 0)
        
        self.assertFalse(os.path.exists("build"))
        self.assertFalse(os.path.exists(binary))

    @patch('driver.cli.print_version')
    def test_cli_version(self, mock_print):
        code = main(["-v"])
        self.assertEqual(code, 0)
        mock_print.assert_called_once()

        mock_print.reset_mock()
        code2 = main(["--version"])
        self.assertEqual(code2, 0)
        mock_print.assert_called_once()

    @patch('driver.compiler.detect_compiler', return_value=("g++", "/bin/g++"))
    @patch('subprocess.run')
    def test_print_version_gxx(self, mock_run, mock_detect):
        mock_run.return_value.stdout = "g++ (Ubuntu 11.2.0) 11.2.0"
        with patch('sys.stdout', new=StringIO()) as fake_out:
            from driver.cli import print_version
            print_version()
            output = fake_out.getvalue()
            self.assertIn("PenguScript Toolchain v0.1.0", output)
            self.assertIn("Detected C++ Compiler: g++ (g++ (Ubuntu 11.2.0) 11.2.0)", output)

if __name__ == "__main__":
    unittest.main()
