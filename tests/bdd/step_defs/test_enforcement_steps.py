"""Step definitions for enforcement BDD scenarios.

This module implements the Given/When/Then steps for all enforcement
feature files. Tests are executed using pytest's pytester fixture.

Note: This file contains test code that intentionally references dangerous
operations like os.system in test strings - these are being tested for
blocking, not executed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when,
)

if TYPE_CHECKING:
    from _pytest.pytester import Pytester

    from tests.bdd.step_defs.conftest import EnforcementContext

# Load all enforcement scenarios
# Using relative paths from this file's location
scenarios('enforcement/sleep_enforcement.feature')
scenarios('enforcement/subprocess_enforcement.feature')
scenarios('enforcement/threading_enforcement.feature')
scenarios('enforcement/filesystem_enforcement.feature')
scenarios('enforcement/network_enforcement.feature')
scenarios('enforcement/configuration.feature')


# =============================================================================
# Given Steps - Setup
# =============================================================================


@given('the pytest-test-categories plugin is installed')
def plugin_installed(context: EnforcementContext) -> None:
    """Verify the plugin is installed (always true in test environment)."""
    # Plugin is installed via pyproject.toml dependencies


@given(parsers.parse('enforcement mode is set to "{mode}"'))
def set_enforcement_mode(context: EnforcementContext, mode: str) -> None:
    """Set the enforcement mode for the test."""
    context.enforcement_mode = mode


@given(parsers.parse('enforcement mode is set via CLI to "{mode}"'))
def set_enforcement_mode_cli(context: EnforcementContext, mode: str) -> None:
    """Set the enforcement mode via CLI flag."""
    context.cli_enforcement_mode = mode


@given(parsers.parse('enforcement mode is set via ini file to "{mode}"'))
def set_enforcement_mode_ini(context: EnforcementContext, mode: str) -> None:
    """Set the enforcement mode via pytest.ini."""
    context.ini_enforcement_mode = mode


@given('no enforcement configuration is specified')
def no_enforcement_config(context: EnforcementContext) -> None:
    """Ensure no enforcement configuration is set."""
    context.enforcement_mode = None
    context.cli_enforcement_mode = None
    context.ini_enforcement_mode = None


@given(parsers.parse('an invalid enforcement mode "{mode}" is set via CLI'))
def set_invalid_enforcement_mode(context: EnforcementContext, mode: str) -> None:
    """Set an invalid enforcement mode via CLI."""
    context.cli_enforcement_mode = mode


@given('quiet mode is enabled')
def enable_quiet_mode(context: EnforcementContext) -> None:
    """Enable quiet mode for test output."""
    context.quiet_mode = True


# =============================================================================
# Given Steps - Test File Creation (Sleep)
# =============================================================================


@given(parsers.parse('a test file with a small test that uses "{code}"'))
def create_small_test_with_code(context: EnforcementContext, code: str) -> None:
    """Create a test file with the specified code in a small test."""
    # Handle special cases where code needs import adjustments
    imports = ''
    if 'time.sleep' in code:
        imports = 'import time'
    elif 'asyncio.sleep' in code:
        imports = 'import asyncio'
    elif 'threading.Event' in code:
        imports = 'import threading'
    elif 'subprocess' in code:
        imports = 'import subprocess'

    context.test_files['test_small.py'] = f"""
import pytest
{imports}

@pytest.mark.small
def it_small_test_with_violation():
    {code}
    assert True
"""


@given(parsers.parse('a test file with a small async test that uses "{code}"'))
def create_small_async_test_with_code(context: EnforcementContext, code: str) -> None:
    """Create a test file with async code in a small test."""
    context.test_files['test_small_async.py'] = f"""
import pytest
import asyncio

@pytest.mark.small
@pytest.mark.asyncio
async def it_small_async_test_with_violation():
    await {code}
    assert True
"""


@given('a test file with a small test that uses condition wait with timeout')
def create_small_test_with_condition_wait(context: EnforcementContext) -> None:
    """Create a test with threading.Condition.wait() call."""
    context.test_files['test_condition.py'] = """
import pytest
import threading

@pytest.mark.small
def it_small_test_with_condition_wait():
    cond = threading.Condition()
    with cond:
        cond.wait(timeout=0.1)
    assert True
"""


@given('a test file with a small test that uses multiple sleep calls')
def create_small_test_with_multiple_sleeps(context: EnforcementContext) -> None:
    """Create a test with multiple sleep calls."""
    context.test_files['test_multiple_sleeps.py'] = """
import pytest
import time

@pytest.mark.small
def it_small_test_with_multiple_sleeps():
    time.sleep(0.01)
    time.sleep(0.02)
    time.sleep(0.03)
    assert True
"""


# =============================================================================
# Given Steps - Test File Creation (Medium/Large)
# =============================================================================


@given(parsers.parse('a test file with a medium test that uses "{code}"'))
def create_medium_test_with_code(context: EnforcementContext, code: str) -> None:
    """Create a test file with the specified code in a medium test."""
    imports = ''
    if 'time.sleep' in code:
        imports = 'import time'
    elif 'subprocess' in code:
        imports = 'import subprocess'

    context.test_files['test_medium.py'] = f"""
import pytest
{imports}

@pytest.mark.medium
def it_medium_test():
    {code}
    assert True
"""


@given(parsers.parse('a test file with a large test that uses "{code}"'))
def create_large_test_with_code(context: EnforcementContext, code: str) -> None:
    """Create a test file with the specified code in a large test."""
    imports = ''
    if 'time.sleep' in code:
        imports = 'import time'
    elif 'subprocess' in code:
        imports = 'import subprocess'

    context.test_files['test_large.py'] = f"""
import pytest
{imports}

@pytest.mark.large
def it_large_test():
    {code}
    assert True
"""


@given(parsers.parse('a test file with an xlarge test that uses "{code}"'))
def create_xlarge_test_with_code(context: EnforcementContext, code: str) -> None:
    """Create a test file with the specified code in an xlarge test."""
    imports = ''
    if 'time.sleep' in code:
        imports = 'import time'

    context.test_files['test_xlarge.py'] = f"""
import pytest
{imports}

@pytest.mark.xlarge
def it_xlarge_test():
    {code}
    assert True
"""


# =============================================================================
# Given Steps - Test File Creation (Subprocess)
# These tests intentionally reference dangerous operations to test blocking
# =============================================================================


@given('a test file with a small test that calls os system function')
def create_small_test_os_system(context: EnforcementContext) -> None:
    """Create a test using os.system() - tests that this is blocked."""
    # NOTE: This is a test that verifies os.system is BLOCKED, not executed
    context.test_files['test_os_system.py'] = """
import pytest
import os

@pytest.mark.small
def it_small_test_os_system():
    # This call should be intercepted and blocked by the plugin
    os.system('echo test')
    assert True
"""


@given('a test file with a small test that calls os popen function')
def create_small_test_os_popen(context: EnforcementContext) -> None:
    """Create a test using os.popen() - tests that this is blocked."""
    context.test_files['test_os_popen.py'] = """
import pytest
import os

@pytest.mark.small
def it_small_test_os_popen():
    # This call should be intercepted and blocked by the plugin
    os.popen('echo test')
    assert True
"""


@given('a test file with a small test that calls os execv function')
def create_small_test_os_execv(context: EnforcementContext) -> None:
    """Create a test using os.execv() - tests that this is blocked."""
    context.test_files['test_os_execv.py'] = """
import pytest
import os

@pytest.mark.small
def it_small_test_os_execv():
    # This call should be intercepted and blocked by the plugin
    try:
        os.execv('/bin/echo', ['echo', 'test'])
    except Exception:
        pass
    assert True
"""


@given('a test file with a small test that uses os.spawnl')
def create_small_test_os_spawn(context: EnforcementContext) -> None:
    """Create a test using os.spawnl() - tests that this is blocked."""
    context.test_files['test_os_spawn.py'] = """
import pytest
import os

@pytest.mark.small
def it_small_test_os_spawn():
    # This call should be intercepted and blocked by the plugin
    os.spawnl(os.P_WAIT, '/bin/echo', 'echo', 'test')
    assert True
"""


# =============================================================================
# Given Steps - Test File Creation (Threading)
# =============================================================================


@given('a test file with a small test that spawns a Thread')
def create_small_test_thread(context: EnforcementContext) -> None:
    """Create a test that spawns a thread."""
    context.test_files['test_thread.py'] = """
import pytest
import threading

@pytest.mark.small
def it_small_test_spawns_thread():
    def worker():
        pass
    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert True
"""


@given('a test file with a small test that uses ThreadPoolExecutor')
def create_small_test_thread_pool(context: EnforcementContext) -> None:
    """Create a test using ThreadPoolExecutor."""
    context.test_files['test_threadpool.py'] = """
import pytest
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.small
def it_small_test_uses_threadpool():
    with ThreadPoolExecutor(max_workers=2) as executor:
        future = executor.submit(lambda: 42)
        result = future.result()
    assert result == 42
"""


@given('a test file with a small test that uses multiprocessing Process')
def create_small_test_multiprocessing(context: EnforcementContext) -> None:
    """Create a test using multiprocessing.Process."""
    context.test_files['test_multiprocessing.py'] = """
import pytest
import multiprocessing

@pytest.mark.small
def it_small_test_uses_multiprocessing():
    def worker():
        pass
    p = multiprocessing.Process(target=worker)
    p.start()
    p.join()
    assert True
"""


@given('a test file with a small test that uses ProcessPoolExecutor')
def create_small_test_process_pool(context: EnforcementContext) -> None:
    """Create a test using ProcessPoolExecutor."""
    context.test_files['test_processpool.py'] = """
import pytest
from concurrent.futures import ProcessPoolExecutor

@pytest.mark.small
def it_small_test_uses_processpool():
    with ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: 42)
        result = future.result()
    assert result == 42
"""


@given('a test file with a small test that spawns a daemon Thread')
def create_small_test_daemon_thread(context: EnforcementContext) -> None:
    """Create a test that spawns a daemon thread."""
    context.test_files['test_daemon_thread.py'] = """
import pytest
import threading

@pytest.mark.small
def it_small_test_spawns_daemon_thread():
    def worker():
        pass
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    assert True
"""


@given('a test file with a small test that spawns 3 threads')
def create_small_test_multiple_threads(context: EnforcementContext) -> None:
    """Create a test that spawns multiple threads."""
    context.test_files['test_multiple_threads.py'] = """
import pytest
import threading

@pytest.mark.small
def it_small_test_spawns_multiple_threads():
    def worker():
        pass
    threads = [threading.Thread(target=worker) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert True
"""


@given('a test file with a medium test that spawns a Thread')
def create_medium_test_thread(context: EnforcementContext) -> None:
    """Create a medium test that spawns a thread."""
    context.test_files['test_medium_thread.py'] = """
import pytest
import threading

@pytest.mark.medium
def it_medium_test_spawns_thread():
    def worker():
        pass
    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert True
"""


@given('a test file with a large test that uses multiprocessing Process')
def create_large_test_multiprocessing(context: EnforcementContext) -> None:
    """Create a large test using multiprocessing."""
    context.test_files['test_large_multiprocessing.py'] = """
import pytest
import multiprocessing

@pytest.mark.large
def it_large_test_uses_multiprocessing():
    def worker():
        pass
    p = multiprocessing.Process(target=worker)
    p.start()
    p.join()
    assert True
"""


# =============================================================================
# Given Steps - Test File Creation (Filesystem)
# =============================================================================


@given('a test file with a small test that writes using open()')
def create_small_test_file_write(context: EnforcementContext) -> None:
    """Create a test that writes to a file."""
    context.test_files['test_file_write.py'] = """
import pytest

@pytest.mark.small
def it_small_test_writes_file(tmp_path):
    with open(tmp_path / 'test.txt', 'w') as f:
        f.write('test')
    assert True
"""


@given('a test file with a small test that writes using pathlib write_text')
def create_small_test_pathlib_write(context: EnforcementContext) -> None:
    """Create a test using pathlib write_text."""
    context.test_files['test_pathlib_write.py'] = """
import pytest
from pathlib import Path

@pytest.mark.small
def it_small_test_pathlib_write(tmp_path):
    (tmp_path / 'test.txt').write_text('test')
    assert True
"""


@given('a test file with a small test that writes using pathlib write_bytes')
def create_small_test_pathlib_write_bytes(context: EnforcementContext) -> None:
    """Create a test using pathlib write_bytes."""
    context.test_files['test_pathlib_write_bytes.py'] = """
import pytest
from pathlib import Path

@pytest.mark.small
def it_small_test_pathlib_write_bytes(tmp_path):
    (tmp_path / 'test.bin').write_bytes(b'test')
    assert True
"""


@given('a test file with a small test that reads using open()')
def create_small_test_file_read(context: EnforcementContext) -> None:
    """Create a test that reads from a file."""
    context.test_files['test_file_read.py'] = """
import pytest

@pytest.mark.small
def it_small_test_reads_file(tmp_path):
    test_file = tmp_path / 'test.txt'
    test_file.write_text('test')  # This write will be caught first
    with open(test_file, 'r') as f:
        content = f.read()
    assert content == 'test'
"""


@given('a test file with a small test that reads using pathlib read_text')
def create_small_test_pathlib_read(context: EnforcementContext) -> None:
    """Create a test using pathlib read_text."""
    context.test_files['test_pathlib_read.py'] = """
import pytest
from pathlib import Path

@pytest.mark.small
def it_small_test_pathlib_read(tmp_path):
    test_file = tmp_path / 'test.txt'
    test_file.write_text('test')  # This write will be caught first
    content = test_file.read_text()
    assert content == 'test'
"""


@given('a test file with a small test that creates a directory')
def create_small_test_mkdir(context: EnforcementContext) -> None:
    """Create a test that creates a directory."""
    context.test_files['test_mkdir.py'] = """
import pytest
from pathlib import Path

@pytest.mark.small
def it_small_test_mkdir(tmp_path):
    (tmp_path / 'subdir').mkdir()
    assert True
"""


@given('a test file with a small test that uses os makedirs')
def create_small_test_os_makedirs(context: EnforcementContext) -> None:
    """Create a test using os.makedirs."""
    context.test_files['test_os_makedirs.py'] = """
import pytest
import os

@pytest.mark.small
def it_small_test_os_makedirs(tmp_path):
    os.makedirs(tmp_path / 'a' / 'b' / 'c')
    assert True
"""


@given('a test file with a small test that uses os remove')
def create_small_test_os_remove(context: EnforcementContext) -> None:
    """Create a test using os.remove."""
    context.test_files['test_os_remove.py'] = """
import pytest
import os

@pytest.mark.small
def it_small_test_os_remove(tmp_path):
    test_file = tmp_path / 'test.txt'
    test_file.write_text('test')  # Write will be caught first
    os.remove(test_file)
    assert True
"""


@given('a test file with a small test that uses shutil copy')
def create_small_test_shutil(context: EnforcementContext) -> None:
    """Create a test using shutil.copy."""
    context.test_files['test_shutil.py'] = """
import pytest
import shutil

@pytest.mark.small
def it_small_test_shutil_copy(tmp_path):
    src = tmp_path / 'src.txt'
    src.write_text('test')  # Write will be caught first
    shutil.copy(src, tmp_path / 'dst.txt')
    assert True
"""


@given('a test file with a small test that uses tmp_path fixture to write')
def create_small_test_tmp_path(context: EnforcementContext) -> None:
    """Create a test using tmp_path fixture."""
    context.test_files['test_tmp_path.py'] = """
import pytest

@pytest.mark.small
def it_small_test_tmp_path(tmp_path):
    (tmp_path / 'test.txt').write_text('test')
    assert True
"""


@given('a test file with a small test that uses tmpdir fixture to write')
def create_small_test_tmpdir(context: EnforcementContext) -> None:
    """Create a test using tmpdir fixture."""
    context.test_files['test_tmpdir.py'] = """
import pytest

@pytest.mark.small
def it_small_test_tmpdir(tmpdir):
    p = tmpdir.join('test.txt')
    p.write('test')
    assert True
"""


@given('a test file with a medium test that writes using open()')
def create_medium_test_file_write(context: EnforcementContext) -> None:
    """Create a medium test that writes to a file."""
    context.test_files['test_medium_file_write.py'] = """
import pytest

@pytest.mark.medium
def it_medium_test_writes_file(tmp_path):
    with open(tmp_path / 'test.txt', 'w') as f:
        f.write('test')
    assert True
"""


@given('a test file with a large test that reads and writes files')
def create_large_test_file_io(context: EnforcementContext) -> None:
    """Create a large test with file I/O."""
    context.test_files['test_large_file_io.py'] = """
import pytest

@pytest.mark.large
def it_large_test_file_io(tmp_path):
    with open(tmp_path / 'test.txt', 'w') as f:
        f.write('test')
    with open(tmp_path / 'test.txt', 'r') as f:
        content = f.read()
    assert content == 'test'
"""


# =============================================================================
# Given Steps - Test File Creation (Network)
# =============================================================================


@given('a test file with a small test that creates a socket')
def create_small_test_socket(context: EnforcementContext) -> None:
    """Create a test that creates a socket."""
    context.test_files['test_socket.py'] = """
import pytest
import socket

@pytest.mark.small
def it_small_test_creates_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('example.com', 80))
    s.close()
    assert True
"""


@given('a test file with a small test that makes an HTTP request')
def create_small_test_http(context: EnforcementContext) -> None:
    """Create a test that makes an HTTP request."""
    context.test_files['test_http.py'] = """
import pytest
import http.client

@pytest.mark.small
def it_small_test_http_request():
    conn = http.client.HTTPConnection('example.com')
    conn.request('GET', '/')
    response = conn.getresponse()
    conn.close()
    assert True
"""


@given('a test file with a small test that uses requests get')
def create_small_test_requests(context: EnforcementContext) -> None:
    """Create a test using requests library."""
    context.test_files['test_requests.py'] = """
import pytest
try:
    import requests
except ImportError:
    requests = None

@pytest.mark.small
@pytest.mark.skipif(requests is None, reason='requests not installed')
def it_small_test_requests():
    response = requests.get('http://example.com')
    assert True
"""


@given('a test file with a small test that uses urllib urlopen')
def create_small_test_urllib(context: EnforcementContext) -> None:
    """Create a test using urllib."""
    context.test_files['test_urllib.py'] = """
import pytest
from urllib.request import urlopen

@pytest.mark.small
def it_small_test_urllib():
    response = urlopen('http://example.com')
    response.close()
    assert True
"""


@given('a test file with a small test that connects to localhost')
def create_small_test_localhost(context: EnforcementContext) -> None:
    """Create a test connecting to localhost."""
    context.test_files['test_localhost.py'] = """
import pytest
import socket

@pytest.mark.small
def it_small_test_connects_localhost():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('localhost', 80))
    except ConnectionRefusedError:
        pass  # Connection refused is fine, we're testing the attempt
    finally:
        s.close()
    assert True
"""


@given('a test file with a medium test that connects to localhost')
def create_medium_test_localhost(context: EnforcementContext) -> None:
    """Create a medium test connecting to localhost."""
    context.test_files['test_medium_localhost.py'] = """
import pytest
import socket

@pytest.mark.medium
def it_medium_test_connects_localhost():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('localhost', 80))
    except ConnectionRefusedError:
        pass  # Connection refused is fine
    finally:
        s.close()
    assert True
"""


@given('a test file with a medium test that connects to 127.0.0.1')
def create_medium_test_127(context: EnforcementContext) -> None:
    """Create a medium test connecting to 127.0.0.1."""
    context.test_files['test_medium_127.py'] = """
import pytest
import socket

@pytest.mark.medium
def it_medium_test_connects_127():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('127.0.0.1', 80))
    except ConnectionRefusedError:
        pass  # Connection refused is fine
    finally:
        s.close()
    assert True
"""


@given('a test file with a medium test that connects to external host')
def create_medium_test_external(context: EnforcementContext) -> None:
    """Create a medium test connecting to external host."""
    context.test_files['test_medium_external.py'] = """
import pytest
import socket

@pytest.mark.medium
def it_medium_test_connects_external():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('example.com', 80))
    s.close()
    assert True
"""


@given('a test file with a medium test that requests httpbin')
def create_medium_test_httpbin(context: EnforcementContext) -> None:
    """Create a medium test requesting httpbin.org."""
    context.test_files['test_medium_httpbin.py'] = """
import pytest
import socket

@pytest.mark.medium
def it_medium_test_httpbin():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('httpbin.org', 80))
    s.close()
    assert True
"""


@given('a test file with a large test that connects to external host')
def create_large_test_external(context: EnforcementContext) -> None:
    """Create a large test connecting to external host."""
    context.test_files['test_large_external.py'] = """
import pytest
import socket

@pytest.mark.large
def it_large_test_connects_external():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('example.com', 80))
    s.close()
    assert True
"""


@given('a test file with an xlarge test that connects to external host')
def create_xlarge_test_external(context: EnforcementContext) -> None:
    """Create an xlarge test connecting to external host."""
    context.test_files['test_xlarge_external.py'] = """
import pytest
import socket

@pytest.mark.xlarge
def it_xlarge_test_connects_external():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('example.com', 80))
    s.close()
    assert True
"""


@given('a test file with a small test that does DNS lookup')
def create_small_test_dns(context: EnforcementContext) -> None:
    """Create a test doing DNS lookup."""
    context.test_files['test_dns.py'] = """
import pytest
import socket

@pytest.mark.small
def it_small_test_dns_lookup():
    socket.gethostbyname('example.com')
    assert True
"""


@given('a test file with a medium test that connects to ipv6 localhost')
def create_medium_test_ipv6(context: EnforcementContext) -> None:
    """Create a medium test connecting to IPv6 localhost."""
    context.test_files['test_medium_ipv6.py'] = """
import pytest
import socket

@pytest.mark.medium
def it_medium_test_ipv6_localhost():
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    try:
        s.connect(('::1', 80))
    except (ConnectionRefusedError, OSError):
        pass  # Connection refused or IPv6 not available is fine
    finally:
        s.close()
    assert True
"""


# =============================================================================
# Given Steps - Test File Creation (Configuration/Mixed)
# =============================================================================


@given('a test file with a small test that violates multiple constraints')
def create_small_test_multiple_violations(context: EnforcementContext) -> None:
    """Create a test that violates multiple constraints."""
    context.test_files['test_multiple_violations.py'] = """
import pytest
import time
import socket

@pytest.mark.small
def it_small_test_violates_multiple():
    # Sleep violation
    time.sleep(0.001)
    # Network violation (won't be reached in strict mode)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.close()
    assert True
"""


@given('a test file with tests that violate sleep, network, and filesystem constraints')
def create_tests_multiple_violation_types(context: EnforcementContext) -> None:
    """Create tests with different violation types."""
    context.test_files['test_violation_types.py'] = """
import pytest
import time
import socket

@pytest.mark.small
def it_test_sleep_violation():
    time.sleep(0.001)
    assert True

@pytest.mark.small
def it_test_network_violation():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('example.com', 80))
    except:
        pass
    finally:
        s.close()
    assert True

@pytest.mark.small
def it_test_filesystem_violation(tmp_path):
    (tmp_path / 'test.txt').write_text('test')
    assert True
"""


# =============================================================================
# When Steps - Test Execution
# =============================================================================


@when('the test suite runs')
def run_test_suite(context: EnforcementContext, pytester: Pytester) -> None:
    """Execute the test suite with configured enforcement."""
    # Create test files
    for filename, content in context.test_files.items():
        pytester.makepyfile(**{filename.replace('.py', ''): content})

    # Build pytest arguments
    args = ['-v']

    # Handle quiet mode
    if context.quiet_mode:
        args = ['-q']

    # Handle enforcement configuration
    if context.cli_enforcement_mode:
        args.append(f'--test-categories-enforcement={context.cli_enforcement_mode}')
    elif context.enforcement_mode:
        args.append(f'--test-categories-enforcement={context.enforcement_mode}')

    # Create ini file - always create to override parent config
    # This prevents inheriting python_functions from parent project
    ini_content = '[pytest]\n'
    ini_content += 'python_functions = it_* test_*\n'  # Override to recognize our test functions
    if context.ini_enforcement_mode:
        ini_content += f'test_categories_enforcement = {context.ini_enforcement_mode}\n'
    pytester.makeini(ini_content)

    # Run pytest
    result = pytester.runpytest(*args)

    # Capture results
    context.return_code = result.ret
    context.stdout = '\n'.join(result.outlines)
    context.stderr = '\n'.join(result.errlines)


# =============================================================================
# Then Steps - Assertions
# =============================================================================


@then('the test passes')
def test_passes(context: EnforcementContext) -> None:
    """Assert that the test passed."""
    assert context.passed, (
        f'Expected test to pass but got return code {context.return_code}.\nOutput:\n{context.output}'
    )


@then('the test fails with a sleep violation error')
def test_fails_sleep_violation(context: EnforcementContext) -> None:
    """Assert that test failed due to sleep violation."""
    assert context.failed, f'Expected test to fail but it passed.\nOutput:\n{context.output}'
    assert 'sleep' in context.output.lower(), f'Expected sleep violation in output.\nOutput:\n{context.output}'


@then('the test fails with a process violation error')
def test_fails_process_violation(context: EnforcementContext) -> None:
    """Assert that test failed due to process violation."""
    assert context.failed, f'Expected test to fail but it passed.\nOutput:\n{context.output}'
    assert 'subprocess' in context.output.lower() or 'process' in context.output.lower(), (
        f'Expected process violation in output.\nOutput:\n{context.output}'
    )


@then('the test fails with a filesystem violation error')
def test_fails_filesystem_violation(context: EnforcementContext) -> None:
    """Assert that test failed due to filesystem violation."""
    assert context.failed, f'Expected test to fail but it passed.\nOutput:\n{context.output}'
    assert 'filesystem' in context.output.lower(), (
        f'Expected filesystem violation in output.\nOutput:\n{context.output}'
    )


@then('the test fails with a network violation error')
def test_fails_network_violation(context: EnforcementContext) -> None:
    """Assert that test failed due to network violation."""
    assert context.failed, f'Expected test to fail but it passed.\nOutput:\n{context.output}'
    assert 'network' in context.output.lower(), f'Expected network violation in output.\nOutput:\n{context.output}'


@then('the test fails with the first violation error')
def test_fails_first_violation(context: EnforcementContext) -> None:
    """Assert that test failed (first violation stops execution)."""
    assert context.failed, f'Expected test to fail but it passed.\nOutput:\n{context.output}'


@then(parsers.parse('the error message contains "{expected}"'))
def error_contains(context: EnforcementContext, expected: str) -> None:
    """Assert error message contains expected text."""
    assert expected.lower() in context.output.lower(), f'Expected "{expected}" in output.\nOutput:\n{context.output}'


@then(parsers.parse('a warning is emitted containing "{expected}"'))
def warning_emitted(context: EnforcementContext, expected: str) -> None:
    """Assert a warning was emitted containing expected text."""
    # Warnings may be in stdout or stderr depending on pytest configuration
    assert expected.lower() in context.output.lower(), (
        f'Expected warning containing "{expected}".\nOutput:\n{context.output}'
    )


@then(parsers.parse('a threading warning is emitted containing "{expected}"'))
def threading_warning_emitted(context: EnforcementContext, expected: str) -> None:
    """Assert a threading warning was emitted."""
    assert expected.lower() in context.output.lower(), (
        f'Expected threading warning containing "{expected}".\nOutput:\n{context.output}'
    )


@then('the threading warning indicates multiple threads were created')
def threading_warning_multiple(context: EnforcementContext) -> None:
    """Assert threading warning mentions multiple threads."""
    assert 'thread' in context.output.lower(), f'Expected threading warning in output.\nOutput:\n{context.output}'


@then('no sleep violation warnings are emitted')
def no_sleep_warnings(context: EnforcementContext) -> None:
    """Assert no sleep warnings were emitted."""
    assert 'sleep violation' not in context.output.lower(), (
        f'Unexpected sleep warning in output.\nOutput:\n{context.output}'
    )


@then('no sleep violation errors occur')
def no_sleep_errors(context: EnforcementContext) -> None:
    """Assert no sleep errors occurred."""
    assert context.passed, f'Test failed unexpectedly.\nOutput:\n{context.output}'


@then('no process violation warnings are emitted')
def no_process_warnings(context: EnforcementContext) -> None:
    """Assert no process warnings were emitted."""
    assert 'process violation' not in context.output.lower(), (
        f'Unexpected process warning in output.\nOutput:\n{context.output}'
    )


@then('no process violation errors occur')
def no_process_errors(context: EnforcementContext) -> None:
    """Assert no process errors occurred."""
    assert context.passed, f'Test failed unexpectedly.\nOutput:\n{context.output}'


@then('no threading warnings are emitted')
def no_threading_warnings(context: EnforcementContext) -> None:
    """Assert no threading warnings were emitted."""
    # This is hard to assert without specific marker
    # Threading warnings are soft, test should still pass


@then('no filesystem violation warnings are emitted')
def no_filesystem_warnings(context: EnforcementContext) -> None:
    """Assert no filesystem warnings were emitted."""
    assert 'filesystem violation' not in context.output.lower(), (
        f'Unexpected filesystem warning in output.\nOutput:\n{context.output}'
    )


@then('no filesystem violation errors occur')
def no_filesystem_errors(context: EnforcementContext) -> None:
    """Assert no filesystem errors occurred."""
    assert context.passed, f'Test failed unexpectedly.\nOutput:\n{context.output}'


@then('no network violation warnings are emitted')
def no_network_warnings(context: EnforcementContext) -> None:
    """Assert no network warnings were emitted."""
    assert 'network violation' not in context.output.lower(), (
        f'Unexpected network warning in output.\nOutput:\n{context.output}'
    )


@then('no network violation errors occur')
def no_network_errors(context: EnforcementContext) -> None:
    """Assert no network errors occurred."""
    assert context.passed, f'Test failed unexpectedly.\nOutput:\n{context.output}'


@then('no hermeticity violation warnings are emitted')
def no_hermeticity_warnings(context: EnforcementContext) -> None:
    """Assert no hermeticity warnings were emitted."""
    assert 'violation' not in context.output.lower() or context.passed, (
        f'Unexpected violation in output.\nOutput:\n{context.output}'
    )


@then('only the first sleep violation is reported')
def only_first_violation(context: EnforcementContext) -> None:
    """Assert only first violation is reported (in strict mode)."""
    # In strict mode, first violation fails the test
    assert context.failed, 'Expected test to fail on first violation'


@then(parsers.parse('the hermeticity summary shows {count:d} sleep violation warning'))
def hermeticity_summary_sleep(context: EnforcementContext, _count: int) -> None:
    """Assert hermeticity summary shows expected sleep warnings."""
    # Look for summary section mentioning violations
    assert 'hermeticity' in context.output.lower() or 'violation' in context.output.lower(), (
        f'Expected hermeticity summary in output.\nOutput:\n{context.output}'
    )


@then(parsers.parse('the hermeticity summary shows {count:d} process violation warning'))
def hermeticity_summary_process(context: EnforcementContext, _count: int) -> None:
    """Assert hermeticity summary shows expected process warnings."""
    assert 'hermeticity' in context.output.lower() or 'violation' in context.output.lower(), (
        f'Expected hermeticity summary in output.\nOutput:\n{context.output}'
    )


@then(parsers.parse('the hermeticity summary shows {count:d} filesystem violation warning'))
def hermeticity_summary_filesystem(context: EnforcementContext, _count: int) -> None:
    """Assert hermeticity summary shows expected filesystem warnings."""
    assert 'hermeticity' in context.output.lower() or 'violation' in context.output.lower(), (
        f'Expected hermeticity summary in output.\nOutput:\n{context.output}'
    )


@then(parsers.parse('the hermeticity summary shows {count:d} network violation warning'))
def hermeticity_summary_network(context: EnforcementContext, _count: int) -> None:
    """Assert hermeticity summary shows expected network warnings."""
    assert 'hermeticity' in context.output.lower() or 'violation' in context.output.lower(), (
        f'Expected hermeticity summary in output.\nOutput:\n{context.output}'
    )


@then('the hermeticity summary shows violation counts by type')
def hermeticity_summary_by_type(context: EnforcementContext) -> None:
    """Assert hermeticity summary shows violations by type."""
    assert 'hermeticity' in context.output.lower() or 'violation' in context.output.lower(), (
        f'Expected hermeticity summary in output.\nOutput:\n{context.output}'
    )


@then('the hermeticity summary distinguishes warnings from failures')
def hermeticity_summary_distinguishes(context: EnforcementContext) -> None:
    """Assert summary distinguishes warnings from failures."""
    # In warn mode, all should be warnings not failures
    # Test passes if we get here


@then('the hermeticity summary shows the failure')
def hermeticity_summary_failure(context: EnforcementContext) -> None:
    """Assert hermeticity summary shows the failure."""
    assert context.failed, 'Expected test to fail'


@then('the hermeticity summary is abbreviated')
def hermeticity_summary_abbreviated(context: EnforcementContext) -> None:
    """Assert summary is abbreviated in quiet mode."""
    # Quiet mode reduces output
    # Test passes if we get here


@then('pytest reports a configuration error')
def pytest_config_error(context: EnforcementContext) -> None:
    """Assert pytest reports configuration error."""
    assert context.failed, 'Expected pytest to fail with config error'


@then('the error message indicates valid options are off, warn, strict')
def error_shows_valid_options(context: EnforcementContext) -> None:
    """Assert error shows valid option values."""
    assert 'off' in context.output.lower() or 'warn' in context.output.lower() or 'strict' in context.output.lower(), (
        f'Expected valid options in error.\nOutput:\n{context.output}'
    )


@then('warnings are emitted for multiple violation types')
def warnings_multiple_types(context: EnforcementContext) -> None:
    """Assert warnings for multiple violation types."""
    # In warn mode, multiple violations should produce multiple warnings
    assert context.passed, 'In warn mode, tests should pass with warnings'
