# 示例占位：prod 通常在 EKS/GKE/阿里 ACK 上部署
# 用 Terraform 管网络、IRSA/WorkloadIdentity、S3 冷层、AWS MSK(Kafka)、Aurora(Langfuse) 等。

terraform {
  required_version = ">= 1.8"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

variable "cluster_name" { default = "kg-rag" }
variable "region" { default = "ap-northeast-1" }

# module "eks" { source = "terraform-aws-modules/eks/aws" ... }
# module "s3_cold" { ... bucket for raw docs + cold-tier embeddings ... }
# module "msk" { ... Kafka ... }
# module "elasticache" { ... Redis ... }
