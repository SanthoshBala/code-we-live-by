# Hello Command

A simple greeting command that responds with a personalized hello message.

## Usage

```
/hello <name>
```

## Arguments

- `name` (required) - The name to greet

## Behavior

When invoked, this command should:
1. Extract the provided name argument
2. Return "Hello, {name}!"
3. If no name is provided, return "Hello, World!"

## Examples

```
/hello Alice
> Hello, Alice!

/hello Bob
> Hello, Bob!

/hello
> Hello, World!
```

## Implementation

When this command is invoked with an argument, respond with "Hello, {argument}!" where {argument} is the provided name. If no argument is provided, default to "World".
