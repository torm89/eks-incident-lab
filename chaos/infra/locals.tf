locals {
  common_tags = {
    Project   = "torm-eks"
    ManagedBy = "terraform"
  }

  # Tag that infra/ puts on every resource. FIS finds targets by it,
  # so templates can exist before the cluster does.
  project_tag = {
    key   = "Project"
    value = local.common_tags.Project
  }
}
