# Claude Configuration Directory

This directory contains custom skills and slash commands for Claude Code.

## Structure

- `skills/` - Custom Claude skills that extend functionality (slash commands)
- `commands/` - Legacy location for command definitions (still supported)

## Creating Custom Slash Commands

Custom slash commands in Claude Code are created as **Skills**. Each skill is a directory containing a `SKILL.md` file.

### Directory Structure

```
.claude/skills/
└── hello/
    └── SKILL.md
```

### SKILL.md Format

Create a `SKILL.md` file with YAML frontmatter and instructions:

```yaml
---
name: command-name
description: What the command does
argument-hint: [arg1] [arg2]
---

Instructions for Claude on how to execute this command.
Use $ARGUMENTS to access all arguments, or $1, $2, etc. for individual args.
```

### Example: Hello Command

`.claude/skills/hello/SKILL.md`:
```yaml
---
name: hello
description: Greet someone with a personalized hello message
argument-hint: [name]
---

Greet the person named $ARGUMENTS with "Hello, $ARGUMENTS!"
If no arguments are provided, respond with "Hello, World!"
```

### Usage

Once created, invoke your command:
```
/hello Alice
> Hello, Alice!

/hello
> Hello, World!
```

### Key Frontmatter Options

- `name` - The command name (use without `/` prefix)
- `description` - What the command does; Claude uses this to auto-invoke
- `argument-hint` - Shows expected arguments to users
- `disable-model-invocation` - Set to `true` to prevent auto-invocation
- `allowed-tools` - Restrict which tools Claude can use in this skill

## Scope

- `.claude/skills/` - Project-specific, shared with team via git
- `~/.claude/skills/` - Personal, available across all your projects
