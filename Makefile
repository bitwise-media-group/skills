# Copyright 2026 Bitwise Media Group
# SPDX-License-Identifier: MIT

# skills — the Claude skill/plugin marketplace, its evaluation suite, and its
# docs site. The whole build surface is mise tasks: the toolchain library's
# common tasks (the .mise/ submodule, selected in the root mise.toml) plus the
# repo-local tasks in tasks.toml. This include only forwards, so
# `make <task>` and `mise run <task>` are interchangeable.
include .mise/common/include.mk
