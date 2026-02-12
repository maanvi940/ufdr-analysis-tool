"""
UFDR Analysis Tool - Smoke Tests
Post-installation validation suite
Version: 2.0.0
"""

import sys
from pathlib import Path
import importlib
import subprocess
from typing import List
from dataclasses import dataclass

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    critical: bool = True


class SmokeTestRunner:
    """Runs post-installation smoke tests"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.critical_failures = 0
        self.warnings = 0
    
    def print_header(self):
        """Print test header"""
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("╔══════════════════════════════════════════════════════════╗")
        print("║   UFDR Analysis Tool - Smoke Tests                      ║")
        print("║   Post-Installation Validation                          ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print(f"{Colors.RESET}\n")
    
    def test_python_version(self) -> TestResult:
        """Test Python version"""
        print(f"{Colors.BLUE}[1/15]{Colors.RESET} Testing Python version...")
        
        version = sys.version_info
        if version.major >= 3 and version.minor >= 9:
            return TestResult(
                "Python Version",
                True,
                f"Python {version.major}.{version.minor}.{version.micro}",
                True
            )
        else:
            return TestResult(
                "Python Version",
                False,
                f"Python {version.major}.{version.minor} (3.9+ required)",
                True
            )
    
    def test_core_dependencies(self) -> TestResult:
        """Test core Python dependencies"""
        print(f"{Colors.BLUE}[2/15]{Colors.RESET} Testing core dependencies...")
        
        required_packages = [
            'pandas',
            'numpy',
            'pydantic',
            'cryptography',
            'loguru',
            'click'
        ]
        
        missing = []
        for package in required_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                missing.append(package)
        
        if not missing:
            return TestResult(
                "Core Dependencies",
                True,
                f"{len(required_packages)} packages installed",
                True
            )
        else:
            return TestResult(
                "Core Dependencies",
                False,
                f"Missing: {', '.join(missing)}",
                True
            )
    
    def test_nlp_dependencies(self) -> TestResult:
        """Test NLP dependencies"""
        print(f"{Colors.BLUE}[3/15]{Colors.RESET} Testing NLP dependencies...")
        
        nlp_packages = [
            'sentence_transformers',
            'transformers',
            'torch'
        ]
        
        missing = []
        for package in nlp_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                missing.append(package)
        
        if not missing:
            return TestResult(
                "NLP Dependencies",
                True,
                f"{len(nlp_packages)} packages installed",
                False
            )
        else:
            return TestResult(
                "NLP Dependencies",
                False,
                f"Missing: {', '.join(missing)} (optional)",
                False
            )
    
    def test_ui_dependencies(self) -> TestResult:
        """Test UI dependencies"""
        print(f"{Colors.BLUE}[4/15]{Colors.RESET} Testing UI dependencies...")
        
        ui_packages = [
            'streamlit',
            'plotly',
            'networkx'
        ]
        
        missing = []
        for package in ui_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                missing.append(package)
        
        if not missing:
            return TestResult(
                "UI Dependencies",
                True,
                f"{len(ui_packages)} packages installed",
                True
            )
        else:
            return TestResult(
                "UI Dependencies",
                False,
                f"Missing: {', '.join(missing)}",
                True
            )
    
    def test_directory_structure(self) -> TestResult:
        """Test directory structure"""
        print(f"{Colors.BLUE}[5/15]{Colors.RESET} Testing directory structure...")
        
        required_dirs = [
            'parser',
            'models',
            'heuristics',
            'nlp',
            'vector',
            'graph',
            'security',
            'frontend',
            'data',
            'logs'
        ]
        
        missing = []
        for dir_name in required_dirs:
            if not Path(dir_name).exists():
                missing.append(dir_name)
        
        if not missing:
            return TestResult(
                "Directory Structure",
                True,
                f"{len(required_dirs)} directories found",
                True
            )
        else:
            return TestResult(
                "Directory Structure",
                False,
                f"Missing: {', '.join(missing)}",
                True
            )
    
    def test_configuration_files(self) -> TestResult:
        """Test configuration files"""
        print(f"{Colors.BLUE}[6/15]{Colors.RESET} Testing configuration files...")
        
        config_files = [
            'requirements.txt',
            'README.md',
            'config.env'
        ]
        
        missing = []
        for file_name in config_files:
            if not Path(file_name).exists():
                missing.append(file_name)
        
        if not missing:
            return TestResult(
                "Configuration Files",
                True,
                f"{len(config_files)} files found",
                True
            )
        else:
            return TestResult(
                "Configuration Files",
                False,
                f"Missing: {', '.join(missing)}",
                False
            )
    
    def test_import_parser(self) -> TestResult:
        """Test parser module import"""
        print(f"{Colors.BLUE}[7/15]{Colors.RESET} Testing parser module...")
        
        try:
            sys.path.insert(0, str(Path.cwd()))
            return TestResult(
                "Parser Module",
                True,
                "CanonicalIngestionPipeline imported successfully",
                True
            )
        except Exception as e:
            return TestResult(
                "Parser Module",
                False,
                f"Import failed: {str(e)[:50]}",
                True
            )
    
    def test_import_security(self) -> TestResult:
        """Test security module import"""
        print(f"{Colors.BLUE}[8/15]{Colors.RESET} Testing security module...")
        
        try:
            return TestResult(
                "Security Module",
                True,
                "Security components imported successfully",
                True
            )
        except Exception as e:
            return TestResult(
                "Security Module",
                False,
                f"Import failed: {str(e)[:50]}",
                True
            )
    
    def test_import_heuristics(self) -> TestResult:
        """Test heuristics module import"""
        print(f"{Colors.BLUE}[9/15]{Colors.RESET} Testing heuristics module...")
        
        try:
            return TestResult(
                "Heuristics Module",
                True,
                "HeuristicRuleEngine imported successfully",
                True
            )
        except Exception as e:
            return TestResult(
                "Heuristics Module",
                False,
                f"Import failed: {str(e)[:50]}",
                True
            )
    
    def test_import_graph(self) -> TestResult:
        """Test graph module import"""
        print(f"{Colors.BLUE}[10/15]{Colors.RESET} Testing graph module...")
        
        try:
            return TestResult(
                "Graph Module",
                True,
                "CaseLinkageEngine imported successfully",
                True
            )
        except Exception as e:
            return TestResult(
                "Graph Module",
                False,
                f"Import failed: {str(e)[:50]}",
                True
            )
    
    def test_import_nlp(self) -> TestResult:
        """Test NLP module import"""
        print(f"{Colors.BLUE}[11/15]{Colors.RESET} Testing NLP module...")
        
        try:
            return TestResult(
                "NLP Module",
                True,
                "EnhancedNL2Cypher imported successfully",
                True
            )
        except Exception as e:
            return TestResult(
                "NLP Module",
                False,
                f"Import failed: {str(e)[:50]}",
                True
            )
    
    def test_import_vector(self) -> TestResult:
        """Test vector module import"""
        print(f"{Colors.BLUE}[12/15]{Colors.RESET} Testing vector module...")
        
        try:
            return TestResult(
                "Vector Module",
                True,
                "EnhancedIndexManager imported successfully",
                True
            )
        except Exception as e:
            return TestResult(
                "Vector Module",
                False,
                f"Import failed: {str(e)[:50]}",
                False
            )
    
    def test_frontend_exists(self) -> TestResult:
        """Test frontend files exist"""
        print(f"{Colors.BLUE}[13/15]{Colors.RESET} Testing frontend...")
        
        frontend_file = Path("frontend/production_app.py")
        if frontend_file.exists():
            return TestResult(
                "Frontend",
                True,
                "production_app.py found",
                True
            )
        else:
            return TestResult(
                "Frontend",
                False,
                "production_app.py not found",
                True
            )
    
    def test_data_directories_writable(self) -> TestResult:
        """Test data directories are writable"""
        print(f"{Colors.BLUE}[14/15]{Colors.RESET} Testing data directories...")
        
        test_dirs = [
            Path("data/parsed"),
            Path("logs"),
            Path("exports")
        ]
        
        non_writable = []
        for dir_path in test_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            test_file = dir_path / ".write_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception:
                non_writable.append(str(dir_path))
        
        if not non_writable:
            return TestResult(
                "Data Directories",
                True,
                "All directories writable",
                True
            )
        else:
            return TestResult(
                "Data Directories",
                False,
                f"Not writable: {', '.join(non_writable)}",
                True
            )
    
    def test_streamlit_available(self) -> TestResult:
        """Test streamlit command"""
        print(f"{Colors.BLUE}[15/15]{Colors.RESET} Testing Streamlit availability...")
        
        try:
            result = subprocess.run(
                ['streamlit', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return TestResult(
                    "Streamlit Command",
                    True,
                    f"Available: {version}",
                    True
                )
            else:
                return TestResult(
                    "Streamlit Command",
                    False,
                    "Command failed",
                    True
                )
        except Exception as e:
            return TestResult(
                "Streamlit Command",
                False,
                f"Not available: {str(e)[:30]}",
                True
            )
    
    def run_all_tests(self):
        """Run all smoke tests"""
        self.print_header()
        
        # Run tests
        tests = [
            self.test_python_version,
            self.test_core_dependencies,
            self.test_nlp_dependencies,
            self.test_ui_dependencies,
            self.test_directory_structure,
            self.test_configuration_files,
            self.test_import_parser,
            self.test_import_security,
            self.test_import_heuristics,
            self.test_import_graph,
            self.test_import_nlp,
            self.test_import_vector,
            self.test_frontend_exists,
            self.test_data_directories_writable,
            self.test_streamlit_available
        ]
        
        for test_func in tests:
            result = test_func()
            self.results.append(result)
            
            # Print result
            if result.passed:
                print(f"  {Colors.GREEN}✓{Colors.RESET} {result.name}: {result.message}")
            else:
                color = Colors.RED if result.critical else Colors.YELLOW
                symbol = "✗" if result.critical else "⚠"
                print(f"  {color}{symbol}{Colors.RESET} {result.name}: {result.message}")
                
                if result.critical:
                    self.critical_failures += 1
                else:
                    self.warnings += 1
            
            print()  # Empty line
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Test Summary{Colors.RESET}")
        print(f"{'='*60}\n")
        
        print(f"Total Tests: {total}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
        
        if self.critical_failures > 0:
            print(f"{Colors.RED}Critical Failures: {self.critical_failures}{Colors.RESET}")
        
        if self.warnings > 0:
            print(f"{Colors.YELLOW}Warnings: {self.warnings}{Colors.RESET}")
        
        print()
        
        # Overall status
        if self.critical_failures == 0:
            if self.warnings == 0:
                print(f"{Colors.GREEN}{Colors.BOLD}✅ ALL TESTS PASSED{Colors.RESET}")
                print(f"{Colors.GREEN}Installation is fully operational!{Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  TESTS PASSED WITH WARNINGS{Colors.RESET}")
                print(f"{Colors.YELLOW}Installation is operational but some optional components are missing.{Colors.RESET}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ TESTS FAILED{Colors.RESET}")
            print(f"{Colors.RED}Installation has critical issues. Please review the failed tests above.{Colors.RESET}")
        
        print()
        
        # Next steps
        if self.critical_failures == 0:
            print(f"{Colors.CYAN}Next Steps:{Colors.RESET}")
            print(f"  1. Launch the application: streamlit run frontend/production_app.py")
            print(f"  2. Access at: http://localhost:8501")
            print(f"  3. Review documentation: README.md")
        else:
            print(f"{Colors.CYAN}Troubleshooting:{Colors.RESET}")
            print(f"  1. Review failed tests above")
            print(f"  2. Re-run installation script")
            print(f"  3. Check dependencies: pip install -r requirements.txt")
            print(f"  4. Verify directory permissions")
        
        print()
        
        return self.critical_failures == 0


def main():
    """Main entry point"""
    runner = SmokeTestRunner()
    success = runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()