resource "aws_ecr_repository" "this" {
  for_each = toset(var.repository_names)

  name                 = "${var.name_prefix}/${each.value}"
  image_tag_mutability = "MUTABLE"

  # The registry lives and dies with the test environment; images are rebuilt each session.
  force_delete = true
}
