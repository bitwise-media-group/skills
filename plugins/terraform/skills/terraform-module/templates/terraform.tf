# Provider and core version constraints. This file is always named terraform.tf,
# never versions.tf. Pin providers to a major version so update tooling can
# propose minor bumps without crossing a breaking major.

terraform {
  required_version = ">= 1.10"

  required_providers {
    # Replace with the providers this module actually uses.
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0, < 6.61"
    }
  }
}
