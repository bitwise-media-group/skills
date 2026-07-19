# Copyright 2026 Bitwise Media Group
# SPDX-License-Identifier: MIT

# skills — the Claude skill/plugin marketplace and its evaluation suite.
# The whole build surface is mise tasks from the toolchain library (the .mise/
# submodule): the agent-plugins archetype plus the repo-local tasks in
# tasks.toml. This include only forwards, so `make <task>` and
# `mise run <task>` are interchangeable.
include .mise/mise.mk
