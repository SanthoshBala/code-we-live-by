# Claude Configuration Directory

This directory contains custom skills and slash commands for Claude Code.

## Structure

- `skills/` - Custom Claude skills that extend functionality
- `commands/` - Slash commands for quick access to common operations

## Usage

### Skills

Place custom skill definitions in the `skills/` directory. Skills are reusable components that can perform specific tasks.

### Slash Commands

Place slash command definitions in the `commands/` directory. Slash commands provide quick shortcuts for common operations.

## Examples

To add a new skill:
1. Create a new file in `skills/` (e.g., `my-skill.md`)
2. Define the skill's purpose and implementation
3. Reference it using the Skill tool

To add a new slash command:
1. Create a new file in `commands/` (e.g., `my-command.md`)
2. Define the command's behavior and parameters
3. Use it with `/my-command` in conversations
