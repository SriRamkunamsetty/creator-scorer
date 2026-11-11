output: "eks_cluster_endpoint" {
  description = "Kubernetes API server endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_name" {
  description = "Kubernetes Cluster Name"
  value       = module.eks.cluster_name
}

output "database_endpoint" {
  description = "PostgreSQL primary host endpoint"
  value       = module.db.db_instance_endpoint
  sensitive   = true
}

output "ml_models_s3_bucket" {
  description = "S3 bucket storing ML model artifacts and drift logs"
  value       = aws_s3_bucket.ml_models.bucket
}
