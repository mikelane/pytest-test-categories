# Architecture

This section documents the architectural decisions and design of pytest-test-categories.

## Topics

```{toctree}
:maxdepth: 2

adr-001-network-isolation
adr-002-filesystem-isolation
```

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
| - timers        |
+-----------------+
```

## Key Components

### Plugin Entry Point (`plugin.py`)

The main pytest plugin that:
- Registers pytest hooks
- Initializes plugin state
- Coordinates between services and adapters

### Ports (Interfaces)

Abstract interfaces defining contracts:
- `TestTimer`: Timer interface for measuring test duration
- `NetworkBlockerPort`: Interface for network blocking
- `FilesystemBlockerPort`: Interface for filesystem blocking (planned)

### Adapters (Implementations)

Concrete implementations of ports:
- `WallTimer`: Production timer using `time.perf_counter()`
- `FakeTimer`: Test timer with controllable time
- `SocketPatchingNetworkBlocker`: Production network blocker
- `FakeNetworkBlocker`: Test network blocker
- `FilesystemPatchingBlocker`: Production filesystem blocker (planned)
- `FakeFilesystemBlocker`: Test filesystem blocker (planned)

### Services

Business logic modules:
- `timing_validation`: Validates test timing constraints
- `distribution_validation`: Validates test distribution
- `test_discovery`: Discovers test sizes from markers
- `test_counting`: Counts tests by size category
- `test_reporting`: Generates test size reports

### Types

Domain models:
- `TestSize`: Enum of test size categories
- `TimeLimit`: Immutable time limit configuration
- `DistributionStats`: Test distribution statistics

### Exceptions

Custom exception hierarchy:
- `TimingViolationError`: Test exceeded time limit
- `HermeticityViolationError`: Test violated hermeticity (base class)
- `NetworkAccessViolationError`: Test made unauthorized network request
- `FilesystemAccessViolationError`: Test made unauthorized filesystem access (planned)

## Design Decisions

See the Architecture Decision Records (ADRs) for detailed reasoning behind key design decisions:

- [ADR-001: Network Isolation](adr-001-network-isolation.md)
- [ADR-002: Filesystem Isolation](adr-002-filesystem-isolation.md)
