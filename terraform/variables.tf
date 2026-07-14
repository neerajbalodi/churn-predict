variable "region" {
  description = "AWS region"
  type        = string
  default     = "ca-central-1"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "churn-mlops"
}

variable "cluster_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.30"
}
