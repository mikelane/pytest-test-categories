# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Optimized plugin.py orchestration layer: reduced from 394 to 266 lines (32% reduction) by eliminating duplication and condensing docstrings (#45)
- Switch license to MIT

### Fixed
- Fixed test_base_classes_feature.py regex pattern to use re.search instead of re.match for better output matching
- Include pre-commit in lint reqs


## [0.1.0] - 2024-12-30
Initial release
