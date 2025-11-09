# GitHub Projects Board Setup Guide

This document provides instructions for setting up the GitHub Projects board for pytest-test-categories to support our Agile development workflow.

## Overview

GitHub Projects provides a Kanban-style board for tracking issues, pull requests, and tasks. This guide walks through creating and configuring a project board that aligns with our development workflow.

## Creating the Project Board

### Step 1: Create a New Project

1. Navigate to the repository: https://github.com/mikelane/pytest-test-categories
2. Click on the **Projects** tab
3. Click **New project**
4. Choose **Board** layout
5. Name it: **pytest-test-categories Development Board**
6. Description: **Agile development workflow for pytest-test-categories**
7. Click **Create project**

### Step 2: Configure Project Settings

1. Click the **⋯** menu in the top right
2. Select **Settings**
3. Configure:
   - **Visibility**: Public (or Private if preferred)
   - **README**: Add project overview
   - **Automation**: Enable (we'll configure this later)

## Board Columns

Create the following columns to represent our workflow states:

### 1. Backlog

**Purpose**: Ideas and future work not yet ready for development

**Configuration**:
- **Automation**: None
- **Preset**: None

**Criteria for items**:
- Issues labeled with `triage`
- Not yet fully specified
- No clear acceptance criteria
- Future milestones

### 2. Ready

**Purpose**: Well-defined work ready to be picked up

**Configuration**:
- **Automation**: Move here when issue labeled `accepted`
- **Preset**: None

**Criteria for items**:
- Clear problem statement
- Acceptance criteria defined
- No blockers
- Prioritized
- Labeled with priority

### 3. In Progress

**Purpose**: Actively being worked on

**Configuration**:
- **Automation**:
  - Move here when issue labeled `in-progress`
  - Move here when PR is draft or opened
- **Preset**: In progress

**Criteria for items**:
- Assigned to a developer
- Work has started
- PR may or may not exist yet
- Labeled `in-progress`

### 4. Review

**Purpose**: Code complete, awaiting review

**Configuration**:
- **Automation**:
  - Move here when PR labeled `ready-for-review`
  - Move here when PR is marked ready for review (from draft)
- **Preset**: None

**Criteria for items**:
- PR opened and ready for review
- All CI checks passing
- Documentation updated
- Tests pass with 100% coverage
- PR template completed

### 5. Testing/QA

**Purpose**: Under final validation before merge

**Configuration**:
- **Automation**:
  - Move here when PR approved
- **Preset**: None

**Criteria for items**:
- Code review approved
- Manual testing if needed
- Final validation
- Ready to merge pending final checks

### 6. Done

**Purpose**: Completed work

**Configuration**:
- **Automation**:
  - Move here when issue closed
  - Move here when PR merged
- **Preset**: Done
- **Close issues**: Enabled

**Criteria for items**:
- PR merged to main
- Issue closed
- Deployed to production (for releases)
- Documented in CHANGELOG.md

### 7. Blocked

**Purpose**: Work that cannot proceed due to dependencies

**Configuration**:
- **Automation**: Move here when labeled `blocked`
- **Preset**: None

**Criteria for items**:
- Labeled `blocked`
- Clear blocker documented in comments
- Link to blocking issue/PR
- Escalation if blocked > 1 week

## Custom Fields

Add custom fields to track additional metadata:

### Priority

- **Type**: Single select
- **Options**:
  - 🔴 Critical
  - 🟠 High
  - 🟡 Medium
  - 🟢 Low

**Usage**: Synced with `priority-*` labels

### Size (Effort)

- **Type**: Single select
- **Options**:
  - XS (< 2 hours)
  - S (2-8 hours)
  - M (1-3 days)
  - L (3-7 days)
  - XL (> 1 week)

**Usage**: Estimated effort for planning

### Milestone

- **Type**: Single select
- **Options**: Synced with GitHub milestones
  - v1.0.0 - Stable Release
  - v1.1.0 - Parallel Execution
  - v1.2.0 - Dashboard Integration
  - v1.3.0 - Custom Categories
  - v2.0.0 - Advanced Analytics

**Usage**: Links work to roadmap milestones

### Area

- **Type**: Single select
- **Options**:
  - Plugin
  - Timing
  - Distribution
  - Reporting
  - CI/CD
  - Documentation
  - Infrastructure

**Usage**: Synced with `area:*` labels

### Type

- **Type**: Single select
- **Options**:
  - Bug
  - Feature
  - Documentation
  - Performance
  - Refactoring
  - Testing
  - Security

**Usage**: Synced with type labels

## Automation Rules

Configure automation to reduce manual work:

### Auto-add to Project

**Trigger**: Issue opened or PR opened
**Action**: Add to project in **Backlog** column

### Move to Ready

**Trigger**: Issue labeled `accepted`
**Action**: Move to **Ready** column

### Move to In Progress

**Triggers**:
- Issue labeled `in-progress`
- PR opened as draft
- Issue assigned to someone

**Action**: Move to **In Progress** column

### Move to Review

**Triggers**:
- PR marked as ready for review
- PR labeled `ready-for-review`

**Action**: Move to **Review** column

### Move to Testing

**Trigger**: PR approved by reviewer
**Action**: Move to **Testing/QA** column

### Move to Done

**Triggers**:
- Issue closed
- PR merged

**Action**: Move to **Done** column

### Move to Blocked

**Trigger**: Issue labeled `blocked`
**Action**: Move to **Blocked** column

## Views

Create multiple views for different perspectives:

### 1. Default Board View

**Layout**: Board
**Columns**: All workflow columns
**Filters**: None
**Sort**: Priority (high to low)

### 2. Current Sprint

**Layout**: Board
**Filters**:
- Status: Ready, In Progress, Review, Testing
- Milestone: Current sprint milestone

**Sort**: Priority

### 3. Backlog Refinement

**Layout**: Table
**Columns**:
- Title
- Priority
- Size
- Milestone
- Labels

**Filters**: Status = Backlog
**Sort**: Priority (high to low)

### 4. By Area

**Layout**: Board
**Group by**: Area
**Filters**: Status != Done
**Sort**: Priority

### 5. By Assignee

**Layout**: Table
**Group by**: Assignee
**Filters**: Status = In Progress or Review
**Sort**: Priority

## Workflow Process

### For Contributors

1. **Pick work from Ready column**
   - Choose highest priority item that matches your skills
   - Assign yourself to the issue
   - Issue automatically moves to **In Progress**

2. **During development**
   - Create feature branch
   - Open draft PR (automatically added to **In Progress**)
   - Keep PR updated with regular pushes

3. **Ready for review**
   - Mark PR as ready for review
   - PR automatically moves to **Review**
   - Request review from maintainers

4. **After review**
   - Address feedback
   - Push updates
   - Re-request review if needed

5. **After approval**
   - PR moves to **Testing/QA**
   - Wait for final checks
   - Maintainer merges
   - Issue/PR moves to **Done**

### For Maintainers

1. **Triage new issues**
   - Review issues in **Backlog**
   - Add labels (type, area, priority)
   - Request clarification if needed (`needs-info`)
   - Accept issues by labeling `accepted` → moves to **Ready**

2. **Review PRs**
   - Review PRs in **Review** column
   - Approve or request changes
   - Approved PRs move to **Testing/QA**

3. **Merge PRs**
   - PRs in **Testing/QA** are ready to merge
   - Merge using squash or merge commit
   - Verify moved to **Done**
   - Close related issues if not auto-closed

4. **Manage blocked items**
   - Review **Blocked** column weekly
   - Work to unblock or escalate
   - Update blocker status in comments

## Sprint Planning (Optional)

If using sprint cycles:

### Sprint Duration

- **Recommended**: 2 weeks
- **Planning**: First day of sprint
- **Review**: Last day of sprint
- **Retrospective**: Last day of sprint

### Sprint Milestones

Create sprint milestones:
- **Name**: Sprint [Number] - [Date Range]
- **Description**: Goals for this sprint
- **Due date**: Last day of sprint

### Sprint Planning Process

1. **Review velocity**: How much was completed in last sprint?
2. **Select work**: Pull items from **Ready** column
3. **Set milestone**: Assign to current sprint milestone
4. **Set capacity**: Don't over-commit
5. **Daily standup**: Review **In Progress** items
6. **Sprint review**: Demo completed work from **Done**
7. **Retrospective**: Discuss what went well, what to improve

## Metrics and Reporting

### Velocity Tracking

Track completed work per sprint:
- Count of issues closed
- Sum of story points (if using sizes)
- Trend over time

### Cycle Time

Measure time from **Ready** to **Done**:
- Identify bottlenecks
- Optimize slowest stages
- Target: < 7 days for small issues

### Lead Time

Measure time from **Backlog** to **Done**:
- Overall efficiency metric
- Includes triage and planning time

### Work In Progress (WIP) Limits

Set WIP limits per column to prevent bottlenecks:
- **In Progress**: Max 5 items (adjust based on team size)
- **Review**: Max 3 items
- **Testing**: Max 2 items

## Integration with Other Tools

### GitHub Actions

Link workflow runs to issues/PRs:
- CI status visible in project board
- Failed checks prevent moving to **Testing**

### Documentation

Link to documentation:
- ROADMAP.md for milestone planning
- CONTRIBUTING.md for workflow details
- Issue templates for creating work items

## Maintenance

### Weekly

- Review **Blocked** column
- Triage new issues in **Backlog**
- Update stale items
- Check WIP limits

### Monthly

- Review completed milestones
- Update roadmap if needed
- Archive old **Done** items
- Review and adjust automation rules

### Quarterly

- Review project board effectiveness
- Gather team feedback
- Adjust workflow if needed
- Update this documentation

## Best Practices

### Do's

✅ Keep items small and focused
✅ Update status regularly
✅ Link related issues and PRs
✅ Use labels consistently
✅ Keep **In Progress** column small
✅ Review **Blocked** items regularly
✅ Close items promptly when done

### Don'ts

❌ Don't skip columns in the workflow
❌ Don't have too many items in progress
❌ Don't let blocked items languish
❌ Don't create vague or unclear issues
❌ Don't bypass the review process
❌ Don't forget to update documentation

## Troubleshooting

### Items not moving automatically

- Check automation rules are enabled
- Verify labels are correct
- Check project settings
- Manually move if automation fails

### Too many items in one column

- Review WIP limits
- Identify bottleneck
- Allocate resources to clear backlog
- Consider parallel work streams

### Unclear priorities

- Review and update priority labels
- Communicate with team
- Align with roadmap milestones
- Discuss in sprint planning

## Getting Help

Questions about the project board?

- **Maintainers**: Comment on issues or PRs
- **Discussions**: [GitHub Discussions](https://github.com/mikelane/pytest-test-categories/discussions)
- **Documentation**: This file and CONTRIBUTING.md

---

*This board structure is based on Agile/Kanban principles and can be adapted to team needs.*
