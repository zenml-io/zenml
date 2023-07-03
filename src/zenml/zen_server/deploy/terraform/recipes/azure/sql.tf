# random string for the Flexible Server instance name
resource "random_string" "flexible_server_suffix" {
  count  = var.deploy_db ? 1 : 0
  length = 4
  upper  = false
  special = false
}

resource "azurerm_mysql_flexible_server" "mysql" {
  count                  = var.deploy_db ? 1 : 0
  name                   = "${var.db_instance_name}-${random_string.flexible_server_suffix[0].result}"
  resource_group_name    = local.rg
  location               = data.azurerm_resource_group.rg.location
  administrator_login    = var.database_username
  administrator_password = var.database_password == "" ? random_password.mysql_password.result : var.database_password
  version                = var.db_version
  storage {
    size_gb = var.db_disk_size
  }
  sku_name = var.db_sku_name
}

resource "azurerm_mysql_flexible_database" "db" {
  count               = var.deploy_db ? 1 : 0
  name                = var.db_name
  resource_group_name = data.azurerm_resource_group.rg.name
  server_name         = azurerm_mysql_flexible_server.mysql[0].name
  charset             = "utf8"
  collation           = "utf8_unicode_ci"
}

resource "azurerm_mysql_flexible_server_firewall_rule" "allow_IPs" {
  count               = var.deploy_db ? 1 : 0
  name                = "all_traffic"
  resource_group_name = data.azurerm_resource_group.rg.name
  server_name         = azurerm_mysql_flexible_server.mysql[0].name
  start_ip_address    = "0.0.0.0"
  end_ip_address      = "255.255.255.255"
}

resource "azurerm_mysql_flexible_server_configuration" "require_ssl" {
  count               = var.deploy_db ? 1 : 0
  name                = "require_secure_transport"
  resource_group_name = data.azurerm_resource_group.rg.name
  server_name         = azurerm_mysql_flexible_server.mysql[0].name
  value               = "OFF"
}

resource "random_password" "mysql_password" {
  length      = 12
  special     = false
  min_lower   = 1
  min_numeric = 1
  min_upper   = 1
}

# download SSL certificate
resource "null_resource" "download-SSL-certificate" {
  count = var.deploy_db ? 1 : 0

  provisioner "local-exec" {
    command = "wget https://dl.cacerts.digicert.com/DigiCertGlobalRootCA.crt.pem"
  }

}
