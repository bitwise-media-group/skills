output "security_group_id" {
  description = "ID of the widget security group."
  value       = aws_security_group.main.id
}
