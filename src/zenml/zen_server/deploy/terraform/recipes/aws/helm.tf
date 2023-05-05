# check if the host OS is Linux or Windows
data "external" "os" {
  working_dir = path.module
  program     = ["printf", "{\"os\": \"Linux\"}"]
}
locals {
  os                  = data.external.os.result.os
  kubectl_config_path = local.os == "Windows" ? "%USERPROFILE%\\.kube\\config" : "~/.kube/config"
}

# A default (non-aliased) provider configuration for "helm"
provider "helm" {
  kubernetes {
    config_path = var.kubectl_config_path == "" ? local.kubectl_config_path : var.kubectl_config_path
  }
}

provider "kubernetes" {
  config_path = var.kubectl_config_path == "" ? local.kubectl_config_path : var.kubectl_config_path
}