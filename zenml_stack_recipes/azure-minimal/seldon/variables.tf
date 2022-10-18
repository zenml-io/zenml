# variables are values that should be supplied 
# by the calling module

# seldon variables
variable "seldon_name" {}
variable "seldon_namespace" {}

# eks cluster variables for setting up 
# the kubernetes and kubectl providers
variable "cluster_endpoint" {}
variable "cluster_ca_certificate" {}
variable "cluster_token" {}