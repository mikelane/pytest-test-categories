# Architecture

This section documents the architectural decisions and design of pytest-test-categories.

## Topics

```{toctree}
:maxdepth: 2

design-philosophy
hexagonal-architecture
adr-001-network-isolation
adr-002-filesystem-isolation
adr-003-process-isolation
adr-004-database-isolation
adr-005-sleep-isolation
```

## Design Documents

### [Design Philosophy](design-philosophy.md)

The core principles behind pytest-test-categories:
- The "no escape hatches" philosophy for small tests
- Why strict enforcement matters
- Trade-offs and design decisions
- Comparison with other approaches (pytest-socket, pyfakefs, freezegun)

### [Hexagonal Architecture](hexagonal-architecture.md)

How the codebase is structured for testability:
- Ports and adapters pattern explanation
- How it applies to the timer system and all blockers
- Benefits for testability (fast unit tests, separate integration tests)
- Code structure walkthrough

## Overview

pytest-test-categories follows **hexagonal architecture** (ports and adapters pattern) for testability and maintainability.

### Core Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Dependency Inversion**: Core logic depends on abstractions, not implementations
3. **Testability**: All components can be tested in isolation using test doubles

### Architecture Diagram

```
                    +---------------------+
                    |   pytest hooks      |
                    |   (plugin.py)       |
                    +----------+----------+
                               |
                    +----------v----------+
                    |      Services       |
                    | - timing_validation |
                    | - distribution      |
                    | - test_discovery    |
                    +----------+----------+
                               |
         +---------------------+---------------------+
         |                     |                     |
+--------v--------+   +--------v--------+   +--------v--------+
|     Ports       |   |     Types       |   |   Exceptions    |
| (interfaces)    |   | (domain models) |   |                 |
+-----------------+   +-----------------+   +-----------------+
         |
+--------v--------+
|    Adapters     |
| - pytest        |
| - network       |
| - filesystem    |
| - process       |
| - database      |
| - sleep         |
| - timers        |
+-----------------+
```

## Key Components

### Plugin Entry Point (`plugin.py`)

The main pytest plugin that:
- Registers pytest hooks
- Initializes plugin state
- Coordinates between services and adapters
- Acts as a thin orchestration layer (all business logic delegated to services)

### Ports (Interfaces)

Abstract interfaces defining contracts:

| Port | Purpose | Location |
|------|---------|----------|
| `TestTimer` | Timer interface for measuring test duration | `types.py` |
| `NetworkBlockerPort` | Interface for network blocking | `ports/network.py` |
| `FilesystemBlockerPort` | Interface for filesystem blocking | `ports/filesystem.py` |
| `ProcessBlockerPort` | Interface for subprocess blocking | `ports/process.py` |
| `DatabaseBlockerPort` | Interface for database connection blocking | `ports/database.py` |
| `SleepBlockerPort` | Interface for sleep call blocking | `ports/sleep.py` |
| `TestItemPort` | Abstract pytest.Item | `types.py` |
| `OutputWriterPort` | Terminal output | `types.py` |
| `WarningSystemPort` | Warning emission | `types.py` |
| `ConfigStatePort` | Plugin state access | `types.py` |

### Adapters (Implementations)

Concrete implementations of ports:

| Port | Production Adapter | Test Adapter |
|------|-------------------|--------------|
| `TestTimer` | `WallTimer` | `FakeTimer` |
| `NetworkBlockerPort` | `SocketPatchingNetworkBlocker` | `FakeNetworkBlocker` |
| `FilesystemBlockerPort` | `FilesystemPatchingBlocker` | `FakeFilesystemBlocker` |
| `ProcessBlockerPort` | `SubprocessPatchingBlocker` | `FakeProcessBlocker` |
| `DatabaseBlockerPort` | `DatabasePatchingBlocker` | `FakeDatabaseBlocker` |
| `SleepBlockerPort` | `SleepPatchingBlocker` | `FakeSleepBlocker` |

### Services

Business logic modules:
- `timing_validation`: Validates test timing constraints
- `distribution_validation`: Validates test distribution
- `test_discovery`: Discovers test sizes from markers
- `test_reporting`: Generates test size reports

### Types

Domain models:
- `TestSize`: Enum of test size categories (SMALL, MEDIUM, LARGE, XLARGE)
- `TimeLimit`: Immutable time limit configuration
- `DistributionStats`: Test distribution statistics
- `TimerState`: State machine states (READY, RUNNING, STOPPED)

### Exceptions

Custom exception hierarchy:
- `TimingViolationError`: Test exceeded time limit
- `HermeticityViolationError`: Test violated hermeticity (base class)
  - `NetworkAccessViolationError`: Test made unauthorized network request
  - `FilesystemAccessViolationError`: Test made unauthorized filesystem access
  - `SubprocessViolationError`: Test attempted to spawn subprocess
  - `DatabaseViolationError`: Test attempted database connection
  - `SleepViolationError`: Test called sleep function

## Architecture Decision Records (ADRs)

ADRs document significant architectural decisions with their context, decision, and consequences.

### Index of ADRs

| ADR | Title | Status | Summary |
|-----|-------|--------|---------|
| [ADR-001](adr-001-network-isolation.md) | Network Isolation | Proposed | Socket-level blocking for small tests, localhost-only for medium |
| [ADR-002](adr-002-filesystem-isolation.md) | Filesystem Isolation | Proposed | Comprehensive patching of file operations, tmp_path allowlisting |
| [ADR-003](adr-003-process-isolation.md) | Process Isolation | Implemented | Subprocess/os patching to block process spawning |
| [ADR-004](adr-004-database-isolation.md) | Database Isolation | Implemented | Database library patching including sqlite3, psycopg2, etc. |
| [ADR-005](adr-005-sleep-isolation.md) | Sleep Isolation | Accepted | time.sleep and asyncio.sleep blocking for small tests |

### ADR Status Meanings

- **Proposed**: Design documented, implementation in progress
- **Accepted**: Design approved, ready for implementation
- **Implemented**: Fully implemented and released
- **Superseded**: Replaced by a newer ADR
- **Deprecated**: No longer recommended

## Further Reading

- [Design Philosophy](design-philosophy.md) - Core principles and trade-offs
- [Hexagonal Architecture](hexagonal-architecture.md) - Detailed pattern explanation
- [Alistair Cockburn's Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) - Original pattern description
- [Google's Software Engineering at Google - Testing](https://abseil.io/resources/swe-book/html/ch11.html) - Test size philosophy source
