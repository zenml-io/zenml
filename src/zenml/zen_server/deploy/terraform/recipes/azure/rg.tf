# run kubectl config view commands to get the current cluster and rg
resource "null_resource" "get_cluster_and_rg" {
  provisioner "local-exec" {
    command = "kubectl config view --minify -o jsonpath='{.clusters[].name}' > cluster.txt"
  }
  provisioner "local-exec" {
    command = "kubectl config view --minify -o jsonpath='{.contexts[].context.user}' | cut -d_ -f2 > namespace.txt"
  }
}

# get the current cluster and namespace
data "local_file" "cluster" {
  filename = "cluster.txt"

  depends_on = [
    null_resource.get_cluster_and_rg
  ]
}

data "local_file" "rg" {
  filename = "namespace.txt"

  depends_on = [
    null_resource.get_cluster_and_rg
  ]
}

# get the current cluster and namespace
locals {
  cluster = chomp(data.local_file.cluster.content)
  rg      = chomp(data.local_file.rg.content)
}

data "azurerm_resource_group" "rg" {
  name = local.rg
}