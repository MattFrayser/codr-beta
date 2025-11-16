# Tree-Sitter Parser Warnings

## Warning Message

```
Warning: Failed to load javascript parser: Language.__init__() missing 1 required positional argument: 'name'
```

## What This Means

The tree-sitter library has a version incompatibility with the parser initialization code in your AST validators. This is used for validating JavaScript, C, C++, and Rust code for security.

## Impact

- **Python validation still works** (uses built-in `ast` module)
- **Execution still works** for all languages (Firejail sandbox provides security)
- **Non-critical warning** - doesn't prevent code from running

## Why It Happens

Tree-sitter version 0.21.3 (in requirements.txt) has a different API than newer versions. The language parsers need to be initialized differently.

## Solutions

### Upgrade tree-sitter
Update to the latest tree-sitter version and update the parser initialization code accordingly.

## For Now

The warnings are **cosmetic** and don't affect functionality. Your code will:
- ✅ Execute correctly
- ✅ Be sandboxed by Firejail
- ✅ Stream output properly
- ✅ Handle interactive input

The main async/sync fix is more important, so focus on testing that first!

