#!/usr/bin/env python3
"""Restore dynamic DAB variable references after bundle generate.

Reads a YAML file from stdin, replaces hardcoded warehouse_id and
parent_path with DAB variable references, outputs to stdout.

Usage: python3 postprocess_generated_yml.py < input.yml > output.yml
"""
import re
import sys

text = sys.stdin.read()

# 16-char hex warehouse_id -> ${var.warehouse_id}
text = re.sub(
    r'(warehouse_id:\s*)[a-f0-9]{16}',
    r'\g<1>${var.warehouse_id}',
    text,
)

# /Workspace/Users/<any-user> -> dynamic current_user
text = re.sub(
    r'(parent_path:\s*)/Workspace/Users/[^\s]+',
    r'\g<1>/Workspace/Users/${workspace.current_user.userName}',
    text,
)

sys.stdout.write(text)
