# DESIGN DOCUMENTATION KNOWLEDGE BASE

**Generated:** 2026-03-04
**Commit:** Not available (working directory)
**Branch:** master

## OVERVIEW
Design documents providing specifications, business requirements, and architectural patterns for the report system.

## STRUCTURE
```
./design/
├── biz_requirement.md      # Business requirements and use cases
├── design.md               # High-level system design overview  
├── design_api.md           # API design specifications
├── design_instance.md      # Report instance design patterns
├── design_scheduler.md     # Scheduler and automation design
├── design_template.md      # Template system architecture
├── report_sample.md        # Sample reports and output formats
├── spec.md                 # Technical specifications
└── story.md                # User stories and narrative
```

## WHERE TO LOOK
| Document | Primary Use | Coverage |
|----------|-------------|----------|
| biz_requirement.md | Requirements | Business use cases, stakeholder needs |
| design.md | Architecture | System overview, component relationships |
| design_api.md | API Design | Endpoint specifications, request/response patterns |
| design_instance.md | Data Model | Report lifecycle, data flows |
| design_scheduler.md | Automation | Job scheduling, cron patterns |
| design_template.md | Templates | Template engine, variable substitution |
| report_sample.md | Output | Sample outputs, formatting examples |
| spec.md | Technical Specs | Implementation details, interfaces |
| story.md | User Stories | User interactions, acceptance criteria |

## CONVENTIONS
- Markdown format throughout all design docs
- Structured headings with clear sections
- Use of technical descriptions over implementation details
- Scenario-based requirements documentation

## ANTI-PATTERNS (THIS PROJECT)
- No cross-referencing between related design documents
- Design documents not updated with implementation changes
- Missing version control for evolving requirements
- No validation of design vs. implementation alignment

## UNIQUE STYLES
- Comprehensive business requirement coverage before technical details
- Separate API design document focusing on interface contracts
- Story-driven narrative complementing specification documents
- Detailed sample reports showing expected output

## COMMANDS
```bash
# No executable commands in design directory
# Design reviewed manually via documentation
```

## NOTES
- Design documents reflect initial project vision
- Some implementation may have diverged from original designs
- Good reference for understanding intended features vs. implemented