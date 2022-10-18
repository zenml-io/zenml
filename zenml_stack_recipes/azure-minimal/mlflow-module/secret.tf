# create a secret with user credentials
resource "kubernetes_secret" "name" {
  metadata {
    name = "basic-auth"
  }

  type = "Opaque"
  # the key should be auth for nginx ingress to work
  # throws a 503 error if the key is not auth
  data = {
    "auth" = var.htpasswd
  }
}