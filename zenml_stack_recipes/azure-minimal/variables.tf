# variables for the MLflow tracking server
variable "mlflow-username" {
  description = "The username for the MLflow Tracking Server"
  default     = "admin"
  type        = string
}

variable "mlflow-password" {
  description = "The password for the MLflow Tracking Server"
  default     = "supersafepassword"
  type        = string
}

# this variable only needs to be set if you're using a 
# pre-exisiting storage account (outside the scope of this recipe).
variable "mlflow-artifact-Azure-Access-Key" {
  description = "The access key for your Azure Storage account that you wish to use with MLflow"
  default     = ""
  type        = string
}

# Variables for the CloudSQL metadata store
variable "metadata-db-username" {
  description = "The username for the CloudSQL metadata store"
  default     = "zenmladmin"
  type        = string
}
variable "metadata-db-password" {
  description = "The password for the CloudSQL metadata store"
  default     = ""
  type        = string
}

# variables for creating a ZenML stack configuration file
variable "zenml-version" {
  description = "The version of ZenML being used"
  default     = "0.11.0"
  type        = string
}